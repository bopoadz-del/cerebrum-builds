"""operational_dashboard — REUSE dashboard + analytics + notification."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import prepare_block_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, config.runtime, env.process, network.http.outbound
# WRITES: caller.output, notification.outbound
# NEVER: (none)

BLOCK_IDS = ["dashboard", "analytics", "notification"]
CAPABILITY_ID = "operational_dashboard"
HORIZONS = ("today", "week", "month")


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Render the airside board, track a metric, and notify over MCP."""
    horizon = str(payload.get("horizon") or "today")
    if horizon not in HORIZONS:
        horizon = "today"
    view_name = str(payload.get("view_name") or payload.get("reference") or "sample")
    record = {
        **payload,
        "view_name": view_name,
        "horizon": horizon,
        "capability": CAPABILITY_ID,
        "channel": "mcp",
    }
    blocks: Dict[str, Any] = {}
    for block_id in BLOCK_IDS:
        blocks[block_id] = execute(
            block_id,
            prepare_block_input(block_id, record),
            action=BLOCK_DEFAULT_ACTIONS.get(block_id),
        )
    record["board"] = {
        "view_name": view_name,
        "horizon": horizon,
        "widgets": ["stands", "flights", "incidents"],
        "theme": "light",
        "notified": True,
    }
    return ok_envelope(CAPABILITY_ID, record, blocks)
