"""dynamic_pricing — REUSE formula_executor + analytics. Domain night rate."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import prepare_block_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.domain import allowed_next_status, envelope_status, night_rate
from app.persist import ok_envelope

# READS: caller.input, env.process, config.runtime
# WRITES: caller.output
# NEVER: (none)

BLOCK_IDS = ["formula_executor", "analytics"]
CAPABILITY_ID = "dynamic_pricing"
SEASONS = ("peak", "shoulder", "off")


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Price a stay from season × envelope status; persist a real night_rate."""
    status = envelope_status(payload)
    season = str(payload.get("season") or "peak")
    if season not in SEASONS:
        season = "peak"
    rate_plan = str(payload.get("rate_plan") or payload.get("reference") or "sample")
    rate = night_rate(season, status)
    record = {
        **payload,
        "status": status,
        "season": season,
        "rate_plan": rate_plan,
        "night_rate": rate,
        "base_rate": 200.0,
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
    record["pricing"] = {
        "season": season,
        "rate_plan": rate_plan,
        "night_rate": rate,
        "formula": "base_rate * season_factor * status_adj",
        "allowed_next_status": list(allowed_next_status(status)),
        "priced": True,
    }
    return ok_envelope(CAPABILITY_ID, record, blocks)
