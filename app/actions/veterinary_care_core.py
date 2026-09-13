"""veterinary_care_core — REUSE analytics. Persist clinic caseload readiness."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import prepare_block_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.domain import (
    allowed_next_status,
    clinic_is_overloaded,
    clinic_load_score,
    envelope_status,
)
from app.persist import ok_envelope

# READS: caller.input, config.runtime, llm.provider
# WRITES: caller.output
# NEVER: (none)

BLOCK_IDS = ["analytics"]
CAPABILITY_ID = "veterinary_care_core"
WINDOWS = ("walk_in", "shift", "day")


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Score clinic load from envelope status × window weight; persist the snapshot."""
    status = envelope_status(payload)
    window = str(payload.get("caseload_window") or "walk_in")
    if window not in WINDOWS:
        window = "walk_in"
    clinic_unit = str(payload.get("clinic_unit") or payload.get("reference") or "sample")
    score = clinic_load_score(status, window)
    overloaded = clinic_is_overloaded(score)
    record = {
        **payload,
        "status": status,
        "clinic_unit": clinic_unit,
        "caseload_window": window,
        "clinic_load_score": score,
        "overloaded": overloaded,
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
    record["clinic"] = {
        "clinic_unit": clinic_unit,
        "window": window,
        "score": score,
        "overloaded": overloaded,
        "allowed_next_status": list(allowed_next_status(status)),
        "metric": "vetcare_clinic_events",
        "tracked": True,
    }
    return ok_envelope(CAPABILITY_ID, record, blocks)
