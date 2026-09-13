"""stock_adjustment_workflow — REUSE workflow, audit, validation."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import audit_input, validation_input, workflow_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, env.process, config.runtime, database.sql
# WRITES: caller.output, database.sql
# NEVER: (none)

BLOCK_IDS = ["workflow", "audit", "validation"]


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Run a prepared stock-adjustment pipeline, then audit and persist."""
    record = {**payload, "capability": "stock_adjustment_workflow"}
    prepared = workflow_input(record)
    blocks = {
        "workflow": execute(
            "workflow",
            prepared,
            action=BLOCK_DEFAULT_ACTIONS.get("workflow"),
        ),
        "audit": execute(
            "audit",
            audit_input({**record, "event_action": "stock_adjust", "category": "admin"}),
            action=BLOCK_DEFAULT_ACTIONS.get("audit"),
        ),
        "validation": execute(
            "validation",
            validation_input(record, item_type="stock_adjustment"),
            action=BLOCK_DEFAULT_ACTIONS.get("validation"),
        ),
    }
    return ok_envelope("stock_adjustment_workflow", record, blocks)
