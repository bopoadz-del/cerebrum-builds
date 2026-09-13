"""transaction_capture — REUSE capture + storage + validation. Persist the ledger row."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import capture_input, storage_input, validation_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, file.local.read, config.runtime
# WRITES: caller.output, file.local.write
# NEVER: inventing unverified Store block ids; demanding topic/sql/file paths from the caller

BLOCK_IDS = ["capture", "storage", "validation"]


def _amount(payload: Dict[str, Any]) -> float:
    raw = payload.get("amount")
    if raw in (None, "", "sample"):
        return 1.0
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 1.0


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Extract a transaction, store the artifact, validate the item, persist."""
    blocks = {
        "capture": execute(
            "capture",
            capture_input(payload),
            action=BLOCK_DEFAULT_ACTIONS.get("capture"),
        ),
        "storage": execute(
            "storage",
            storage_input(payload),
            action=BLOCK_DEFAULT_ACTIONS.get("storage"),
        ),
        "validation": execute(
            "validation",
            validation_input(payload),
            action=BLOCK_DEFAULT_ACTIONS.get("validation"),
        ),
    }
    record = {
        **payload,
        "ledger_entry": {
            "reference": str(payload.get("reference") or "sample"),
            "account_name": payload.get("account_name") or "sample",
            "category": payload.get("category") or "income",
            "amount": _amount(payload),
            "captured": True,
        },
    }
    return ok_envelope("transaction_capture", record, blocks)
