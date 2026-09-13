"""financial_dashboard — REUSE dashboard + analytics. Cash-flow rollup persist."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import analytics_input, dashboard_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, config.runtime
# WRITES: caller.output
# NEVER: inventing unverified Store block ids; a second vector store

BLOCK_IDS = ["dashboard", "analytics"]


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Render the operator dashboard and track one spend metric; persist."""
    dash = execute(
        "dashboard",
        dashboard_input(payload),
        action=BLOCK_DEFAULT_ACTIONS.get("dashboard"),
    )
    tracked = execute(
        "analytics",
        analytics_input(payload),
        action=BLOCK_DEFAULT_ACTIONS.get("analytics"),
    )
    record = {
        **payload,
        "dashboard_view": {
            "period": payload.get("period") or "month",
            "currency": payload.get("currency") or "USD",
            "widgets": (dash.get("result") or {}).get("widgets")
            if isinstance(dash, dict)
            else [],
            "metric": "ledgerflow.spend",
        },
    }
    return ok_envelope(
        "financial_dashboard",
        record,
        {"dashboard": dash, "analytics": tracked},
    )
