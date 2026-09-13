"""audit — persistable keyword-fallback capability. REUSE audit block."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import audit_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.domain import allowed_next_status, audit_retention_days, envelope_status
from app.persist import ok_envelope

# READS: caller.input, config.runtime, database.sql
# WRITES: caller.output, database.sql
# NEVER: (none)

BLOCK_IDS = ["audit"]
CAPABILITY_ID = "audit"
CATEGORIES = ("clinical", "billing", "access")


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Persist a clinic audit event with category retention — not a phantom block."""
    status = envelope_status(payload)
    event_category = str(payload.get("event_category") or "clinical")
    if event_category not in CATEGORIES:
        event_category = "clinical"
    resource_label = str(
        payload.get("resource_label") or payload.get("reference") or "sample"
    )
    retention = audit_retention_days(event_category)
    record = {
        **payload,
        "status": status,
        "event_category": event_category,
        "resource_label": resource_label,
        "category": event_category,
        "event_action": payload.get("event_action") or "clinic_audit",
        "retention_days": retention,
        "capability": CAPABILITY_ID,
        "channel": "mcp",
    }
    blocks = {
        "audit": execute(
            "audit",
            audit_input(record),
            action=BLOCK_DEFAULT_ACTIONS.get("audit"),
        ),
    }
    record["audit_event"] = {
        "event_category": event_category,
        "resource_label": resource_label,
        "retention_days": retention,
        "allowed_next_status": list(allowed_next_status(status)),
        "logged": True,
    }
    return ok_envelope(CAPABILITY_ID, record, blocks)
