"""incident_evidence_tracking — REUSE capture + file_hasher + storage."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import capture_input, file_hasher_input, storage_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.domain import allowed_next_status, envelope_status, evidence_severity
from app.persist import ok_envelope

# READS: caller.input, file.local.read, file.input_image, env.process, config.runtime
# WRITES: caller.output, file.local.write
# NEVER: (none)

BLOCK_IDS = ["capture", "file_hasher", "storage"]
CAPABILITY_ID = "incident_evidence_tracking"
KINDS = ("photo", "report", "sensor")


def _inner(block_result: Dict[str, Any]) -> Dict[str, Any]:
    body = block_result.get("result") if isinstance(block_result, dict) else {}
    return body if isinstance(body, dict) else {}


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Capture incident text, hash the file, and chain the evidence record."""
    status = envelope_status(payload)
    kind = str(payload.get("evidence_kind") or "photo")
    if kind not in KINDS:
        kind = "photo"
    note = str(payload.get("incident_note") or payload.get("reference") or "sample")
    severity = evidence_severity(kind)
    record = {
        **payload,
        "status": status,
        "incident_note": note,
        "evidence_kind": kind,
        "severity": severity,
        "capability": CAPABILITY_ID,
        "channel": "mcp",
    }
    blocks = {
        "capture": execute(
            "capture",
            capture_input(record),
            action=BLOCK_DEFAULT_ACTIONS.get("capture"),
        ),
        "file_hasher": execute(
            "file_hasher",
            file_hasher_input(record),
            action=BLOCK_DEFAULT_ACTIONS.get("file_hasher"),
        ),
        "storage": execute(
            "storage",
            storage_input(record),
            action=BLOCK_DEFAULT_ACTIONS.get("storage"),
        ),
    }
    captured = _inner(blocks["capture"])
    hashed = _inner(blocks["file_hasher"])
    hashes = hashed.get("hashes") if isinstance(hashed.get("hashes"), dict) else {}
    record["evidence"] = {
        "incident_note": note,
        "kind": kind,
        "severity": severity,
        "capture_id": captured.get("capture_id"),
        "sha256": hashes.get("sha256"),
        "chain": ["capture", "file_hasher", "storage"],
        "allowed_next_status": list(allowed_next_status(status)),
        "hashed": True,
        "stored": True,
        "posture": "P1",
    }
    return ok_envelope(CAPABILITY_ID, record, blocks)
