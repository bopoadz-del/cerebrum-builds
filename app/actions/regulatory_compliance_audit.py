"""regulatory_compliance_audit — REUSE audit + file_hasher. Evidence pack hash."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import audit_input, file_hasher_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, config.runtime, database.sql, file.local.read
# WRITES: caller.output, database.sql
# NEVER: (none)

BLOCK_IDS = ["audit", "file_hasher"]

REGULATION_LABEL = {
    "far_121": "14 CFR Part 121",
    "easa_part_ops": "EASA Part-ORO",
    "gaca": "GACA aviation ops",
}
SCOPE_EVIDENCE = {
    "airworthiness": "amp_and_ad_status",
    "ops": "ops_manual_revision",
    "training": "crew_training_folder",
}


def _regulation(payload: Dict[str, Any]) -> str:
    value = str(payload.get("regulation") or "far_121")
    return value if value in REGULATION_LABEL else "far_121"


def _scope(payload: Dict[str, Any]) -> str:
    value = str(payload.get("audit_scope") or "airworthiness")
    return value if value in SCOPE_EVIDENCE else "airworthiness"


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Hash the compliance evidence pack and log the regulatory audit event."""
    regulation = _regulation(payload)
    scope = _scope(payload)
    reference = str(payload.get("reference") or "sample")
    pack_text = (
        f"compliance pack {reference} regulation={REGULATION_LABEL[regulation]} "
        f"scope={scope} evidence={SCOPE_EVIDENCE[scope]}"
    )
    hasher_body = file_hasher_input(payload, body=pack_text)
    audit_body = audit_input(
        {
            **payload,
            "category": "admin",
            "event_action": "regulatory_audit",
            "capability": "regulatory_compliance_audit",
        }
    )
    blocks = {
        "audit": execute(
            "audit",
            audit_body,
            action=BLOCK_DEFAULT_ACTIONS.get("audit"),
        ),
        "file_hasher": execute(
            "file_hasher",
            hasher_body,
            action=BLOCK_DEFAULT_ACTIONS.get("file_hasher"),
        ),
    }
    digest = ((blocks["file_hasher"].get("result") or {}) if isinstance(blocks["file_hasher"], dict) else {})
    hashes = digest.get("hashes") if isinstance(digest, dict) else None
    record = {
        **payload,
        "compliance_finding": {
            "regulation": regulation,
            "regulation_label": REGULATION_LABEL[regulation],
            "audit_scope": scope,
            "evidence_class": SCOPE_EVIDENCE[scope],
            "pack_sha256": (hashes or {}).get("sha256") if isinstance(hashes, dict) else None,
            "channel": "mcp",
        },
    }
    return ok_envelope("regulatory_compliance_audit", record, blocks)
