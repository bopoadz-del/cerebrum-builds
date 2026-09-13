"""prescription_management — REUSE validation + analytics. Domain dose math."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import prepare_block_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.domain import allowed_next_status, daily_dose_mg, envelope_status
from app.persist import ok_envelope

# READS: caller.input, config.runtime
# WRITES: caller.output
# NEVER: (none)

BLOCK_IDS = ["validation", "analytics"]
CAPABILITY_ID = "prescription_management"
DOSE_FORMS = ("tablet", "liquid", "injectable")


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a script and persist daily_dose_mg (weight × mg/kg, never silent 0)."""
    status = envelope_status(payload)
    dose_form = str(payload.get("dose_form") or "tablet")
    if dose_form not in DOSE_FORMS:
        dose_form = "tablet"
    medication_name = str(
        payload.get("medication_name") or payload.get("reference") or "sample"
    )
    dose = daily_dose_mg(payload, dose_form)
    refill_due = status == "open"
    record = {
        **payload,
        "status": status,
        "medication_name": medication_name,
        "dose_form": dose_form,
        "daily_dose_mg": dose,
        "refill_due": refill_due,
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
    record["prescription"] = {
        "medication_name": medication_name,
        "dose_form": dose_form,
        "daily_dose_mg": dose,
        "refill_due": refill_due,
        "formula": "weight_kg * mg_per_kg",
        "allowed_next_status": list(allowed_next_status(status)),
        "validated": True,
    }
    return ok_envelope(CAPABILITY_ID, record, blocks)
