"""dashboard — REUSE dashboard. Sales-lot board of leads and inventory."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import dashboard_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.domain import (
    allowed_next_status,
    avg_list_price,
    close_rate,
    envelope_status,
    horizon_of,
    units_on_lot,
)
from app.persist import ok_envelope

# READS: caller.input, config.runtime
# WRITES: caller.output
# NEVER: (none)

BLOCK_IDS = ["dashboard"]
CAPABILITY_ID = "dashboard"


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Render lot occupancy / close-rate widgets and persist the sales board."""
    status = envelope_status(payload)
    horizon = horizon_of(payload)
    view_name = str(payload.get("view_name") or payload.get("reference") or "sample")
    units = units_on_lot(horizon)
    avg_price = avg_list_price(horizon, status)
    rate = close_rate(status)
    record = {
        **payload,
        "status": status,
        "view_name": view_name,
        "horizon": horizon,
        "units_on_lot": units,
        "avg_list_price": avg_price,
        "close_rate": rate,
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
        "units_on_lot": units,
        "avg_list_price": avg_price,
        "close_rate": rate,
        "widgets": ["inventory", "leads", "testdrives"],
        "allowed_next_status": list(allowed_next_status(status)),
        "theme": "light",
    }
    return ok_envelope(CAPABILITY_ID, record, blocks)
