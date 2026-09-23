"""Call state machine.

Written by the factory WRITER role (codewhale exec)

Each lead's call runs queued → dialing → answered → pitched → qualified →
transferred | callback | closed. A transition is allowed only when the table
says so *and* the language's calling window is open; otherwise the decision
is recorded as a refusal with the reason, which is what the operator needs
to see at 3am. Everything is keyed to the Call SID.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from app import dispatch, domain
from app import tenancy
from app.models import MODELS

CAPABILITY_ID = "call_state_machine"

#: The keyword action each bound block is dispatched with:
#: ``dispatch.execute(block_id, action=BLOCK_DEFAULT_ACTIONS.get(block_id))``.
#: The action travels as a keyword and never inside the payload -- the block
#: registry reads its operation from the keyword, and a payload "action" key
#: is just another record field. These are the actions ``app/dispatch.py``
#: registers for each block, so a declared default is a call this platform
#: can actually make.
BLOCK_DEFAULT_ACTIONS = {
    'workflow': 'transition',
    'orchestrator': 'run',
    'event_bus': 'publish',
}

#: The prepared event_bus workflow child.
#:
#: Every key a Store workflow run reads is constructed here in source --
#: ``block`` (a workflow child names its block under that key, not
#: ``block_id``), the keyword ``action``, a non-empty ``topic``, a ``payload``
#: dict of this call's own scalars, a ``message``, ``channel`` = ``mcp`` (the
#: MCP notify path needs a channel it can send on, never the caller's raw
#: record) and ``tool`` = ``event_bus``. The template is copied and populated
#: per call by :func:`event_step`; the caller's payload is never forwarded as
#: a step input.
WORKFLOW_STEPS: List[Dict[str, Any]] = [
    {
        "block": "event_bus",
        "action": "publish",
        "input": {
            "topic": "call.transition",
            "payload": {"reference": "call-event"},
            "message": "call state transition",
            "channel": "mcp",
            "tool": "event_bus",
        },
    },
]

REQUIRED_FIELDS = ["call_sid", "event"]

#: The same contract app/models.py declares, stated where the handler
#: enforces it: the route refuses from the model, the handler refuses
#: from here, and the two cannot drift (tests/test_capability_round_trip.py).
constraints = {
    "call_sid": {"required": True, "max_length": 64},
    "lead_id": {"max_length": 40},
    "lead_reference": {"max_length": 80},
    "event": {"allowed_values": ['dial', 'answer', 'pitch', 'qualify', 'transfer', 'callback', 'close', 'abandon', 'retry', 'no_answer', 'busy'], "required": True},
    "previous_state": {"allowed_values": ['queued', 'dialing', 'answered', 'pitched', 'qualified', 'transferred', 'callback', 'closed']},
    "current_state": {"allowed_values": ['queued', 'dialing', 'answered', 'pitched', 'qualified', 'transferred', 'callback', 'closed']},
    "attempt_count": {"min": 0},
    "within_window": {},
    "window_reason": {"max_length": 60},
    "transition_allowed": {},
    "refusal_reason": {"max_length": 200},
    "guard_notes": {"max_length": 400},
    "window_snapshot": {"max_length": 200},
    "occurred_at": {"max_length": 40},
    "source": {"allowed_values": ['voice_gateway', 'operator', 'scheduler', 'tests']},
    "campaign": {"max_length": 80},
    "reference": {"required": True},
    "status": {"allowed_values": ['open', 'in_progress', 'closed'], "required": True},
}

STATE_ORDER = (
    "queued", "dialing", "answered", "pitched",
    "qualified", "transferred", "callback", "closed",
)


def event_step(body: Dict[str, Any], decision: Dict[str, Any]) -> Dict[str, Any]:
    """The prepared event_bus child, carrying this call's own scalars.

    Copy of :data:`WORKFLOW_STEPS` -- the literal prepared in source -- with
    topic, payload and message populated from the transition. The caller's
    record never becomes a step input.
    """
    step = json.loads(json.dumps(WORKFLOW_STEPS[0]))
    event = str(decision.get("event") or body.get("event") or "attempted")
    call_sid = str(body.get("call_sid") or "")
    step["input"]["topic"] = f"call.transition.{event}"
    step["input"]["payload"] = {
        "call_sid": call_sid,
        "event": event,
        "previous_state": decision.get("previous_state"),
        "current_state": decision.get("current_state"),
        "transition_allowed": bool(decision.get("transition_allowed")),
    }
    step["input"]["message"] = (
        f"{call_sid or 'call'}: {decision.get('previous_state')} -> "
        f"{decision.get('current_state')} ({event})"
    )
    return step


def publish_event(step: Dict[str, Any], body: Dict[str, Any], decision: Dict[str, Any]) -> Dict[str, Any]:
    """Publish the transition on the event bus. A refusal is returned, not hidden."""
    inner = dict(step["input"]["payload"])
    try:
        outcome = dispatch.execute(
            "event_bus",
            action=step["action"],
            payload={
                **inner,
                "tenant_id": str(body.get("tenant_id") or tenancy.deployment_tenant()),
                "event_type": str(decision.get("event") or "attempted"),
                "detail": inner,
                "outcome": body.get("outcome"),
                "actor": "call_state_machine",
                "campaign": body.get("campaign"),
            },
        )
    except Exception as exc:  # BlockRefused, or storage refusing the write
        return {
            "published": False,
            "error": f"{type(exc).__name__}: {exc}",
            "topic": step["input"]["topic"],
        }
    failure = dispatch.refusal_of(outcome)
    if failure:
        return {
            "published": False,
            "error": failure,
            "topic": step["input"]["topic"],
        }
    entry = outcome.get("entry") if isinstance(outcome.get("entry"), dict) else {}
    return {
        "published": True,
        "entry_id": entry.get("id"),
        "topic": step["input"]["topic"],
        "channel": step["input"]["channel"],
        "tool": step["input"]["tool"],
    }


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Guard one transition and return the call's new standing state."""
    body = dict(payload or {})
    for name in REQUIRED_FIELDS:
        if body.get(name) in (None, ""):
            return {"ok": False, "error": f"Missing required field: {name}"}
    if body.get("reference") in (None, ""):
        return {"ok": False, "error": "Missing required field: reference"}
    if body.get("status") in (None, ""):
        return {"ok": False, "error": "Missing required field: status"}
    for name, rules in constraints.items():
        values = rules.get("allowed_values") or ()
        value = body.get(name)
        if value is None or value == "":
            continue
        if values and value not in values:
            return {
                "ok": False,
                "error": f"{name} must be one of: " + ", ".join(str(v) for v in values),
            }
    decision = domain.transition(body)
    warned = None
    if not decision["transition_allowed"] and decision["event"] == "dial":
        warned = "dial refused by the call-window guard"
    elif not decision["transition_allowed"]:
        warned = decision["refusal_reason"]
    # A transition the platform cannot write down is not a transition it can
    # stand behind: the call event leaves through the prepared event_bus child
    # first, and a publish that fails is reported as this capability failing
    # rather than a success over a block that refused.
    event = publish_event(event_step(body, decision), body, decision)
    if not event["published"]:
        return {
            "ok": False,
            "capability": CAPABILITY_ID,
            "error": "call event could not be written: "
            + str(event.get("error") or "event_bus refused the publish"),
        }
    return {
        "ok": True,
        "capability": CAPABILITY_ID,
        "call_sid": body.get("call_sid"),
        "decision": "allowed" if decision["transition_allowed"] else "refused",
        "transition_allowed": decision["transition_allowed"],
        "refusal_reason": decision["refusal_reason"],
        "warning": warned,
        "event": event,
        "record": {
            "lead_id": body.get("lead_id"),
            "lead_reference": body.get("lead_reference"),
            "event": decision["event"],
            "previous_state": decision["previous_state"],
            "current_state": decision["current_state"],
            "attempt_count": decision["attempt_count"],
            "within_window": decision["within_window"],
            "window_reason": decision["window_reason"],
            "transition_allowed": decision["transition_allowed"],
            "refusal_reason": decision["refusal_reason"],
            "guard_notes": warned or "transition permitted by the state table and window guard",
            "window_snapshot": decision["window_snapshot"],
            "occurred_at": decision["occurred_at"],
            "source": body.get("source") or "operator",
        },
        "authority": decision["authority"],
    }
