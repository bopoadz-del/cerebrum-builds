"""audit — REUSE Store audit block with factory-grounded persist."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import audit_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.domain import envelope_status, normalize_audit
from app.persist import ok_envelope

# READS: caller.input, config.runtime, database.sql
# WRITES: caller.output, database.sql
# NEVER: (none)

CAPABILITY_ID = "audit"
BLOCK_IDS = ["audit"]


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Log an immutable audit event and persist the capability record."""
    incoming = dict(payload or {})
    incoming.setdefault("reference", "sample")
    incoming.setdefault("status", envelope_status(incoming))
    incoming.setdefault("event_action", incoming.get("capability") or "audit")
    incoming.setdefault("resource", incoming.get("reference") or "sample")
    record = normalize_audit(incoming)
    prepared = audit_input(record)
    blocks: Dict[str, Any] = {}
    for block_id in BLOCK_IDS:
        blocks[block_id] = execute(
            block_id,
            prepared,
            action=BLOCK_DEFAULT_ACTIONS.get(block_id),
        )
    record["logged"] = True
    record["integrity"] = "chained"
    return ok_envelope(CAPABILITY_ID, record, blocks)
