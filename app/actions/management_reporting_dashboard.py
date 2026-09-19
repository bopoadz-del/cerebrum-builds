"""Capability management_reporting_dashboard — chain-wide KPIs and exceptions.

Written by the factory WRITER role (codewhale exec)

Blocks are invoked through the local dispatch runtime (``app.dispatch.execute``)
against the block source vendored at build time — this module makes no network
call and never persists: the ROUTE writes the tenant-scoped record after
``handle()`` reports success (Phase 2 §0.2).

Pipeline:
  * ``dashboard``        — renders the consolidated chain view for the metric;
  * ``analytics``        — records the metric as a tracked event;
  * ``portfolio_rollup`` — rolls the metric up across the five shops.

Nothing here invents a number the record did not carry: a metric with no value
is reported as unset rather than defaulted to success.

Scope
-----
READS  the caller's payload.
WRITES nothing (the route persists the metric record).
NEVER  network, HTTP store callbacks, ``vendor/**``.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.block_inputs import prepare_block_input
from app.dispatch import execute

CAPABILITY_ID = "management_reporting_dashboard"
ENTITY = "management_reporting_dashboard"
BLOCK_IDS = ["dashboard", "analytics", "portfolio_rollup"]
#: Each block's declared action (keyword dispatch; never inside the payload).
BLOCK_DEFAULT_ACTIONS = {
    "dashboard": "render",
    "analytics": "track_event",
    "portfolio_rollup": "rollup",
}
CAPABILITY_FIELDS: List[str] = [
    "reference",
    "metric_name",
    "metric_value",
    "shop_code",
    "reporting_period",
    "notes",
    "status",
]


def _metric_window(record: Dict[str, Any]) -> Dict[str, Any]:
    """The metric, its value, and the shop/period it was reported for."""
    name = str(record.get("metric_name") or "sales_total")
    raw = record.get("metric_value")
    value = float(raw) if isinstance(raw, (int, float)) else 0.0
    shop = str(record.get("shop_code") or "chain")
    period = str(record.get("reporting_period") or "day")
    if name.endswith("_percent") or name in ("delivery_on_time", "stock_accuracy"):
        band = "on_target" if value >= 95 else "watch" if value >= 85 else "below_target"
    else:
        band = "recorded"
    return {"metric": name, "value": value, "shop": shop, "period": period, "band": band}


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(payload) if isinstance(payload, dict) else {"value": payload}
    metric = _metric_window(data)
    results: Dict[str, Any] = {}
    errors: Dict[str, str] = {}
    for block_id in BLOCK_IDS:
        prepared = prepare_block_input(block_id, data, entity=ENTITY)
        if block_id in ("dashboard", "analytics"):
            prepared["metric"] = metric["metric"]
            prepared["value"] = metric["value"]
            prepared["name"] = ENTITY
            prepared["window"] = metric["period"]
        if block_id == "dashboard":
            prepared["title"] = "chain dashboard: %s (%s)" % (
                metric["metric"],
                metric["shop"],
            )
        if block_id == "portfolio_rollup":
            prepared["properties"] = [
                {
                    "name": ENTITY,
                    "value": metric["value"],
                    "reference": str(data.get("reference") or "sample"),
                    "shop_code": metric["shop"],
                    "band": metric["band"],
                }
            ]
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
