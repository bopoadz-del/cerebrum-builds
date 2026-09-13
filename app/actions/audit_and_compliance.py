"""audit_and_compliance — REUSE audit + file_hasher. Immutable trail persist."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import audit_input, file_hasher_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, config.runtime, database.sql, file.local.read
# WRITES: caller.output, database.sql
# NEVER: inventing unverified Store block ids

BLOCK_IDS = ["audit", "file_hasher"]


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Log a chained audit event and hash constructed evidence; persist."""
    logged = execute(
        "audit",
        audit_input(payload),
        action=BLOCK_DEFAULT_ACTIONS.get("audit"),
    )
    hashed = execute(
        "file_hasher",
        file_hasher_input(payload),
        action=BLOCK_DEFAULT_ACTIONS.get("file_hasher"),
    )
    hashes = (hashed.get("result") or {}).get("hashes") if isinstance(hashed, dict) else {}
    record = {
        **payload,
        "compliance": {
            "event_action": payload.get("event_action") or "persist",
            "evidence_label": payload.get("evidence_label") or "sample",
            "sha256": (hashes or {}).get("sha256"),
            "logged": True,
        },
    }
    return ok_envelope(
        "audit_and_compliance",
        record,
        {"audit": logged, "file_hasher": hashed},
    )
