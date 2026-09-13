"""booking_management — REUSE workflow + database + notification + queue."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import (
    booking_workflow_input,
    database_input,
    notification_input,
    queue_input,
)
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.domain import (
    allowed_next_status,
    booking_cascade,
    envelope_status,
    nightly_rate,
    stay_nights,
    stay_total,
)
from app.persist import ok_envelope

# READS: caller.input, env.process, config.runtime, database.sql, queue.jobs
# WRITES: caller.output, database.sql, notification.outbound, queue.jobs
# NEVER: (none)

BLOCK_IDS = ["workflow", "database", "notification", "queue"]
CAPABILITY_ID = "booking_management"
STAY_KINDS = ("night", "week", "group")


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Reserve a stay with prepared workflow steps and persist the booking."""
    status = envelope_status(payload)
    stay_kind = str(payload.get("stay_kind") or "night")
    if stay_kind not in STAY_KINDS:
        stay_kind = "night"
    room_label = str(payload.get("room_label") or payload.get("reference") or "sample")
    nights = stay_nights(stay_kind)
    rate = nightly_rate(status)
    total = stay_total(status, stay_kind)
    cascade = booking_cascade(stay_kind)
    record = {
        **payload,
        "status": status,
        "stay_kind": stay_kind,
        "room_label": room_label,
        "stay_nights": nights,
        "nightly_rate": rate,
        "stay_total": total,
        "event": f"hotel.booking.{stay_kind}",
        "next_action": cascade["next_action"],
        "hold_minutes": cascade["hold_minutes"],
        "capability": CAPABILITY_ID,
        "channel": "mcp",
    }
    blocks = {
        "workflow": execute(
            "workflow",
            booking_workflow_input(record),
            action=BLOCK_DEFAULT_ACTIONS.get("workflow"),
        ),
        "database": execute(
            "database",
            database_input(record),
            action=BLOCK_DEFAULT_ACTIONS.get("database"),
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
    record["booking"] = {
        "stay_kind": stay_kind,
        "room_label": room_label,
        "stay_nights": nights,
        "nightly_rate": rate,
        "stay_total": total,
        "next_action": cascade["next_action"],
        "hold_minutes": cascade["hold_minutes"],
        "queue": cascade["queue"],
        "allowed_next_status": list(allowed_next_status(status)),
        "pipeline": f"booking-{record.get('reference') or 'sample'}",
        "steps": ["step_0", "step_1", "step_2"],
    }
    return ok_envelope(CAPABILITY_ID, record, blocks)
