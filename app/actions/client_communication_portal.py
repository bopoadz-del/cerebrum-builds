"""client_communication_portal — REUSE notification + event_bus + knowledge."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import event_bus_input, knowledge_input, notification_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.domain import allowed_next_status, comms_priority, envelope_status
from app.persist import ok_envelope

# READS: caller.input, env.process, config.runtime, llm.provider
# WRITES: caller.output, notification.outbound
# NEVER: (none)

BLOCK_IDS = ["notification", "event_bus", "knowledge"]
CAPABILITY_ID = "client_communication_portal"
KINDS = ("reminder", "result", "billing")


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Publish a client notice on MCP and persist the comms record."""
    status = envelope_status(payload)
    message_kind = str(payload.get("message_kind") or "reminder")
    if message_kind not in KINDS:
        message_kind = "reminder"
    client_name = str(payload.get("client_name") or payload.get("reference") or "sample")
    priority = comms_priority(message_kind)
    record = {
        **payload,
        "status": status,
        "message_kind": message_kind,
        "client_name": client_name,
        "event": f"vetcare.comms.{message_kind}",
        "priority": priority,
        "capability": CAPABILITY_ID,
        "channel": "mcp",
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
        "knowledge": execute(
            "knowledge",
            knowledge_input(record),
            action=BLOCK_DEFAULT_ACTIONS.get("knowledge"),
        ),
    }
    record["comms"] = {
        "client_name": client_name,
        "message_kind": message_kind,
        "priority": priority,
        "channel": "mcp",
        "published": True,
        "allowed_next_status": list(allowed_next_status(status)),
        "notified": True,
    }
    return ok_envelope(CAPABILITY_ID, record, blocks)
