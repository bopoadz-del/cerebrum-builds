"""Capability fleet_cost_and_pricing — delivery cost, vehicle cost, pricing.

Written by the factory WRITER role (codewhale exec)

Blocks are invoked through the local dispatch runtime (``app.dispatch.execute``)
against the block source vendored at build time — this module makes no network
call and never persists: the ROUTE writes the tenant-scoped record after
``handle()`` reports success (Phase 2 §0.2).

Pipeline:
  * ``formula_executor`` — evaluates the declared bakery formula in-process
    (delivery cost, vehicle operating cost, product price) against the record's
    own numbers;
  * ``database``         — records the costed row;
  * ``portfolio_rollup`` — rolls the cost up into the chain cost view;
  * ``analytics``        — records the cost metric as a tracked event;
  * ``validation``       — runs the five-stage pipeline over the costed record.

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

CAPABILITY_ID = "fleet_cost_and_pricing"
ENTITY = "fleet_cost_and_pricing"
BLOCK_IDS = [
    "formula_executor",
    "database",
    "portfolio_rollup",
    "analytics",
    "validation",
]
#: Each block's declared action (keyword dispatch; never inside the payload).
BLOCK_DEFAULT_ACTIONS = {
    "formula_executor": "execute",
    "database": "insert",
    "portfolio_rollup": "rollup",
    "analytics": "track_event",
    "validation": "validate_pipeline",
}
CAPABILITY_FIELDS: List[str] = [
    "reference",
    "vehicle_code",
    "vehicle_type",
    "distance_km",
    "unit_price",
    "operating_cost",
    "price_basis",
    "notes",
    "status",
]

#: Declared formulas this capability evaluates. The expression is data, and the
#: vendored formula_executor runs it in-process — no network sandbox.
FORMULA_CODE: Dict[str, str] = {
    "delivery_cost": "result = distance_km * unit_price",
    "vehicle_operating_cost": (
        "result = distance_km * (fuel_price + maintenance_rate)"
    ),
    "product_price": "result = unit_cost * (1 + margin_percent / 100)",
    "stock_reorder_shortfall": "result = max(0, reorder_threshold - quantity_on_hand)",
}


def _number(value: Any, fallback: float = 0.0) -> float:
    return float(value) if isinstance(value, (int, float)) else fallback


def _cost_context(record: Dict[str, Any]) -> Dict[str, Any]:
    """The cost inputs this record carries, named as the formula declares them."""
    distance = _number(record.get("distance_km"))
    unit_price = _number(record.get("unit_price"))
    operating = record.get("operating_cost")
    if not isinstance(operating, (int, float)):
        operating = distance * unit_price
    return {
        "vehicle": str(record.get("vehicle_code") or "vehicle"),
        "vehicle_type": str(record.get("vehicle_type") or "bike"),
        "distance_km": distance,
        "unit_price": unit_price,
        "operating_cost": float(operating),
        "basis": str(record.get("price_basis") or "per_delivery"),
    }


def _formula_key(record: Dict[str, Any]) -> str:
    basis = str(record.get("price_basis") or "").strip().lower()
    if basis in FORMULA_CODE:
        return basis
    return "delivery_cost"


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(payload) if isinstance(payload, dict) else {"value": payload}
    cost = _cost_context(data)
    key = _formula_key(data)
    results: Dict[str, Any] = {}
    errors: Dict[str, str] = {}
    for block_id in BLOCK_IDS:
        prepared = prepare_block_input(block_id, data, entity=ENTITY)
        if block_id == "formula_executor":
            prepared["formula_key"] = key
            prepared["formula_description"] = key.replace("_", " ")
            prepared["input_values"] = {
                "distance_km": cost["distance_km"],
                "unit_price": cost["unit_price"],
                "fuel_price": cost["unit_price"],
                "maintenance_rate": 0.0,
                "unit_cost": cost["unit_price"],
                "margin_percent": 0.0,
                "reorder_threshold": 0,
                "quantity_on_hand": 0,
            }
            prepared["custom_code"] = FORMULA_CODE[key]
            prepared["operation"] = "auto"
        if block_id == "portfolio_rollup":
            prepared["properties"] = [
                {
                    "name": ENTITY,
                    "value": cost["operating_cost"],
                    "reference": str(data.get("reference") or "sample"),
                    "vehicle_code": cost["vehicle"],
                }
            ]
        if block_id == "analytics":
            prepared["metric"] = "fleet_operating_cost"
            prepared["value"] = cost["operating_cost"]
            prepared["name"] = ENTITY
            prepared["period"] = cost["basis"]
        if block_id == "validation":
            item = dict(prepared.get("item") or {})
            item.setdefault("id", str(data.get("reference") or "sample"))
            item.setdefault("type", ENTITY)
            item["cost"] = cost["operating_cost"]
            prepared["item"] = item
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
    return {"ok": True, "capability": CAPABILITY_ID, "results": results}
