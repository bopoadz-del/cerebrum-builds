"""incident_evidence_tracking — REUSE capture + file_hasher + storage."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import capture_input, file_hasher_input, storage_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, file.local.read, file.input_image, env.process, config.runtime
# WRITES: caller.output, file.local.write
# NEVER: (none)

BLOCK_IDS = ["capture", "file_hasher", "storage"]
CAPABILITY_ID = "incident_evidence_tracking"
KINDS = ("photo", "report", "sensor")


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Extract incident text, hash the evidence file, and persist storage."""
    kind = str(payload.get("evidence_kind") or "photo")
    if kind not in KINDS:
        kind = "photo"
    note = str(payload.get("incident_note") or payload.get("reference") or "sample")
    record = {
        **payload,
        "incident_note": note,
        "evidence_kind": kind,
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
    record["evidence"] = {
        "incident_note": note,
        "kind": kind,
        "hashed": True,
        "stored": True,
        "posture": "P1",
    }
    return ok_envelope(CAPABILITY_ID, record, blocks)
