"""Handler for capability call_state_machine.

Written by the factory WRITER role (codewhale exec)

Authored by the coder CLI (codewhale exec) — the factory WRITER coding
agent — against the vendored blocks, in this repository.

One lead's call lifecycle as an explicit state machine keyed to the Call SID:
queued -> dialing -> answered -> pitched -> qualified -> transferred |
callback | closed. The configured call window is a guard on the transition,
not a suggestion: a transition whose target window is shut is refused before
anything is published. Each accepted transition is run through the vendored
``workflow`` block, whose first child is a fully prepared ``event_bus``
publish step, and the vendored ``orchestrator`` is asked for the plan of the
transition chain.

Scope
-----
READS  this capability's own columns from the caller's record; app.workflows
       (the transition table and the call-window guard); app.dispatch (the
       local offline block runtime); app.block_inputs (block input
       construction); app.store (the ``call_state_machine`` table, through
       the route's tenant-scoped save).
WRITES app.dispatch.execute() results; exactly one row in
       ``call_state_machine`` via the ROUTE's ``store.save(entity, record,
       tenant_id)`` -- this handler has no tenant and never persists
       directly; one ``call.<state>`` event on the in-process event bus.
NEVER  unguarded network egress; ``vendor/**`` (sealed, read-only); another
       capability's table; ``tests/**``; dialing anything.

Blocks are action-dispatched: ``action=`` is a keyword on
``app.dispatch.execute`` (via app.block_run), never a key inside the domain
payload. Block-contract keys are constructed by
``app.block_inputs.prepare_block_input`` from this record -- the caller is
never asked for them. Every workflow child step is constructed here, fully
specified, so no child reaches the pipeline unprepared.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app import workflows
from app.block_run import block_runner
from app.security import InputRefused, clean_text

CAPABILITY_ID = "call_state_machine"
ENTITY = "call_state_machine"
BLOCK_IDS = ['workflow', 'orchestrator', 'event_bus']
#: Each block's declared action (block.json / the Store map). Blocks are
#: action-dispatched; calling one with no action answers "Unknown action".
BLOCK_DEFAULT_ACTIONS = {'workflow': 'run', 'orchestrator': 'run', 'event_bus': 'publish'}
#: This capability's own domain columns.
CAPABILITY_FIELDS = [
    'reference', 'status', 'call_sid', 'lead_name', 'phone', 'current_state',
    'previous_state', 'call_window', 'window_state', 'transition_event',
    'attempt_count', 'notes',
]

EDGE_CONSTRAINTS = {
    'reference': {'required': True},
    'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True},
    'call_sid': {'required': True},
    'current_state': {'allowed_values': list(workflows.STATES), 'required': True},
}


def _text(data: Dict[str, Any], name: str, limit: int = 2000) -> str:
    return clean_text(data.get(name), field=name, limit=limit)


def _bool(data: Dict[str, Any], name: str, default: bool) -> bool:
    raw = data.get(name)
    if raw in (None, ""):
        return default
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() in ("1", "true", "yes", "open")


def _int(data: Dict[str, Any], name: str, default: int) -> int:
    raw = data.get(name)
    if raw in (None, ""):
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(payload or {}) if isinstance(payload, dict) else {}
    runner = block_runner(entity=ENTITY, roster=BLOCK_IDS, default_actions=BLOCK_DEFAULT_ACTIONS)

    try:
        reference = _text(data, "reference", 120) or "call"
        call_sid = _text(data, "call_sid", 80)
        lead_name = _text(data, "lead_name", 200)
        current = _text(data, "current_state", 40).lower() or workflows.INITIAL_STATE
        window = _text(data, "call_window", 80) or workflows.DEFAULT_WINDOW
        window_state = _text(data, "window_state", 20).lower() or "open"
        # The guard is the configured calling window, and the record states it
        # in a vocabulary the schema can express: open / closed. A record that
        # says "closed" is refused at the transition, not after it.
        window_open = window_state != "closed"
        attempt_count = max(0, _int(data, "attempt_count", 0))
        if not call_sid:
            return {
                "ok": False,
                "capability": CAPABILITY_ID,
                "error": "call_sid is required: a call event is keyed to its SID",
            }
        if window_state not in ("open", "closed"):
            return {
                "ok": False,
                "capability": CAPABILITY_ID,
                "error": "window_state must be one of: open, closed",
            }
        if current not in workflows.STATES:
            return {
                "ok": False,
                "capability": CAPABILITY_ID,
                "error": "current_state must be one of: " + ", ".join(workflows.STATES),
            }
        decision = workflows.next_state(
            current, window_open=window_open, attempt_count=attempt_count
        )
        if not decision["allowed"]:
            return {
                "ok": False,
                "capability": CAPABILITY_ID,
                "error": decision["reason"],
                "state": current,
                "call_sid": call_sid,
            }
    except InputRefused as exc:
        return {"ok": False, "capability": CAPABILITY_ID, "error": str(exc)}

    target = decision["next_state"]
    topic = f"call.{target}"
    result_payload = {
        "reference": reference,
        "call_sid": call_sid,
        "from_state": current,
        "to_state": target,
        "attempt_count": attempt_count,
    }
    steps = [
        {
            "id": "step_0",
            "block": "event_bus",
            "action": "publish",
            "params": {"action": "publish"},
            "input": {
                "topic": topic,
                "payload": {
                    "reference": reference,
                    "call_sid": call_sid,
                    "state": target,
                },
                "message": f"call {call_sid} moved {current} -> {target}",
                "channel": "mcp",
                "tool": "event_bus",
            },
        }
    ]

    plan = runner(
        "orchestrator",
        {"task": f"advance call {call_sid} to {target}", "input": result_payload},
        action="run",
    )
    pipeline = runner(
        "workflow",
        {
            "pipeline_id": f"call-state-{reference}".replace(" ", "_"),
            "timeout": 30,
            "result": result_payload,
            "steps": steps,
        },
        action="run",
    )
    published = runner(
        "event_bus",
        {
            "topic": topic,
            "payload": {
                "reference": reference,
                "call_sid": call_sid,
                "state": target,
            },
            "message": f"call {call_sid} moved {current} -> {target}",
            "channel": "mcp",
            "tool": "event_bus",
        },
        action="publish",
    )

    refusal = runner.refusal()
    if refusal is not None:
        return {"ok": False, "capability": CAPABILITY_ID, **refusal}

    children = pipeline.get("results") if isinstance(pipeline, dict) else []
    return {
        "ok": True,
        "capability": CAPABILITY_ID,
        "call_sid": call_sid,
        "transition": {
            "from_state": current,
            "to_state": target,
            "event": decision["event"],
            "call_window": window,
            "window_state": window_state,
            "window_open": window_open,
            "guard": decision["guard"],
        },
        "orchestration": {
            "mode": plan.get("mode") if isinstance(plan, dict) else None,
            "task": plan.get("task") if isinstance(plan, dict) else None,
        },
        "workflow": {
            "pipeline_id": pipeline.get("pipeline_id") if isinstance(pipeline, dict) else None,
            "step_count": pipeline.get("step_count") if isinstance(pipeline, dict) else None,
            "children": [
                {"step_id": item.get("step_id"), "block": item.get("block"),
                 "status": item.get("status")}
                for item in (children or [])
                if isinstance(item, dict)
            ],
        },
        "published": {
            "topic": published.get("topic") if isinstance(published, dict) else topic,
            "correlation_id": published.get("correlation_id") if isinstance(published, dict) else None,
        },
        "blocks": runner.report(),
    }
