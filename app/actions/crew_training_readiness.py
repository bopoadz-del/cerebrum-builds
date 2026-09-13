"""crew_training_readiness — REUSE team + notification + workflow. Currency windows."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import prepare_block_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, env.process, config.runtime
# WRITES: caller.output, notification.outbound
# NEVER: (none)

BLOCK_IDS = ["team", "notification", "workflow"]
CAPABILITY_ID = "crew_training_readiness"
ROLES = ("captain", "first_officer", "cabin")
ITEMS = ("line_check", "sim", "crm")
CURRENCY_DAYS = {"line_check": 365, "sim": 180, "crm": 730}


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Stand up a crew team, notify over MCP, and run the currency workflow."""
    role = str(payload.get("crew_role") or "captain")
    if role not in ROLES:
        role = "captain"
    item = str(payload.get("currency_item") or "line_check")
    if item not in ITEMS:
        item = "line_check"
    days = CURRENCY_DAYS[item]
    ready = payload.get("status") != "closed"
    record = {
        **payload,
        "crew_role": role,
        "currency_item": item,
        "capability": CAPABILITY_ID,
        "channel": "mcp",
        "event": f"aviation.crew.{item}",
    }
    blocks: Dict[str, Any] = {}
    for block_id in BLOCK_IDS:
        blocks[block_id] = execute(
            block_id,
            prepare_block_input(block_id, record),
            action=BLOCK_DEFAULT_ACTIONS.get(block_id),
        )
    record["readiness"] = {
        "crew_role": role,
        "currency_item": item,
        "window_days": days,
        "ready": ready,
        "notified": True,
    }
    return ok_envelope(CAPABILITY_ID, record, blocks)
