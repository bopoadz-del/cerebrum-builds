"""inventory_stock_tracking — REUSE database, storage, validation, audit."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import audit_input, database_input, storage_input, validation_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, env.process, config.runtime, database.sql, file.local.read
# WRITES: caller.output, database.sql, file.local.write
# NEVER: (none)

BLOCK_IDS = ["database", "storage", "validation", "audit"]


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Persist a SKU on-hand record after constructed Store block calls."""
    record = {**payload, "capability": "inventory_stock_tracking"}
    blocks = {
        "database": execute(
            "database",
            database_input(record),
            action=BLOCK_DEFAULT_ACTIONS.get("database"),
        ),
        "storage": execute(
            "storage",
            storage_input(record),
            action=BLOCK_DEFAULT_ACTIONS.get("storage"),
        ),
        "validation": execute(
            "validation",
            validation_input(record, item_type="inventory_sku"),
            action=BLOCK_DEFAULT_ACTIONS.get("validation"),
        ),
        "audit": execute(
            "audit",
            audit_input({**record, "event_action": "stock_track", "category": "data_access"}),
            action=BLOCK_DEFAULT_ACTIONS.get("audit"),
        ),
    }
    return ok_envelope("inventory_stock_tracking", record, blocks)
