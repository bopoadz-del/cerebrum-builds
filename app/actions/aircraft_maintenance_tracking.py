"""aircraft_maintenance_tracking — REUSE workflow + audit. Airworthiness work orders."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import audit_input, workflow_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, env.process, config.runtime, database.sql
# WRITES: caller.output, database.sql
# NEVER: (none)

BLOCK_IDS = ["workflow", "audit"]

KIND_INTERVAL = {
    "scheduled": 400,
    "unscheduled": 40,
    "ad_compliance": 120,
}


def _kind(payload: Dict[str, Any]) -> str:
    value = str(payload.get("maintenance_kind") or "scheduled")
    return value if value in KIND_INTERVAL else "scheduled"


def _tail(payload: Dict[str, Any]) -> str:
    tail = str(payload.get("tail_number") or payload.get("reference") or "sample")
    return tail if tail else "sample"


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Open an airworthiness work order, run the mx workflow, then persist."""
    kind = _kind(payload)
    tail = _tail(payload)
    reference = str(payload.get("reference") or "sample")
    topic = f"maintenance.{kind}"
    message = f"Airworthiness work order {reference} for tail {tail}"
    audit_body = audit_input(
        {
            **payload,
            "category": "system",
            "event_action": "maintenance_open",
            "capability": "aircraft_maintenance_tracking",
        }
    )
    steps = [
        {
            "id": "step_0",
            "block": "audit",
            "action": "log",
            "params": {"action": BLOCK_DEFAULT_ACTIONS.get("audit")},
            "input": audit_body,
        }
    ]
    first_result = steps[0]["input"]
    blocks = {
        "workflow": execute(
            "workflow",
            workflow_input(payload, steps, f"mx-{reference}"),
            action=BLOCK_DEFAULT_ACTIONS.get("workflow"),
        ),
        "audit": execute(
            "audit",
            audit_body,
            action=BLOCK_DEFAULT_ACTIONS.get("audit"),
        ),
    }
    record = {
        **payload,
        "work_order": {
            "tail_number": tail,
            "maintenance_kind": kind,
            "hours_until_due": KIND_INTERVAL[kind],
            "airworthy_after_close": True,
            "topic": topic,
            "message": message,
            "channel": "mcp",
            "result": first_result,
        },
    }
    return ok_envelope("aircraft_maintenance_tracking", record, blocks)
