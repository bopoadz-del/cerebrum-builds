"""Capability stock_inventory_management — per-shop stock, waste and transfers.

Written by the factory WRITER role (codewhale exec)

Blocks are invoked through the local dispatch runtime (``app.dispatch.execute``)
against the block source vendored at build time — this module makes no network
call and never persists: the ROUTE writes the tenant-scoped record after
``handle()`` reports success (Phase 2 §0.2).

Pipeline (block inputs are constructed in ``app/block_inputs.py``):
  * ``database``   — records the stock movement against the shop's ledger;
  * ``workflow``   — the movement run: a database step writes the movement and
    an analytics step records the position (both store children import cleanly;
  * ``validation`` — runs the five-stage pipeline over the movement record;
  * ``notification`` — sends the reorder notice over the MCP channel;
  * ``analytics``  — records the stock metric as a tracked event.

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

CAPABILITY_ID = "stock_inventory_management"
ENTITY = "stock_inventory_management"
BLOCK_IDS = ["database", "workflow", "validation", "notification", "analytics"]
#: Each block's declared action (keyword dispatch; never inside the payload).
BLOCK_DEFAULT_ACTIONS = {
    "database": "insert",
    "workflow": "run",
    "validation": "validate_pipeline",
    "notification": "send",
    "analytics": "track_event",
}
CAPABILITY_FIELDS: List[str] = [
    "reference",
    "shop_code",
    "item_code",
    "item_name",
    "quantity_on_hand",
    "reorder_threshold",
    "unit",
    "movement_type",
    "notes",
    "status",
]


def _stock_decision(record: Dict[str, Any]) -> Dict[str, Any]:
    """Stock position for this item, without inventing a number when absent."""
    on_hand = record.get("quantity_on_hand")
    threshold = record.get("reorder_threshold")
    if not isinstance(on_hand, (int, float)) or not isinstance(threshold, (int, float)):
        return {
            "known": False,
            "reorder_required": False,
            "shortfall": 0,
            "item": str(record.get("item_code") or record.get("reference") or "item"),
            "shop": str(record.get("shop_code") or "shop"),
        }
    return {
        "known": True,
        "reorder_required": on_hand <= threshold,
        "shortfall": max(0, int(threshold - on_hand)),
        "item": str(record.get("item_code") or record.get("reference") or "item"),
        "shop": str(record.get("shop_code") or "shop"),
    }


def _movement_steps(record: Dict[str, Any], decision: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Prepared workflow children: ledger write, then the shop notice."""
    values = prepare_block_input("database", record, entity=ENTITY)["values"]
    metric = prepare_block_input("analytics", record, entity=ENTITY)
    metric["metric"] = "stock_on_hand"
    metric["value"] = (
        record.get("quantity_on_hand")
        if isinstance(record.get("quantity_on_hand"), (int, float))
        else 0
    )
    metric["name"] = ENTITY
    metric["period"] = str(record.get("movement_type") or "shift")
    return [
        {
            "id": "step_0",
            "block": "database",
            "action": "insert",
            "input": {"table": ENTITY, "values": values},
            "params": {"action": "insert"},
        },
        {
            "id": "step_1",
            "block": "analytics",
            "action": "track_event",
            "input": metric,
            "params": {"action": "track_event"},
        },
    ]


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(payload) if isinstance(payload, dict) else {"value": payload}
    decision = _stock_decision(data)
    steps = _movement_steps(data, decision)
    results: Dict[str, Any] = {}
    errors: Dict[str, str] = {}
    for block_id in BLOCK_IDS:
        prepared = prepare_block_input(
            block_id, data, entity=ENTITY, steps=steps if block_id == "workflow" else None
        )
        if block_id == "notification":
            prepared["message"] = (
                "%s below threshold: %s" % (decision["shop"], decision["item"])
                if decision["reorder_required"]
                else "%s stock recorded: %s" % (decision["shop"], decision["item"])
            )
            prepared["payload"] = {
                "reference": str(data.get("reference") or "sample"),
                "item_code": decision["item"],
                "quantity_on_hand": data.get("quantity_on_hand"),
                "reorder_required": decision["reorder_required"],
            }
        if block_id == "analytics":
            prepared["metric"] = "stock_on_hand"
            prepared["value"] = (
                data.get("quantity_on_hand")
                if isinstance(data.get("quantity_on_hand"), (int, float))
                else 0
            )
            prepared["name"] = ENTITY
            prepared["period"] = str(data.get("movement_type") or "shift")
        if block_id == "validation":
            item = dict(prepared.get("item") or {})
            item.setdefault("id", str(data.get("reference") or "sample"))
            item.setdefault("type", ENTITY)
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
