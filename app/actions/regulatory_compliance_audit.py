"""regulatory_compliance_audit — REUSE audit + file_hasher. Evidence integrity."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import audit_input, file_hasher_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, config.runtime, database.sql
# WRITES: caller.output, database.sql
# NEVER: (none)

BLOCK_IDS = ["audit", "file_hasher"]
CAPABILITY_ID = "regulatory_compliance_audit"
REGULATIONS = ("part_121", "part_135", "easa_ops")
SEVERITIES = ("observation", "minor", "major")


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Hash the evidence pack and write a Principal-attributed compliance event."""
    regulation = str(payload.get("regulation") or "part_121")
    if regulation not in REGULATIONS:
        regulation = "part_121"
    severity = str(payload.get("finding_severity") or "observation")
    if severity not in SEVERITIES:
        severity = "observation"
    record = {
        **payload,
        "regulation": regulation,
        "finding_severity": severity,
        "capability": CAPABILITY_ID,
        "channel": "mcp",
        "category": "data_access",
        "event_action": "compliance_review",
    }
    blocks = {
        "audit": execute(
            "audit",
            audit_input(record),
            action=BLOCK_DEFAULT_ACTIONS.get("audit"),
        ),
        "file_hasher": execute(
            "file_hasher",
            file_hasher_input(record),
            action=BLOCK_DEFAULT_ACTIONS.get("file_hasher"),
        ),
    }
    digest = ((blocks["file_hasher"].get("result") or {}) or {}).get("digest")
    record["compliance"] = {
        "regulation": regulation,
        "finding_severity": severity,
        "evidence_digest": digest,
        "finding_open": record.get("status") != "closed",
    }
    return ok_envelope(CAPABILITY_ID, record, blocks)
