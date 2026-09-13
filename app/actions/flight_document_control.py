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

# READS: caller.input, file.local.read, file.input_document, config.runtime,
#        env.process, network.http.outbound, credential.env, block.peer
# WRITES: caller.output, file.local.write, file.temp, network.smtp.outbound,
#         email.outbound, notification.outbound
# NEVER: (none)

BLOCK_IDS = ["document_engine", "storage", "file_hasher", "notification"]

CLASS_LABEL = {
    "amm": "aircraft_maintenance_manual",
    "mel": "minimum_equipment_list",
    "qrh": "quick_reference_handbook",
    "ops_manual": "operations_manual",
}
STATE_CONTROLLED = {"controlled": True, "draft": False, "superseded": False}


def _doc_class(payload: Dict[str, Any]) -> str:
    value = str(payload.get("document_class") or "amm")
    return value if value in CLASS_LABEL else "amm"


def _state(payload: Dict[str, Any]) -> str:
    value = str(payload.get("control_state") or "controlled")
    return value if value in STATE_CONTROLLED else "controlled"


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Parse, store, hash, and notify on a controlled flight document."""
    doc_class = _doc_class(payload)
    state = _state(payload)
    reference = str(payload.get("reference") or "sample")
    body = (
        f"Controlled {CLASS_LABEL[doc_class]} {reference} state={state} "
        "for Aviation Operations Hub document control."
    )
    filename = f"{doc_class}-{reference}.txt"
    blocks = {
        "document_engine": execute(
            "document_engine",
            document_engine_input(payload, body=body),
            action=BLOCK_DEFAULT_ACTIONS.get("document_engine"),
        ),
        "storage": execute(
            "storage",
            storage_input(payload, filename, body),
            action=BLOCK_DEFAULT_ACTIONS.get("storage"),
        ),
        "file_hasher": execute(
            "file_hasher",
            file_hasher_input(payload, body=body),
            action=BLOCK_DEFAULT_ACTIONS.get("file_hasher"),
        ),
        "notification": execute(
            "notification",
            notification_input(payload, f"Document {filename} is {state}"),
            action=BLOCK_DEFAULT_ACTIONS.get("notification"),
        ),
    }
    record = {
        **payload,
        "controlled_document": {
            "document_class": doc_class,
            "label": CLASS_LABEL[doc_class],
            "control_state": state,
            "is_controlled": STATE_CONTROLLED[state],
            "filename": filename,
            "channel": "mcp",
        },
    }
    return ok_envelope("flight_document_control", record, blocks)
