"""automotive_core — GENERATE gap. Vehicle inventory, leads, test-drives, financing."""

from __future__ import annotations

from typing import Any, Dict

from app.domain import (
    allowed_next_status,
    branch_stock,
    envelope_status,
    lead_score,
    list_price,
    listing_kind_of,
    model_year,
    monthly_payment,
    odometer_miles,
    testdrive_hold_minutes,
)
from app.persist import ok_envelope

# READS: caller.input
# WRITES: caller.output, database.sql
# NEVER: (none)

BLOCK_IDS: list[str] = []
CAPABILITY_ID = "automotive_core"


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Price a lot listing from kind × envelope status and persist the vehicle."""
    status = envelope_status(payload)
    listing_kind = listing_kind_of(payload)
    branch_code = str(payload.get("branch_code") or payload.get("reference") or "sample")
    make = str(payload.get("make") or payload.get("reference") or "sample")
    model = str(payload.get("model") or payload.get("reference") or "sample")
    price = list_price(listing_kind, status)
    payment = monthly_payment(listing_kind, status)
    year = model_year(listing_kind)
    miles = odometer_miles(listing_kind)
    hold = testdrive_hold_minutes(listing_kind)
    score = lead_score(listing_kind)
    stock = branch_stock(branch_code)
    record = {
        **payload,
        "status": status,
        "listing_kind": listing_kind,
        "branch_code": branch_code,
        "make": make,
        "model": model,
        "model_year": year,
        "odometer_miles": miles,
        "list_price": price,
        "monthly_payment": payment,
        "lead_score": score,
        "testdrive_hold_minutes": hold,
        "branch_stock": stock,
        "capability": CAPABILITY_ID,
        "channel": "mcp",
    }
    record["listing"] = {
        "make": make,
        "model": model,
        "listing_kind": listing_kind,
        "model_year": year,
        "list_price": price,
        "monthly_payment": payment,
        "lead_score": score,
        "testdrive_hold_minutes": hold,
        "branch_stock": stock,
        "allowed_next_status": list(allowed_next_status(status)),
        "vin_slot": f"VIN-{record.get('reference') or 'sample'}",
        "priced": True,
    }
    return ok_envelope(CAPABILITY_ID, record, {})
