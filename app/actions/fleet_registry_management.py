"""fleet_registry_management — REUSE database + validation. Tail registry card."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import database_input, validation_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, env.process, config.runtime, database.sql
# WRITES: caller.output, database.sql
# NEVER: (none)

BLOCK_IDS = ["database", "validation"]

TYPE_SEATS = {
    "narrow_body": 180,
    "wide_body": 300,
    "regional": 90,
    "rotorcraft": 12,
}


def _aircraft_type(payload: Dict[str, Any]) -> str:
    value = str(payload.get("aircraft_type") or "narrow_body")
    return value if value in TYPE_SEATS else "narrow_body"


def _mark(payload: Dict[str, Any]) -> str:
    mark = str(payload.get("registry_mark") or payload.get("reference") or "sample")
    return mark if mark else "sample"


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a fleet registry card then query the local aircraft table."""
    aircraft_type = _aircraft_type(payload)
    mark = _mark(payload)
    table = "fleet_registry_cards"
    blocks = {
        "database": execute(
            "database",
            database_input(payload, table),
            action=BLOCK_DEFAULT_ACTIONS.get("database"),
        ),
        "validation": execute(
            "validation",
            validation_input(payload, "aircraft"),
            action=BLOCK_DEFAULT_ACTIONS.get("validation"),
        ),
    }
    record = {
        **payload,
        "registry_card": {
            "registry_mark": mark,
            "aircraft_type": aircraft_type,
            "typical_seats": TYPE_SEATS[aircraft_type],
            "active": payload.get("status") != "closed",
            "not_a_booking_engine": True,
            "channel": "mcp",
        },
    }
    return ok_envelope("fleet_registry_management", record, blocks)
