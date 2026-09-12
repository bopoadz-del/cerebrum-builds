"""estate_registry — multi-property registry. REUSE database + storage + validation."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import database_input, storage_input, validation_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, env.process, config.runtime, database.sql, file.local.read
# WRITES: caller.output, database.sql, file.local.write
# NEVER: (none)

BLOCK_IDS = ["database", "storage", "validation"]


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Register a property/asset envelope and persist it to estate_registry."""
    blocks = {
        "database": execute(
            "database",
            database_input(payload),
            action=BLOCK_DEFAULT_ACTIONS.get("database"),
        ),
        "storage": execute(
            "storage",
            storage_input(payload),
            action=BLOCK_DEFAULT_ACTIONS.get("storage"),
        ),
        "validation": execute(
            "validation",
            validation_input(payload),
            action=BLOCK_DEFAULT_ACTIONS.get("validation"),
        ),
    }
    return ok_envelope("estate_registry", payload, blocks)
