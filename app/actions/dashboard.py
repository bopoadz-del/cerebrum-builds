"""dashboard — REUSE Store dashboard block. Bind persist + BLOCK_DEFAULT_ACTIONS."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import dashboard_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, config.runtime
# WRITES: caller.output
# NEVER: (none)

BLOCK_IDS = ["dashboard"]


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Render the AirOps portfolio dashboard from constructed inputs; persist."""
    blocks = {
        "dashboard": execute(
            "dashboard",
            dashboard_input(payload),
            action=BLOCK_DEFAULT_ACTIONS.get("dashboard"),
        ),
    }
    return ok_envelope("dashboard", payload, blocks)
