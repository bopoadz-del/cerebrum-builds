"""regulatory_document_control — REUSE document_engine + validation + audit + storage."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import prepare_block_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, file.local.read, file.input_document, config.runtime, database.sql
# WRITES: caller.output, file.local.write, file.temp, database.sql
# NEVER: (none)

BLOCK_IDS = ["document_engine", "validation", "audit", "storage"]
CAPABILITY_ID = "regulatory_document_control"
CLASSES = ("manual", "certificate", "directive")


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Parse a controlled document, validate, audit, and store the envelope."""
    control_class = str(payload.get("control_class") or "manual")
    if control_class not in CLASSES:
        control_class = "manual"
    title = str(payload.get("document_title") or payload.get("reference") or "sample")
    record = {
        **payload,
        "document_title": title,
        "control_class": control_class,
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
        "validated": True,
        "stored": True,
    }
    return ok_envelope(CAPABILITY_ID, record, blocks)
