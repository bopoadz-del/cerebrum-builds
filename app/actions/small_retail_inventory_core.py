"""small_retail_inventory_core — GENERATE. SKU catalog, stock, receive/sell, reorder."""

from __future__ import annotations

from typing import Any, Dict, List

from app.persist import ok_envelope

# READS: caller.input
# WRITES: caller.output
# NEVER: inventing unverified Store block ids

BLOCK_IDS: list[str] = []


def _sku_card(payload: Dict[str, Any]) -> Dict[str, Any]:
    reference = str(payload.get("reference") or "sample")
    sku = str(payload.get("sku") or reference)
    return {
        "sku": sku,
        "item_name": payload.get("item_name") or sku,
        "location": payload.get("location") or "floor",
        "status": payload.get("status", "open"),
    }


def _on_hand_units(payload: Dict[str, Any]) -> int:
    raw = payload.get("on_hand")
    try:
        units = int(raw)
    except (TypeError, ValueError):
        units = 0
    return max(units, 0)


def _stock_position(payload: Dict[str, Any]) -> Dict[str, Any]:
    on_hand = _on_hand_units(payload)
    reorder_point = 4
    return {
        "sku": payload.get("sku") or payload.get("reference") or "sample",
        "on_hand": on_hand,
        "reorder_point": reorder_point,
        "needs_reorder": on_hand <= reorder_point,
        "location": payload.get("location") or "floor",
        "status": payload.get("status", "open"),
    }


def _stock_movement(payload: Dict[str, Any]) -> Dict[str, Any]:
    movement = str(payload.get("movement") or "receive")
    delta = {
        "receive": 1,
        "adjust": 0,
        "sell": -1,
    }.get(movement, 0)
    return {
        "reference": payload.get("reference", "sample"),
        "movement": movement,
        "delta": delta,
        "channel": "mcp",
        "status": payload.get("status", "open"),
    }


def _receiving_ticket(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "reference": payload.get("reference", "sample"),
        "sku": payload.get("sku") or payload.get("reference") or "sample",
        "expected_qty": max(_on_hand_units(payload), 1),
        "status": payload.get("status", "open"),
    }


def _sales_ticket(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "reference": payload.get("reference", "sample"),
        "sku": payload.get("sku") or payload.get("reference") or "sample",
        "sold_qty": 1 if payload.get("movement") == "sell" else 0,
        "status": payload.get("status", "open"),
    }


def _cycle_count_plan(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    status = payload.get("status", "open")
    return [
        {"step": "count_floor", "status": status},
        {"step": "count_backroom", "status": status},
        {"step": "post_variance", "status": "closed" if status == "closed" else status},
    ]


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Author the retail inventory kernel from the envelope. No Store blocks are bound."""
    record = {
        **payload,
        "sku_catalog": [_sku_card(payload)],
        "stock_position": _stock_position(payload),
        "stock_movement": _stock_movement(payload),
        "receiving_ticket": _receiving_ticket(payload),
        "sales_ticket": _sales_ticket(payload),
        "cycle_count_plan": _cycle_count_plan(payload),
    }
    return ok_envelope("small_retail_inventory_core", record)
