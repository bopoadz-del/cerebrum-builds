"""flight_event_orchestration — REUSE event_bus + workflow + notification + queue."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import (
    event_bus_input,
    flight_workflow_input,
    notification_input,
    queue_input,
)
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.domain import allowed_next_status, envelope_status, flight_cascade
from app.persist import ok_envelope

# READS: caller.input, env.process, config.runtime, memory.cache, queue.jobs
# WRITES: caller.output, notification.outbound, queue.jobs
# NEVER: (none)

BLOCK_IDS = ["event_bus", "workflow", "notification", "queue"]
CAPABILITY_ID = "flight_event_orchestration"
EVENT_TYPES = ("arrival", "departure", "weather", "hold")


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Publish a flight event, run prepared event_bus steps, and cascade next action."""
    status = envelope_status(payload)
    event_type = str(payload.get("event_type") or "arrival")
    if event_type not in EVENT_TYPES:
        event_type = "arrival"
    flight_reference = str(
        payload.get("flight_reference") or payload.get("reference") or "sample"
    )
    cascade = flight_cascade(event_type)
    record = {
        **payload,
        "status": status,
        "event_type": event_type,
        "flight_reference": flight_reference,
        "event": f"airport.flight.{event_type}",
        "next_action": cascade["next_action"],
        "sla_minutes": cascade["sla_minutes"],
        "capability": CAPABILITY_ID,
        "channel": "mcp",
    }
    # Workflow carries result + prepared event_bus step_0, step_1, step_2.
    blocks = {
        "event_bus": execute(
            "event_bus",
            event_bus_input(record),
            action=BLOCK_DEFAULT_ACTIONS.get("event_bus"),
        ),
        "workflow": execute(
            "workflow",
            flight_workflow_input(record),
            action=BLOCK_DEFAULT_ACTIONS.get("workflow"),
        ),
        "notification": execute(
            "notification",
            notification_input(record),
            action=BLOCK_DEFAULT_ACTIONS.get("notification"),
        ),
        "queue": execute(
            "queue",
            queue_input(record),
            action=BLOCK_DEFAULT_ACTIONS.get("queue"),
        ),
    }
    record["orchestration"] = {
        "event_type": event_type,
        "flight_reference": flight_reference,
        "next_action": cascade["next_action"],
        "sla_minutes": cascade["sla_minutes"],
        "queue": cascade["queue"],
        "published": True,
        "allowed_next_status": list(allowed_next_status(status)),
        "pipeline": f"flight-{record.get('reference') or 'sample'}",
        "steps": ["step_0", "step_1", "step_2"],
    }
    return ok_envelope(CAPABILITY_ID, record, blocks)
