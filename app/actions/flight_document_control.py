"""flight_document_control — REUSE document_engine + storage + file_hasher + notification."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import (
    document_engine_input,
    file_hasher_input,
    notification_input,
    storage_input,
)
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, env.process, file.local.read
# WRITES: caller.output, file.local.write, notification.outbound
# NEVER: (none)

BLOCK_IDS = ["document_engine", "storage", "file_hasher", "notification"]
CAPABILITY_ID = "flight_document_control"
KINDS = ("mel", "qrh", "weight_balance", "release")


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Parse a controlled flight document, store it, hash it, and notify ops."""
    kind = str(payload.get("document_kind") or "mel")
    if kind not in KINDS:
        kind = "mel"
    revision = str(payload.get("revision") or payload.get("reference") or "sample")
    record = {
        **payload,
        "document_kind": kind,
        "revision": revision,
        "capability": CAPABILITY_ID,
        "channel": "mcp",
        "event": f"aviation.doc.{kind}",
    }
    blocks = {
        "document_engine": execute(
            "document_engine",
            document_engine_input(record),
            action=BLOCK_DEFAULT_ACTIONS.get("document_engine"),
        ),
        "storage": execute(
            "storage",
            storage_input(record),
            action=BLOCK_DEFAULT_ACTIONS.get("storage"),
        ),
        "file_hasher": execute(
            "file_hasher",
            file_hasher_input(record),
            action=BLOCK_DEFAULT_ACTIONS.get("file_hasher"),
        ),
        "notification": execute(
            "notification",
            notification_input(record),
            action=BLOCK_DEFAULT_ACTIONS.get("notification"),
        ),
    }
    digest = ((blocks["file_hasher"].get("result") or {}) or {}).get("digest")
    record["document"] = {
        "kind": kind,
        "revision": revision,
        "controlled": True,
        "effective": record.get("status") != "closed",
        "digest": digest,
    }
    return ok_envelope(CAPABILITY_ID, record, blocks)
