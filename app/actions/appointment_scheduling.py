"""appointment_scheduling — REUSE workflow + event_bus + notification + queue."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import (
    appointment_workflow_input,
    event_bus_input,
    notification_input,
    queue_input,
)
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.domain import allowed_next_status, appointment_cascade, envelope_status
from app.persist import ok_envelope

# READS: caller.input, env.process, config.runtime, memory.cache, queue.jobs
# WRITES: caller.output, notification.outbound, queue.jobs
# NEVER: (none)

BLOCK_IDS = ["workflow", "event_bus", "notification", "queue"]
CAPABILITY_ID = "appointment_scheduling"
VISIT_TYPES = ("wellness", "surgery", "emergency", "follow_up")


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Book a visit with prepared event_bus steps and a cascade next action."""
    status = envelope_status(payload)
    visit_type = str(payload.get("visit_type") or "wellness")
    if visit_type not in VISIT_TYPES:
        visit_type = "wellness"
    slot_label = str(payload.get("slot_label") or payload.get("reference") or "sample")
    cascade = appointment_cascade(visit_type)
    record = {
        **payload,
        "status": status,
        "visit_type": visit_type,
        "slot_label": slot_label,
        "event": f"vetcare.appointment.{visit_type}",
        "next_action": cascade["next_action"],
        "sla_minutes": cascade["sla_minutes"],
        "capability": CAPABILITY_ID,
        "channel": "mcp",
    }
    # Workflow carries result + prepared event_bus step_0, step_1, step_2.
    blocks = {
        "workflow": execute(
            "workflow",
            appointment_workflow_input(record),
            action=BLOCK_DEFAULT_ACTIONS.get("workflow"),
        ),
        "event_bus": execute(
            "event_bus",
            event_bus_input(record),
            action=BLOCK_DEFAULT_ACTIONS.get("event_bus"),
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
    record["appointment"] = {
        "visit_type": visit_type,
        "slot_label": slot_label,
        "next_action": cascade["next_action"],
        "sla_minutes": cascade["sla_minutes"],
        "queue": cascade["queue"],
        "published": True,
        "allowed_next_status": list(allowed_next_status(status)),
        "pipeline": f"appointment-{record.get('reference') or 'sample'}",
        "steps": ["step_0", "step_1", "step_2"],
    }
    return ok_envelope(CAPABILITY_ID, record, blocks)
