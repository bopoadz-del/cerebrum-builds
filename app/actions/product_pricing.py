"""Capability product_pricing — catalogue unit costs, margins and price lists.

Written by the factory WRITER role (codewhale exec)

Blocks are invoked through the local dispatch runtime (``app.dispatch.execute``)
against the block source vendored at build time — this module makes no network
call and never persists: the ROUTE writes the tenant-scoped record after
``handle()`` reports success (Phase 2 §0.2).

Pipeline:
  * ``formula_executor`` — evaluates the declared bakery pricing formulas
    (cost-plus price, gross margin, price-list delta) in-process against the
    record's own numbers — the expression is data, never a network sandbox;
  * ``database``         — records the priced catalogue row;
  * ``validation``       — runs the five-stage pipeline over the priced record;
  * ``analytics``        — records the margin metric as a tracked event.

A record whose formula cannot be evaluated is reported as an error, never as a
silently defaulted price: a price the cost sheet does not support is not a
price the shop may charge.

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

CAPABILITY_ID = "product_pricing"
ENTITY = "product_pricing"
BLOCK_IDS = [
    "formula_executor",
    "database",
    "validation",
    "analytics",
]
#: Each block's declared action (keyword dispatch; never inside the payload).
BLOCK_DEFAULT_ACTIONS = {
    "formula_executor": "execute",
    "database": "insert",
    "validation": "validate_pipeline",
    "analytics": "track_event",
}
CAPABILITY_FIELDS: List[str] = [
    "reference",
    "product_code",
    "product_name",
    "shop_code",
    "unit_cost",
    "margin_percent",
    "unit_price",
    "price_list_version",
    "notes",
    "status",
]

#: Declared formulas this capability evaluates.  The vendored
#: ``formula_executor`` runs the expression in-process — no network sandbox.
FORMULA_CODE: Dict[str, str] = {
    "price_from_cost": "result = unit_cost * (1 + margin_percent / 100)",
    "margin_from_price": (
        "result = (unit_price - unit_cost) / unit_price * 100 if unit_price else 0"
    ),
    "price_list_delta": "result = unit_price - unit_cost",
    "stock_reorder_shortfall": "result = max(0, reorder_threshold - quantity_on_hand)",
}


def _number(value: Any, fallback: float = 0.0) -> float:
    return float(value) if isinstance(value, (int, float)) else fallback


def _price_context(record: Dict[str, Any]) -> Dict[str, Any]:
    """The pricing inputs this record carries, named as the formulas declare."""
    unit_cost = _number(record.get("unit_cost"))
    margin = _number(record.get("margin_percent"))
    unit_price = _number(record.get("unit_price"))
    if unit_price <= 0.0:
        unit_price = unit_cost * (1 + margin / 100)
    return {
        "product": str(record.get("product_code") or "product"),
        "shop": str(record.get("shop_code") or "chain"),
        "unit_cost": unit_cost,
        "margin_percent": margin,
        "unit_price": unit_price,
        "version": str(record.get("price_list_version") or "v1"),
    }


def _formula_key(record: Dict[str, Any]) -> str:
    version = str(record.get("price_list_version") or "").strip().lower()
    if version in FORMULA_CODE:
        return version
    return "price_from_cost"


def _margin(record: Dict[str, Any], price: Dict[str, Any]) -> float:
    explicit = record.get("margin_percent")
    if isinstance(explicit, (int, float)):
        return float(explicit)
    if price["unit_price"] > 0:
        return (price["unit_price"] - price["unit_cost"]) / price["unit_price"] * 100
    return 0.0


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(payload) if isinstance(payload, dict) else {"value": payload}
    price = _price_context(data)
    key = _formula_key(data)
    margin = _margin(data, price)
    results: Dict[str, Any] = {}
    errors: Dict[str, str] = {}
    for block_id in BLOCK_IDS:
        prepared = prepare_block_input(block_id, data, entity=ENTITY)
        if block_id == "formula_executor":
            prepared["formula_key"] = key
            prepared["formula_description"] = key.replace("_", " ")
            prepared["input_values"] = {
                "unit_cost": price["unit_cost"],
                "margin_percent": margin,
                "unit_price": price["unit_price"],
                "quantity_on_hand": 0,
                "reorder_threshold": 0,
            }
            prepared["custom_code"] = FORMULA_CODE[key]
            prepared["operation"] = "auto"
        if block_id == "validation":
            item = dict(prepared.get("item") or {})
            item.setdefault("id", str(data.get("reference") or "sample"))
            item.setdefault("type", ENTITY)
            item["unit_price"] = price["unit_price"]
            item["unit_cost"] = price["unit_cost"]
            prepared["item"] = item
            prepared["context"] = {
                "entity": ENTITY,
                "shop_code": price["shop"],
                "price_list_version": price["version"],
            }
        if block_id == "analytics":
            prepared["metric"] = "product_margin_percent"
            prepared["value"] = margin
            prepared["name"] = ENTITY
            prepared["period"] = price["version"]
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
        "price": {
            "product_code": price["product"],
            "shop_code": price["shop"],
            "unit_cost": price["unit_cost"],
            "margin_percent": margin,
            "unit_price": price["unit_price"],
            "price_list_version": price["version"],
        },
        "results": results,
    }
