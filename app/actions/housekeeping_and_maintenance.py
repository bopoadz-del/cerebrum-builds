"""Handler for capability housekeeping_and_maintenance.

Written by the factory WRITER role (codewhale exec)

Authored by the coder CLI (codewhale exec) — the factory WRITER coding
agent — against the vendored blocks, in this repository.

Schedules and tracks room turnover and repair work: the work order is opened in the
vendored maintenance ledger, its board is rendered for the duty manager, and the
dispatched task is recorded as a second ledger entry, so assignment and completion
state are visible per room and per asset.

Scope
-----
READS  this capability's own columns from the caller's record; app.dispatch
       (the local offline block runtime); app.block_inputs (block input
       construction); app.store (the ``housekeeping_and_maintenance`` table, through the route's
       tenant-scoped save).
WRITES app.dispatch.execute() results; exactly one row in ``housekeeping_and_maintenance`` via the
       ROUTE's tenant-scoped persistence (app.routes) -- this handler has no
       tenant and never persists directly.
NEVER  unguarded network egress; ``vendor/**`` (sealed, read-only); another
       capability's table; ``tests/**``.

Blocks are action-dispatched: ``action=`` is a keyword on
``app.dispatch.execute`` (via app.block_run), never a key inside the domain
payload. Block-contract keys are constructed by
``app.block_inputs.prepare_block_input`` from this record -- the caller is
never asked for them. Every workflow child step is constructed here, fully
specified, so no child reaches the pipeline unprepared.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.block_run import block_runner
from app.security import InputRefused, clean_text

CAPABILITY_ID = "housekeeping_and_maintenance"
ENTITY = "housekeeping_and_maintenance"
BLOCK_IDS = ['estate_maintenance', 'workflow']
#: Each block's declared action (block.json / the Store map). Blocks are
#: action-dispatched; calling one with no action answers "Unknown action".
BLOCK_DEFAULT_ACTIONS = {'estate_maintenance': 'create', 'workflow': 'run'}
#: This capability's own domain columns.
CAPABILITY_FIELDS = ['reference', 'status', 'title', 'work_type', 'room_number', 'priority', 'due_date', 'assigned_to', 'work_status', 'notes']


def _text(data: Dict[str, Any], name: str, limit: int = 2000) -> str:
    return clean_text(data.get(name), field=name, limit=limit)

def _work_order_summary(data: Dict[str, Any]) -> str:
    return (
        "Housekeeping and maintenance work order. Title: {title}. Type: {kind}. "
        "Room: {room}. Priority: {priority}. Due: {due}. Assigned to: {who}. "
        "Work status: {work_status}. Notes: {notes}"
    ).format(
        title=_text(data, "title", 200) or "unnamed task",
        kind=_text(data, "work_type", 40) or "housekeeping",
        room=_text(data, "room_number", 40) or "unassigned",
        priority=_text(data, "priority", 20) or "normal",
        due=_text(data, "due_date", 40),
        who=_text(data, "assigned_to", 120) or "unassigned",
        work_status=_text(data, "work_status", 40) or "open",
        notes=_text(data, "notes", 500),
    )


def _priority_rank(priority: str) -> int:
    order = {"low": 1, "normal": 2, "high": 3, "urgent": 4}
    return order.get(priority, 2)


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(payload or {}) if isinstance(payload, dict) else {}
    runner = block_runner(entity=ENTITY, roster=BLOCK_IDS, default_actions=BLOCK_DEFAULT_ACTIONS)

    try:
        title = _text(data, "title", 200)
        if not title:
            return {
                "ok": False,
                "capability": CAPABILITY_ID,
                "error": "title is required: a work order without a task cannot be scheduled",
            }
        room = _text(data, "room_number", 40)
        work_type = _text(data, "work_type", 40) or "housekeeping"
        priority = _text(data, "priority", 20) or "normal"
        summary = _work_order_summary(data)
    except InputRefused as exc:
        return {"ok": False, "capability": CAPABILITY_ID, "error": str(exc)}

    created = runner(
        "estate_maintenance",
        {"title": title, "due": _text(data, "due_date", 40) or None},
        action="create",
        payload_extra={"action": "create"},
    )
    work_order_id = created.get("id") if isinstance(created, dict) else None

    pipeline = runner(
        "workflow",
        {
            "pipeline_id": f"work-order-{work_order_id or 'new'}",
            "timeout": 30,
            "result": {"work_order_id": work_order_id, "title": title, "room_number": room},
            "steps": [
                {
                    "id": "step_0",
                    "block": "dashboard",
                    "action": BLOCK_DEFAULT_ACTIONS.get("dashboard"),
                    "input": {"status": "open", "widget": "work_orders", "title": "Open work orders"},
                },
                {
                    "id": "step_1",
                    "block": "estate_maintenance",
                    "action": BLOCK_DEFAULT_ACTIONS.get("estate_maintenance"),
                    "input": {"title": f"{work_type}: {title}", "due": _text(data, "due_date", 40) or None},
                },
            ],
        },
        action="run",
    )

    refusal = runner.refusal()
    if refusal is not None:
        return {"ok": False, "capability": CAPABILITY_ID, **refusal}

    steps = pipeline.get("results") if isinstance(pipeline, dict) else []
    return {
        "ok": True,
        "capability": CAPABILITY_ID,
        "work_order": {
            "id": work_order_id,
            "title": title,
            "room_number": room,
            "work_type": work_type,
            "priority": priority,
            "priority_rank": _priority_rank(priority),
            "work_status": _text(data, "work_status", 40) or "open",
        },
        "board": {
            "widget": "work_orders",
            "rendered": bool(pipeline.get("status") == "completed") if isinstance(pipeline, dict) else False,
            "steps": [
                {"step_id": item.get("step_id"), "block": item.get("block"),
                 "status": item.get("status")}
                for item in (steps or [])
                if isinstance(item, dict)
            ],
        },
        "blocks": runner.report(),
    }
