"""fleet_registry_management — REUSE database + validation. Aircraft registry."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import database_input, validation_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, config.runtime, database.sql
# WRITES: caller.output, database.sql
# NEVER: (none)

BLOCK_IDS = ["database", "validation"]
CAPABILITY_ID = "fleet_registry_management"
TYPES = ("narrowbody", "widebody", "bizjet")
TYPE_CERTS = {
    "narrowbody": "A320-family",
    "widebody": "B787-family",
    "bizjet": "G650-family",
}


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a registry row and query the fleet table constructed from the envelope."""
    aircraft_type = str(payload.get("aircraft_type") or "narrowbody")
    if aircraft_type not in TYPES:
        aircraft_type = "narrowbody"
    registration = str(payload.get("registration") or payload.get("reference") or "sample")
    record = {
        **payload,
        "registration": registration,
        "aircraft_type": aircraft_type,
        "capability": CAPABILITY_ID,
        "channel": "mcp",
    }
    blocks = {
        "database": execute(
            "database",
            database_input(record),
            action=BLOCK_DEFAULT_ACTIONS.get("database"),
        ),
        "validation": execute(
            "validation",
            validation_input(record),
            action=BLOCK_DEFAULT_ACTIONS.get("validation"),
        ),
    }
    record["registry"] = {
        "registration": registration,
        "aircraft_type": aircraft_type,
        "type_certificate": TYPE_CERTS[aircraft_type],
        "active": record.get("status") != "closed",
    }
    return ok_envelope(CAPABILITY_ID, record, blocks)
