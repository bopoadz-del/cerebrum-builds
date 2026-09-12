"""audit — REUSE Store audit block. Bind persist + BLOCK_DEFAULT_ACTIONS."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import audit_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, config.runtime, database.sql
# WRITES: caller.output, database.sql
# NEVER: (none)

BLOCK_IDS = ["audit"]


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Log an AirOps Principal audit event from the envelope; persist the record."""
    blocks = {
        "audit": execute(
            "audit",
            audit_input(payload),
            action=BLOCK_DEFAULT_ACTIONS.get("audit"),
        ),
    }
    return ok_envelope("audit", payload, blocks)
