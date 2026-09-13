"""stock_alerts — REUSE notification + event_bus. MCP-only staff notices."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import event_bus_input, notification_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, env.process, config.runtime, network.http.outbound, credential.env
# WRITES: caller.output, notification.outbound
# NEVER: (none)

BLOCK_IDS = ["notification", "event_bus"]
CAPABILITY_ID = "stock_alerts"
ALERT_KINDS = ("below_reorder", "stalled_order")


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Publish a stock/order alert on the bus and notify staff over MCP."""
    kind = str(payload.get("alert_kind") or "below_reorder")
    if kind not in ALERT_KINDS:
        kind = "below_reorder"
    sku = str(payload.get("sku") or payload.get("reference") or "sample")
    record = {
        **payload,
        "sku": sku,
        "alert_kind": kind,
        "capability": CAPABILITY_ID,
        "channel": "mcp",
        "event": f"retail.alert.{kind}",
    }
    blocks = {
        "notification": execute(
            "notification",
            notification_input(record),
            action=BLOCK_DEFAULT_ACTIONS.get("notification"),
        ),
        "event_bus": execute(
            "event_bus",
            event_bus_input(record),
            action=BLOCK_DEFAULT_ACTIONS.get("event_bus"),
        ),
    }
    record["alert"] = {
        "sku": sku,
        "kind": kind,
        "channel": "mcp",
        "published": True,
    }
    return ok_envelope(CAPABILITY_ID, record, blocks)
