"""order_management — REUSE workflow + queue + database + notification."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import prepare_block_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, env.process, config.runtime, memory.cache, queue.jobs
# WRITES: caller.output, queue.jobs, notification.outbound
# NEVER: (none)

BLOCK_IDS = ["workflow", "queue", "database", "notification"]
CAPABILITY_ID = "order_management"
STAGES = ("received", "picking", "packed", "shipped")


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Run the fulfillment pipeline: enqueue, persist, notify over MCP."""
    stage = str(payload.get("fulfillment_stage") or "received")
    if stage not in STAGES:
        stage = "received"
    order_number = str(payload.get("order_number") or payload.get("reference") or "sample")
    record = {
        **payload,
        "order_number": order_number,
        "fulfillment_stage": stage,
        "capability": CAPABILITY_ID,
        "channel": "mcp",
    }
    # Workflow input already carries result + prepared queue/notification children.
    blocks: Dict[str, Any] = {}
    for block_id in BLOCK_IDS:
        blocks[block_id] = execute(
            block_id,
            prepare_block_input(block_id, record),
            action=BLOCK_DEFAULT_ACTIONS.get(block_id),
        )
    record["fulfillment"] = {
        "order_number": order_number,
        "stage": stage,
        "queued": True,
        "notified": True,
        "pipeline": "order-fulfill",
    }
    return ok_envelope(CAPABILITY_ID, record, blocks)
