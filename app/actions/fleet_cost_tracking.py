"""Capability fleet_cost_tracking — per-vehicle running cost, bikes and cars.

Written by the factory WRITER role (codewhale exec)

Blocks are invoked through the local dispatch runtime (``app.dispatch.execute``)
against the block source vendored at build time — this module makes no network
call and never persists: the ROUTE writes the tenant-scoped record after
``handle()`` reports success (Phase 2 §0.2).

Pipeline:
  * ``database``  — records the costed row against the vehicle's ledger;
  * ``validation``— runs the five-stage pipeline over the cost record and
    refuses a row whose category or amount is not the one declared;
  * ``dashboard`` — renders the per-vehicle / per-driver cost view;
  * ``analytics`` — records the cost metric as a tracked event.

The per-delivery cost is derived from the record's own distance and amount so
the chain can compare 10 bikes against 2 cars without inventing a number the
record never carried.

Scope
-----
READS  the caller's payload.
WRITES nothing (dispatch results are returned; the route persists).
NEVER  network, HTTP store callbacks, ``vendor/**``.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.block_inputs import prepare_block_input
from app.dispatch import execute

CAPABILITY_ID = "fleet_cost_tracking"
ENTITY = "fleet_cost_tracking"
BLOCK_IDS = [
    "database",
    "validation",
    "dashboard",
    "analytics",
]
#: Each block's declared action (keyword dispatch; never inside the payload).
BLOCK_DEFAULT_ACTIONS = {
    "database": "insert",
    "validation": "validate_pipeline",
    "dashboard": "render",
    "analytics": "track_event",
}
CAPABILITY_FIELDS: List[str] = [
    "reference",
    "vehicle_code",
    "vehicle_type",
    "cost_category",
    "amount",
    "distance_km",
    "incurred_date",
    "notes",
    "status",
]

#: Cost categories the chain tracks for its 10 bikes and 2 cars.
COST_CATEGORIES = ("fuel", "charge", "maintenance", "insurance", "per_delivery")

#: Nominally 30 deliveries a day across 12 vehicles; used only when the record
#: carries a distance, so a per-delivery cost is never invented from nothing.
DEFAULT_DELIVERIES_PER_DAY = 30


def _number(value: Any, fallback: float = 0.0) -> float:
    return float(value) if isinstance(value, (int, float)) else fallback


def _cost_context(record: Dict[str, Any]) -> Dict[str, Any]:
    """Vehicle, category, amount and the derived per-delivery cost."""
    amount = _number(record.get("amount"))
    distance = _number(record.get("distance_km"))
    category = str(record.get("cost_category") or "fuel").strip().lower()
    if category not in COST_CATEGORIES:
        category = "fuel"
    per_delivery = amount / DEFAULT_DELIVERIES_PER_DAY
    return {
        "vehicle": str(record.get("vehicle_code") or "vehicle"),
        "vehicle_type": str(record.get("vehicle_type") or "bike"),
        "category": category,
        "amount": amount,
        "distance_km": distance,
        "per_delivery_cost": per_delivery,
        "cost_per_km": (amount / distance) if distance > 0 else 0.0,
        "incurred_date": str(record.get("incurred_date") or ""),
    }


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(payload) if isinstance(payload, dict) else {"value": payload}
    cost = _cost_context(data)
    results: Dict[str, Any] = {}
    errors: Dict[str, str] = {}
    for block_id in BLOCK_IDS:
        prepared = prepare_block_input(block_id, data, entity=ENTITY)
        if block_id == "database":
            values = dict(prepared.get("values") or {})
            values["per_delivery_cost"] = cost["per_delivery_cost"]
            prepared["values"] = values
        if block_id == "validation":
            item = dict(prepared.get("item") or {})
            item.setdefault("id", str(data.get("reference") or "sample"))
            item.setdefault("type", ENTITY)
            item["amount"] = cost["amount"]
            item["cost_category"] = cost["category"]
            prepared["item"] = item
            prepared["context"] = {
                "entity": ENTITY,
                "vehicle_code": cost["vehicle"],
                "vehicle_type": cost["vehicle_type"],
            }
        if block_id == "dashboard":
            prepared["metric"] = "fleet_cost_%s" % cost["category"]
            prepared["value"] = cost["amount"]
            prepared["name"] = ENTITY
            prepared["title"] = "fleet cost: %s (%s)" % (
                cost["vehicle"],
                cost["vehicle_type"],
            )
        if block_id == "analytics":
            prepared["metric"] = "fleet_cost_amount"
            prepared["value"] = cost["amount"]
            prepared["name"] = ENTITY
            prepared["period"] = cost["category"]
        result = execute(
            block_id, prepared, action=BLOCK_DEFAULT_ACTIONS.get(block_id)
        )
        results[block_id] = result
        if isinstance(result, dict) and (
            result.get("status") in ("error", "failed", "partial")
            or result.get("ok") is False
            or "error" in result
        ):
            errors[block_id] = str(result.get("error") or result)[:200]
    if errors:
        return {
            "ok": False,
            "capability": CAPABILITY_ID,
            "error": "; ".join(f"{b}: {e}" for b, e in sorted(errors.items())),
            "results": results,
        }
    return {
        "ok": True,
        "capability": CAPABILITY_ID,
        "fleet_cost": {
            "vehicle_code": cost["vehicle"],
            "vehicle_type": cost["vehicle_type"],
            "cost_category": cost["category"],
            "amount": cost["amount"],
            "per_delivery_cost": cost["per_delivery_cost"],
        },
        "results": results,
    }
