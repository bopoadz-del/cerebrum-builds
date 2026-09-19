"""Formula surface for bakery delivery and product economics.

Written by the factory WRITER role (codewhale exec)

Formulas are versioned data evaluated locally; the vendored ``formula_executor``
block owns execution, so nothing here duplicates it. This module is the
platform's own bookkeeping: which formula version a record used and what it
computed, so a cost record can cite the exact revision.

Scope
-----
READS  the caller's inputs.
WRITES nothing.
NEVER  network, ``vendor/**``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

FORMULA_VERSION = "formulas.v1"

#: Declared bakery formulas: name -> (params, unit).
FORMULA_LIBRARY: Dict[str, Dict[str, Any]] = {
    "delivery_cost": {"params": ["distance_km", "unit_price"], "unit": "currency"},
    "vehicle_operating_cost": {
        "params": ["distance_km", "fuel_price", "maintenance_rate"],
        "unit": "currency",
    },
    "product_price": {"params": ["unit_cost", "margin_percent"], "unit": "currency"},
    "stock_reorder_shortfall": {
        "params": ["reorder_threshold", "quantity_on_hand"],
        "unit": "unit",
    },
    "driver_utilisation": {
        "params": ["deliveries_done", "deliveries_planned"],
        "unit": "%",
    },
}


def describe(name: str) -> Optional[Dict[str, Any]]:
    spec = FORMULA_LIBRARY.get(str(name or ""))
    if spec is None:
        return None
    return {"name": name, "version": FORMULA_VERSION, **spec}


def evaluate(name: str, variables: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate a declared formula. The block does the numeric work."""
    from app.block_inputs import prepare_block_input
    from app.dispatch import execute

    if str(name) not in FORMULA_LIBRARY:
        return {"ok": False, "error": f"unknown formula: {name}",
                "known": sorted(FORMULA_LIBRARY)}
    result = execute(
        "formula_executor",
        prepare_block_input("formula_executor", dict(variables or {}), formula=name),
        action="execute",
    )
    return {"ok": not (isinstance(result, dict) and result.get("status") == "error"),
            "formula": name, "version": FORMULA_VERSION, "result": result}
