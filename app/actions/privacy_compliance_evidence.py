"""privacy_compliance_evidence — REUSE audit, document_engine, hasher, capture."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import (
    capture_input,
    document_engine_input,
    file_hasher_input,
    gdpr_audit_input,
    notification_input,
    storage_input,
    validation_input,
)
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, file.local.read, file.input_document, database.sql
# WRITES: caller.output, file.local.write, database.sql, notification.outbound
# NEVER: inventing unverified Store block ids

BLOCK_IDS = [
    "audit",
    "document_engine",
    "file_hasher",
    "capture",
    "storage",
    "validation",
    "notification",
]

BASIS_RETENTION = {
    "legitimate_interest": 2555,
    "consent": 730,
    "contract": 1825,
    "legal_obligation": 2555,
}


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Log a GDPR/privacy control event and persist verifiable evidence."""
    basis = str(payload.get("lawful_basis") or "legitimate_interest")
    if basis not in BASIS_RETENTION:
        basis = "legitimate_interest"
    prepared = {
        "audit": gdpr_audit_input(payload),
        "document_engine": document_engine_input(payload),
        "file_hasher": file_hasher_input(payload),
        "capture": capture_input(payload),
        "storage": storage_input(payload),
        "validation": validation_input(payload),
        "notification": notification_input(payload),
    }
    blocks: Dict[str, Any] = {}
    for block_id in BLOCK_IDS:
        blocks[block_id] = execute(
            block_id,
            prepared[block_id],
            action=BLOCK_DEFAULT_ACTIONS.get(block_id),
        )
    record = {
        **payload,
        "privacy_control": {
            "lawful_basis": basis,
            "retention_days": BASIS_RETENTION[basis],
            "fail_closed_auth": True,
            "principal_audit": True,
            "cors_allowlist_only": True,
            "data_subject": payload.get("data_subject") or "sample",
            "channel": "mcp",
        },
    }
    return ok_envelope("privacy_compliance_evidence", record, blocks)
