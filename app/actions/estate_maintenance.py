"""estate_maintenance — GAP. Work-order intelligence authored in-handler."""

from __future__ import annotations

from typing import Any, Dict

from app.persist import ok_envelope

# READS: caller.input
# WRITES: caller.output
# NEVER: unlisted Store block ids

BLOCK_IDS: list[str] = []


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Author a maintenance work-order envelope from the asset register fields."""
    work_order = {
        "kind": "maintenance",
        "reference": payload.get("reference"),
        "status": payload.get("status", "open"),
        "cadence": "preventive",
    }
    record = {**payload, "work_order": work_order}
    return ok_envelope("estate_maintenance", record)
