"""automotive_core — GENERATE gap. Vehicle inventory kernel; no Store block ids."""

from __future__ import annotations

from typing import Any, Dict

from app.domain import (
    allowed_next_status,
    ask_price,
    days_on_lot,
    envelope_status,
    inquiry_priority,
    inventory_score,
    vehicle_condition,
)
from app.persist import ok_envelope

# READS: caller.input
# WRITES: caller.output, database.sql (spec.entity automotive_core)
# NEVER: (none) — no Store block is bound

BLOCK_IDS: list[str] = []
CAPABILITY_ID = "automotive_core"


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """List a vehicle on a branch lot and persist the inventory record."""
    payload = dict(payload or {})
    status = envelope_status(payload)
    condition = vehicle_condition(payload)
    branch = str(payload.get("branch") or payload.get("reference") or "sample")
    score = inventory_score(status, condition)
    price = ask_price(status)
    lot_days = days_on_lot(status)
    record = {
        **payload,
        "reference": str(payload.get("reference") or "sample"),
        "status": status,
        "condition": condition,
        "branch": branch,
        "make": str(payload.get("make") or "sample"),
        "model": str(payload.get("model") or "sample"),
        "vin": str(payload.get("vin") or payload.get("reference") or "sample"),
        "ask_price": price,
        "mileage": int(payload.get("mileage") or 1),
        "year": int(payload.get("year") or 2026),
        "days_on_lot": lot_days,
        "inventory_score": score,
        "inquiry_priority": inquiry_priority(status),
        "allowed_next_status": list(allowed_next_status(status)),
        "capability": CAPABILITY_ID,
        "channel": "mcp",
    }
    return ok_envelope(CAPABILITY_ID, record, {})
