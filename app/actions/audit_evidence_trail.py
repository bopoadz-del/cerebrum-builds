"""Capability audit_evidence_trail — audit entries, evidence and integrity hashes.

Written by the factory WRITER role (codewhale exec)

Blocks are invoked through the local dispatch runtime (``app.dispatch.execute``)
against the block source vendored at build time — this module makes no network
call and never persists: the ROUTE writes the tenant-scoped record after
``handle()`` reports success (Phase 2 §0.2).

Pipeline:
  * ``audit``            — appends the immutable trail entry (stock change,
    delivery completion, document upload, procedure acknowledgment);
  * ``evidence_verifier``— stores the integrity record for the evidence text;
  * ``file_hasher``      — hashes the evidence document on disk;
  * ``database``         — records the trail row;
  * ``storage``          — stores the evidence text under ``STORAGE_PATH``.

The evidence text, its digest and the stored artefact all cover the same bytes,
so a later verification of a tampered record fails rather than passing.

Scope
-----
READS  the caller's payload, ``STORAGE_PATH`` (evidence artefacts).
WRITES ``STORAGE_PATH`` (evidence) through the blocks.
NEVER  network, HTTP store callbacks, ``vendor/**``.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List

from app.block_inputs import prepare_block_input
from app.dispatch import execute

CAPABILITY_ID = "audit_evidence_trail"
ENTITY = "audit_evidence_trail"
BLOCK_IDS = ["audit", "evidence_verifier", "file_hasher", "database", "storage"]
#: Each block's declared action (keyword dispatch; never inside the payload).
BLOCK_DEFAULT_ACTIONS = {
    "audit": "log",
    "evidence_verifier": "store",
    "file_hasher": "hash",
    "database": "insert",
    "storage": "store",
}
CAPABILITY_FIELDS: List[str] = [
    "reference",
    "event_type",
    "entity_name",
    "actor",
    "evidence_path",
    "content_hash",
    "notes",
    "status",
]


def _evidence_text(record: Dict[str, Any]) -> str:
    """The exact text the entry, the evidence record and the digest must cover."""
    return "%s|%s|%s|%s" % (
        str(record.get("event_type") or "event"),
        str(record.get("entity_name") or "entity"),
        str(record.get("actor") or "actor"),
        str(record.get("notes") or record.get("reference") or ""),
    )


def _evidence_identity(record: Dict[str, Any]) -> Dict[str, str]:
    text = _evidence_text(record)
    return {
        "text": text,
        "digest": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "reference": str(record.get("reference") or "sample"),
    }


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(payload) if isinstance(payload, dict) else {"value": payload}
    evidence = _evidence_identity(data)
    results: Dict[str, Any] = {}
    errors: Dict[str, str] = {}
    for block_id in BLOCK_IDS:
        prepared = prepare_block_input(block_id, data, entity=ENTITY)
        if block_id == "audit":
            prepared["event_action"] = str(data.get("event_type") or "record")
            prepared["resource"] = str(data.get("entity_name") or ENTITY)
            prepared["details"] = {
                "actor": str(data.get("actor") or ""),
                "reference": evidence["reference"],
                "digest": evidence["digest"],
            }
        if block_id == "evidence_verifier":
            prepared["content"] = evidence["text"]
            prepared["reference"] = evidence["reference"]
        if block_id == "file_hasher":
            prepared["content"] = evidence["text"]
        if block_id == "storage":
            prepared["filename"] = "%s.evidence.txt" % evidence["reference"].replace(
                "/", "_"
            )
            prepared["content"] = evidence["text"]
            prepared["metadata"] = {
                "event_type": str(data.get("event_type") or "event"),
                "digest": evidence["digest"],
            }
        result = execute(
            block_id, prepared, action=BLOCK_DEFAULT_ACTIONS.get(block_id)
        )
        results[block_id] = result
        if isinstance(result, dict) and (
            result.get("status") in ("error", "failed", "partial")
            or result.get("ok") is False
            or "error" in result
        ):
            errors[block_id] = str(result.get("error") or result)[:400]
    if errors:
        return {
            "ok": False,
            "capability": CAPABILITY_ID,
            "error": "; ".join(f"{b}: {e}" for b, e in sorted(errors.items())),
            "results": results,
        }
    return {"ok": True, "capability": CAPABILITY_ID, "results": results}
