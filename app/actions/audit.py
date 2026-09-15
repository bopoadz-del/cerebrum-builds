"""audit — REUSE Store audit block with factory-grounded persist."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import audit_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.domain import allowed_next_status, audit_category, envelope_status
from app.persist import ok_envelope

# READS: caller.input, config.runtime, database.sql
# WRITES: caller.output, database.sql
# NEVER: (none)

BLOCK_IDS = ["audit"]
CAPABILITY_ID = "audit"


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Log an audit event via execute(action=) and persist the capability record."""
    status = envelope_status(payload)
    category = audit_category(payload.get("category"))
    resource = str(payload.get("reference") or "sample")
    record = {
        **payload,
        "status": status,
        "category": category,
        "resource": resource,
        "event_action": str(payload.get("event_action") or "note_mutate"),
        "capability": CAPABILITY_ID,
        "channel": "mcp",
    }
    prepared = audit_input(record)
    blocks: Dict[str, Any] = {}
    for block_id in BLOCK_IDS:
        blocks[block_id] = execute(
            block_id,
            prepared,
            action=BLOCK_DEFAULT_ACTIONS.get(block_id),
        )
    result = blocks.get("audit") or {}
    inner = result.get("result") if isinstance(result, dict) else {}
    record["audit"] = {
        "category": category,
        "resource": resource,
        "logged": bool(isinstance(inner, dict) and inner.get("logged")),
        "event_id": inner.get("event_id") if isinstance(inner, dict) else None,
        "allowed_next_status": list(allowed_next_status(status)),
    }
    return ok_envelope(CAPABILITY_ID, record, blocks)
