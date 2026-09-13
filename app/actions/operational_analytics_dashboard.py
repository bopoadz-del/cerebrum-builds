"""operational_analytics_dashboard — REUSE dashboard + analytics. OTP / delay views."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import analytics_input, dashboard_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, config.runtime
# WRITES: caller.output
# NEVER: (none)

BLOCK_IDS = ["dashboard", "analytics"]
CAPABILITY_ID = "operational_analytics_dashboard"
HORIZONS = {"today": 24, "week": 168, "month": 720}


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Track an ops metric and render the operator dashboard for the chosen horizon."""
    horizon = str(payload.get("horizon") or "today")
    if horizon not in HORIZONS:
        horizon = "today"
    view_name = str(payload.get("view_name") or payload.get("reference") or "sample")
    window_hours = HORIZONS[horizon]
    record = {
        **payload,
        "view_name": view_name,
        "horizon": horizon,
        "capability": CAPABILITY_ID,
        "channel": "mcp",
    }
    blocks = {
        "dashboard": execute(
            "dashboard",
            dashboard_input(record),
            action=BLOCK_DEFAULT_ACTIONS.get("dashboard"),
        ),
        "analytics": execute(
            "analytics",
            analytics_input(record),
            action=BLOCK_DEFAULT_ACTIONS.get("analytics"),
        ),
    }
    record["ops_view"] = {
        "view_name": view_name,
        "horizon": horizon,
        "window_hours": window_hours,
        "otp_basis": "departures",
        "tracked": True,
    }
    return ok_envelope(CAPABILITY_ID, record, blocks)
