"""audit — REUSE audit. Immutable log of listing, lead, and test-drive events."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import audit_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.domain import allowed_next_status, audit_weight, envelope_status, event_kind_of
from app.persist import ok_envelope

# READS: caller.input, config.runtime, database.sql
# WRITES: caller.output, database.sql
# NEVER: (none)

BLOCK_IDS = ["audit"]
CAPABILITY_ID = "audit"


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Chain-hash a dealership mutation and persist the audit row."""
    status = envelope_status(payload)
    event_kind = event_kind_of(payload)
    resource_label = str(payload.get("resource_label") or payload.get("reference") or "sample")
    weight = audit_weight(event_kind)
    record = {
        **payload,
        "status": status,
        "event_kind": event_kind,
        "resource_label": resource_label,
        "audit_weight": weight,
        "retention_days": 2555,
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
        "event_kind": event_kind,
        "resource_label": resource_label,
        "audit_weight": weight,
        "retention_days": 2555,
        "allowed_next_status": list(allowed_next_status(status)),
        "chained": True,
    }
    return ok_envelope(CAPABILITY_ID, record, blocks)
