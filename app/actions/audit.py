"""audit — REUSE Store audit. Follow-up notes and mutation trail."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import audit_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.domain import allowed_next_status, envelope_status, inquiry_priority
from app.persist import ok_envelope

# READS: caller.input, config.runtime, database.sql
# WRITES: caller.output, database.sql
# NEVER: (none)

BLOCK_IDS = ["audit"]
CAPABILITY_ID = "audit"


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Log a lead follow-up note and persist the audit record."""
    payload = dict(payload or {})
    status = envelope_status(payload)
    note = str(payload.get("note") or payload.get("reference") or "sample")
    category = str(payload.get("category") or "data_access")
    record = {
        **payload,
        "reference": str(payload.get("reference") or "sample"),
        "status": status,
        "note": note,
        "category": category,
        "follow_up": inquiry_priority(status),
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
    record["trail"] = {
        "note": note,
        "category": category,
        "follow_up": inquiry_priority(status),
        "allowed_next_status": list(allowed_next_status(status)),
        "immutable": True,
    }
    return ok_envelope(CAPABILITY_ID, record, blocks)
