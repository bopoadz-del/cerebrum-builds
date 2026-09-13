"""portfolio_program_governance — REUSE workflow, dashboard, team. Persist."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import prepare_block_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, config.runtime, team.state
# WRITES: caller.output, file.local.write
# NEVER: inventing unverified Store block ids

BLOCK_IDS = ["workflow", "dashboard", "team"]

HORIZON_WEIGHT = {"strategic": 3, "tactical": 2, "runway": 1}
STATUS_VALUES = ("open", "in_progress", "closed")


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Roll a strategic initiative into the enterprise tech portfolio view."""
    status = str(payload.get("status") or "open")
    if status not in STATUS_VALUES:
        status = "open"
    horizon = str(payload.get("horizon") or "strategic")
    if horizon not in HORIZON_WEIGHT:
        horizon = "strategic"
    initiative = str(payload.get("initiative_name") or payload.get("reference") or "sample")
    blocks: Dict[str, Any] = {}
    for block_id in BLOCK_IDS:
        blocks[block_id] = execute(
            block_id,
            prepare_block_input(block_id, payload),
            action=BLOCK_DEFAULT_ACTIONS.get(block_id),
        )
    record = {
        **payload,
        "status": status,
        "portfolio_card": {
            "initiative": initiative,
            "horizon": horizon,
            "owner_surface": "enterprise_and_corporate_technology",
            "health_score": {"open": 20, "in_progress": 60, "closed": 100}[status]
            + HORIZON_WEIGHT[horizon] * 10,
            "tracks_value_realization": True,
            "not_a_booking_engine": True,
            "carrier": "RX",
        },
    }
    return ok_envelope("portfolio_program_governance", record, blocks)
