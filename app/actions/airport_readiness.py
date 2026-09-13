"""airport_readiness — REUSE analytics. Persist stand/turnaround readiness."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import prepare_block_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.domain import (
    allowed_next_status,
    envelope_status,
    readiness_score,
    stand_is_degraded,
)
from app.persist import ok_envelope

# READS: caller.input, config.runtime, llm.provider
# WRITES: caller.output
# NEVER: (none)

BLOCK_IDS = ["analytics"]
CAPABILITY_ID = "airport_readiness"
WINDOWS = ("turnaround", "shift", "day")


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Score a stand from envelope status × window weight; persist the snapshot."""
    status = envelope_status(payload)
    window = str(payload.get("readiness_window") or "turnaround")
    if window not in WINDOWS:
        window = "turnaround"
    stand_id = str(payload.get("stand_id") or payload.get("reference") or "sample")
    score = readiness_score(status, window)
    degraded = stand_is_degraded(score)
    record = {
        **payload,
        "status": status,
        "stand_id": stand_id,
        "readiness_window": window,
        "readiness_score": score,
        "degraded": degraded,
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
    record["readiness"] = {
        "stand_id": stand_id,
        "window": window,
        "score": score,
        "degraded": degraded,
        "allowed_next_status": list(allowed_next_status(status)),
        "metric": "airport_ops_events",
        "tracked": True,
    }
    return ok_envelope(CAPABILITY_ID, record, blocks)
