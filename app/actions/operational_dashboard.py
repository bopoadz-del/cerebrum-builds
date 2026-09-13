"""operational_dashboard — REUSE dashboard + analytics + notification."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import prepare_block_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.domain import allowed_next_status, dashboard_band, envelope_status
from app.persist import ok_envelope

# READS: caller.input, config.runtime, env.process, network.http.outbound
# WRITES: caller.output, notification.outbound
# NEVER: (none)

BLOCK_IDS = ["dashboard", "analytics", "notification"]
CAPABILITY_ID = "operational_dashboard"
HORIZONS = ("today", "week", "month")


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Render the airside board with a horizon band and open-item count."""
    status = envelope_status(payload)
    horizon = str(payload.get("horizon") or "today")
    if horizon not in HORIZONS:
        horizon = "today"
    view_name = str(payload.get("view_name") or payload.get("reference") or "sample")
    open_items = 1 if status == "open" else 0
    in_motion = 1 if status == "in_progress" else 0
    record = {
        **payload,
        "status": status,
        "view_name": view_name,
        "horizon": horizon,
        "open_items": open_items,
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
        "band": dashboard_band(horizon),
        "widgets": ["stands", "flights", "incidents"],
        "open_items": open_items,
        "in_motion": in_motion,
        "allowed_next_status": list(allowed_next_status(status)),
        "theme": "light",
        "notified": True,
    }
    return ok_envelope(CAPABILITY_ID, record, blocks)
