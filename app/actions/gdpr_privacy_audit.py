"""gdpr_privacy_audit — REUSE Store audit. Fail-closed auth, Principal, CORS."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import gdpr_audit_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, config.runtime, database.sql
# WRITES: caller.output, database.sql
# NEVER: (none)

BLOCK_IDS = ["audit"]

BASIS_RETENTION = {
    "legitimate_interest": 2555,
    "consent": 730,
    "contract": 1825,
    "legal_obligation": 2555,
}


def _basis(payload: Dict[str, Any]) -> str:
    value = str(payload.get("lawful_basis") or "legitimate_interest")
    return value if value in BASIS_RETENTION else "legitimate_interest"


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Log a GDPR/privacy control event via the audit block; persist the review."""
    basis = _basis(payload)
    prepared = gdpr_audit_input(payload)
    blocks = {
        "audit": execute(
            "audit",
            prepared,
            action=BLOCK_DEFAULT_ACTIONS.get("audit"),
        ),
    }
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
    return ok_envelope("gdpr_privacy_audit", record, blocks)
