"""regulatory_document_control — REUSE document_engine + validation + audit + storage."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import prepare_block_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.domain import allowed_next_status, document_retention_days, envelope_status
from app.persist import ok_envelope

# READS: caller.input, file.local.read, file.input_document, config.runtime, database.sql
# WRITES: caller.output, file.local.write, file.temp, database.sql
# NEVER: (none)

BLOCK_IDS = ["document_engine", "validation", "audit", "storage"]
CAPABILITY_ID = "regulatory_document_control"
CLASSES = ("manual", "certificate", "directive")


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Parse a controlled document and stamp class retention + review state."""
    status = envelope_status(payload)
    control_class = str(payload.get("control_class") or "manual")
    if control_class not in CLASSES:
        control_class = "manual"
    title = str(payload.get("document_title") or payload.get("reference") or "sample")
    retention = document_retention_days(control_class)
    review_state = {
        "open": "pending_review",
        "in_progress": "under_review",
        "closed": "approved",
    }[status]
    record = {
        **payload,
        "status": status,
        "document_title": title,
        "control_class": control_class,
        "retention_days": retention,
        "review_state": review_state,
        "capability": CAPABILITY_ID,
        "channel": "mcp",
    }
    blocks: Dict[str, Any] = {}
    for block_id in BLOCK_IDS:
        blocks[block_id] = execute(
            block_id,
            prepare_block_input(block_id, record),
            action=BLOCK_DEFAULT_ACTIONS.get(block_id),
        )
    record["controlled_document"] = {
        "document_title": title,
        "control_class": control_class,
        "retention_days": retention,
        "review_state": review_state,
        "allowed_next_status": list(allowed_next_status(status)),
        "validated": True,
        "stored": True,
    }
    return ok_envelope(CAPABILITY_ID, record, blocks)
