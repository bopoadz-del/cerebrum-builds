"""operational_analytics_dashboard — REUSE dashboard + analytics. Dispatch/delay KPIs."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import analytics_input, dashboard_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, config.runtime, llm.provider
# WRITES: caller.output
# NEVER: (none)

BLOCK_IDS = ["dashboard", "analytics"]

HORIZON_WINDOW = {"daily": 1, "weekly": 7, "monthly": 30}
FAMILY_BASELINE = {"dispatch": 97.4, "delay": 12.0, "mx_backlog": 8.0}


def _horizon(payload: Dict[str, Any]) -> str:
    value = str(payload.get("horizon") or "daily")
    return value if value in HORIZON_WINDOW else "daily"


def _family(payload: Dict[str, Any]) -> str:
    value = str(payload.get("metric_family") or "dispatch")
    return value if value in FAMILY_BASELINE else "dispatch"


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Render the ops dashboard and track one aviation KPI event."""
    horizon = _horizon(payload)
    family = _family(payload)
    baseline = FAMILY_BASELINE[family]
    dash_payload = {
        **payload,
        "user_id": str(payload.get("actor") or "operator"),
    }
    blocks = {
        "dashboard": execute(
            "dashboard",
            dashboard_input(dash_payload),
            action=BLOCK_DEFAULT_ACTIONS.get("dashboard"),
        ),
        "analytics": execute(
            "analytics",
            analytics_input(payload, f"aviation.{family}", baseline),
            action=BLOCK_DEFAULT_ACTIONS.get("analytics"),
        ),
    }
    record = {
        **payload,
        "ops_kpi": {
            "horizon": horizon,
            "window_days": HORIZON_WINDOW[horizon],
            "metric_family": family,
            "baseline": baseline,
            "unit": "percent" if family == "dispatch" else "count",
            "channel": "mcp",
        },
    }
    return ok_envelope("operational_analytics_dashboard", record, blocks)
