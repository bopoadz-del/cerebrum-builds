"""audit — REUSE Store audit block. Factory persist envelope."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import audit_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.domain import normalize_audit
from app.persist import ok_envelope

# READS: caller.input, config.runtime, database.sql
# WRITES: caller.output, database.sql
# NEVER: (none)

BLOCK_IDS = ["audit"]
CAPABILITY_ID = "audit"


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Log an audit event via execute(action=) then persist the capability record."""
    record = normalize_audit(payload if isinstance(payload, dict) else {})
    record["capability"] = CAPABILITY_ID
    prepared = audit_input(record)
    blocks: Dict[str, Any] = {}
    for block_id in BLOCK_IDS:
        blocks[block_id] = execute(
            block_id,
            prepared,
            action=BLOCK_DEFAULT_ACTIONS.get(block_id),
        )
    logged = blocks.get("audit") or {}
    inner = logged.get("result") if isinstance(logged, dict) else {}
    if isinstance(inner, dict):
        record["event_id"] = inner.get("event_id")
        record["sequence"] = inner.get("sequence")
        record["logged"] = inner.get("logged")
    return ok_envelope(CAPABILITY_ID, record, blocks)
