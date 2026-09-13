"""airport_readiness — REUSE analytics. Persist stand/turnaround readiness."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import prepare_block_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, config.runtime, llm.provider
# WRITES: caller.output
# NEVER: (none)

BLOCK_IDS = ["analytics"]
CAPABILITY_ID = "airport_readiness"
WINDOWS = ("turnaround", "shift", "day")


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Track a readiness metric for a stand and persist the snapshot."""
    window = str(payload.get("readiness_window") or "turnaround")
    if window not in WINDOWS:
        window = "turnaround"
    stand_id = str(payload.get("stand_id") or payload.get("reference") or "sample")
    record = {
        **payload,
        "stand_id": stand_id,
        "readiness_window": window,
        "readiness_score": 1.0,
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
        "tracked": True,
        "metric": "airport_ops_events",
    }
    return ok_envelope(CAPABILITY_ID, record, blocks)
