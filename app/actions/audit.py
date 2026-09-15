"""audit — REUSE Store audit block (action=log via BLOCK_DEFAULT_ACTIONS)."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import audit_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.domain import envelope_status
from app.persist import ok_envelope

# READS: caller.input, config.runtime, database.sql
# WRITES: caller.output, database.sql
# NEVER: (none)

BLOCK_IDS = ["audit"]
CAPABILITY_ID = "audit"
EVENT_KINDS = ("create", "update", "delete")


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Log a constructed audit event, then persist the capability record."""
    status = envelope_status(payload)
    event_kind = str(payload.get("event_kind") or "create")
    if event_kind not in EVENT_KINDS:
        event_kind = "create"
    resource_ref = str(payload.get("resource_ref") or payload.get("reference") or "sample")
    record = {
        **payload,
        "status": status,
        "event_kind": event_kind,
        "resource_ref": resource_ref,
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
    record["audit_event"] = {
        "event_kind": event_kind,
        "resource_ref": resource_ref,
        "logged": bool(isinstance(inner, dict) and inner.get("logged")),
        "event_id": inner.get("event_id") if isinstance(inner, dict) else None,
        "immutable": True,
    }
    return ok_envelope(CAPABILITY_ID, record, blocks)
