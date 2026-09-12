"""vendor_budget — vendor rates and spend. REUSE formula_executor + audit + notification."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import audit_input, formula_executor_input, notification_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, env.process, config.runtime, database.sql, credential.env, block.peer
# WRITES: caller.output, database.sql, notification.outbound
# NEVER: (none)

BLOCK_IDS = ["formula_executor", "audit", "notification"]


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Price a vendor line, audit it, and notify ops on the MCP channel."""
    blocks = {
        "formula_executor": execute(
            "formula_executor",
            formula_executor_input(payload),
            action=BLOCK_DEFAULT_ACTIONS.get("formula_executor"),
        ),
        "audit": execute(
            "audit",
            audit_input(payload),
            action=BLOCK_DEFAULT_ACTIONS.get("audit"),
        ),
        "notification": execute(
            "notification",
            notification_input(payload),
            action=BLOCK_DEFAULT_ACTIONS.get("notification"),
        ),
    }
    return ok_envelope("vendor_budget", payload, blocks)
