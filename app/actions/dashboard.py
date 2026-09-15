"""dashboard — REUSE Store dashboard. Sales-team board of leads and inventory."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import dashboard_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.domain import (
    allowed_next_status,
    board_horizon,
    envelope_status,
    inventory_score,
    lead_count,
)
from app.persist import ok_envelope

# READS: caller.input, config.runtime
# WRITES: caller.output
# NEVER: (none)

BLOCK_IDS = ["dashboard"]
CAPABILITY_ID = "dashboard"


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Render the sales board and persist the dashboard snapshot."""
    payload = dict(payload or {})
    status = envelope_status(payload)
    horizon = board_horizon(payload)
    view_name = str(payload.get("view_name") or payload.get("reference") or "sample")
    leads = lead_count(horizon)
    score = inventory_score(status, "new")
    record = {
        **payload,
        "reference": str(payload.get("reference") or "sample"),
        "status": status,
        "view_name": view_name,
        "horizon": horizon,
        "lead_count": leads,
        "inventory_score": score,
        "widgets": ["leads", "inventory", "test_drives", "financing"],
        "capability": CAPABILITY_ID,
        "channel": "mcp",
    }
    prepared = dashboard_input(record)
    blocks: Dict[str, Any] = {}
    for block_id in BLOCK_IDS:
        blocks[block_id] = execute(
            block_id,
            prepared,
            action=BLOCK_DEFAULT_ACTIONS.get(block_id),
        )
    record["board"] = {
        "view_name": view_name,
        "horizon": horizon,
        "lead_count": leads,
        "inventory_score": score,
        "allowed_next_status": list(allowed_next_status(status)),
        "theme": "light",
    }
    return ok_envelope(CAPABILITY_ID, record, blocks)
