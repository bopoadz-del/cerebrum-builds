"""inventory_tracking — REUSE database + validation + audit. Persist SKU counts."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import prepare_block_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, env.process, config.runtime, database.sql
# WRITES: caller.output, database.sql
# NEVER: (none)

BLOCK_IDS = ["database", "validation", "audit"]
CAPABILITY_ID = "inventory_tracking"


def _qty(payload: Dict[str, Any], key: str) -> int:
    raw = payload.get(key)
    if raw in (None, "", "sample"):
        return 0
    try:
        return max(0, int(raw))
    except (TypeError, ValueError):
        return 0


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a stock count, query the SKU table, and audit the persist."""
    quantity = _qty(payload, "quantity_on_hand")
    threshold = _qty(payload, "reorder_threshold")
    sku = str(payload.get("sku") or payload.get("reference") or "sample")
    record = {
        **payload,
        "sku": sku,
        "quantity_on_hand": quantity,
        "reorder_threshold": threshold,
        "below_reorder": quantity <= threshold,
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
    return ok_envelope(CAPABILITY_ID, record, blocks)
