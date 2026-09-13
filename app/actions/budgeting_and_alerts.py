"""budgeting_and_alerts — REUSE formula_executor + notification + workflow."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import formula_executor_input, notification_input, workflow_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, env.process, config.runtime
# WRITES: caller.output, notification.outbound
# NEVER: forwarding the schema sample as an event_bus workflow step input

BLOCK_IDS = ["formula_executor", "notification", "workflow"]


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Compute a budget variance, notify over MCP, run the prepared workflow."""
    computed = execute(
        "formula_executor",
        formula_executor_input(payload),
        action=BLOCK_DEFAULT_ACTIONS.get("formula_executor"),
    )
    notified = execute(
        "notification",
        notification_input(payload),
        action=BLOCK_DEFAULT_ACTIONS.get("notification"),
    )
    piped = execute(
        "workflow",
        workflow_input(payload),
        action=BLOCK_DEFAULT_ACTIONS.get("workflow"),
    )
    record = {
        **payload,
        "budget_watch": {
            "budget_name": payload.get("budget_name") or "sample",
            "threshold_pct": payload.get("threshold_pct") or 1,
            "alert_channel": "mcp",
            "workflow_pipeline": (piped.get("result") or {}).get("pipeline_id")
            if isinstance(piped, dict)
            else None,
        },
    }
    return ok_envelope(
        "budgeting_and_alerts",
        record,
        {
            "formula_executor": computed,
            "notification": notified,
            "workflow": piped,
        },
    )
