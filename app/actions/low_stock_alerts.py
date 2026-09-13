"""low_stock_alerts — REUSE notification, event_bus, queue."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import event_bus_input, notification_input, queue_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, env.process, config.runtime, network.http.outbound, credential.env, block.peer, memory.cache, queue.jobs
# WRITES: caller.output, network.smtp.outbound, email.outbound, notification.outbound, queue.jobs
# NEVER: (none)

BLOCK_IDS = ["notification", "event_bus", "queue"]


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Notify staff of a low-stock SKU via MCP + event_bus + queue, then persist."""
    record = {**payload, "capability": "low_stock_alerts"}
    topic = f"inventory.low_stock.{record.get('sku') or record.get('reference') or 'sample'}"
    blocks = {
        "notification": execute(
            "notification",
            notification_input(record),
            action=BLOCK_DEFAULT_ACTIONS.get("notification"),
        ),
        "event_bus": execute(
            "event_bus",
            event_bus_input(record, topic=topic),
            action=BLOCK_DEFAULT_ACTIONS.get("event_bus"),
        ),
        "queue": execute(
            "queue",
            queue_input(record),
            action=BLOCK_DEFAULT_ACTIONS.get("queue"),
        ),
    }
    return ok_envelope("low_stock_alerts", record, blocks)
