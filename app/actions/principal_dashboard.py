"""principal_dashboard — portfolio health. REUSE dashboard + analytics."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import analytics_input, dashboard_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, config.runtime, llm.provider
# WRITES: caller.output
# NEVER: (none)

BLOCK_IDS = ["dashboard", "analytics"]


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Render the principal surface and track a portfolio health metric."""
    blocks = {
        "dashboard": execute(
            "dashboard",
            dashboard_input(payload),
            action=BLOCK_DEFAULT_ACTIONS.get("dashboard"),
        ),
        "analytics": execute(
            "analytics",
            analytics_input(payload),
            action=BLOCK_DEFAULT_ACTIONS.get("analytics"),
        ),
    }
    return ok_envelope("principal_dashboard", payload, blocks)
