"""ops_dashboard — REUSE dashboard + analytics + database. One-screen ops view."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import prepare_block_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, config.runtime, llm.provider, database.sql
# WRITES: caller.output, database.sql
# NEVER: (none)

BLOCK_IDS = ["dashboard", "analytics", "database"]
CAPABILITY_ID = "ops_dashboard"
HORIZONS = ("today", "week", "month")


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Render the ops board, track a sample metric, and persist the view."""
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
        "widgets": ["stock_on_hand", "open_orders", "alerts"],
        "theme": "light",
    }
    return ok_envelope(CAPABILITY_ID, record, blocks)
