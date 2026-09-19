"""Deterministic bakery formulas (margins, takings, stock cover).

Written by the factory WRITER role (codewhale exec)

Pure stdlib arithmetic. Every function refuses malformed input by name
rather than returning a number that looks authoritative; the caller sees
why it could not be computed.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional


class FormulaError(ValueError):
    """A formula was asked for a figure its inputs cannot support."""


def _number(value: Any, name: str) -> float:
    if isinstance(value, bool) or value is None:
        raise FormulaError(f"{name} must be a number")
    try:
        return float(value)
    except (TypeError, ValueError):
        raise FormulaError(f"{name} must be a number, got {type(value).__name__}") from None


def margin_percent(*, sale_price: Any, ingredient_cost: Any) -> float:
    """Gross margin as a percentage of the sale price."""
    sale = _number(sale_price, "sale_price")
    cost = _number(ingredient_cost, "ingredient_cost")
    if sale <= 0:
        raise FormulaError("sale_price must be greater than zero")
    if cost < 0:
        raise FormulaError("ingredient_cost cannot be negative")
    return round(((sale - cost) / sale) * 100.0, 4)


def unit_cost(*, batch_cost: Any, units: Any) -> float:
    """Ingredient cost per finished unit for a batch."""
    total = _number(batch_cost, "batch_cost")
    count = _number(units, "units")
    if count <= 0:
        raise FormulaError("units must be greater than zero")
    return round(total / count, 4)


def daily_takings(entries: Iterable[Dict[str, Any]]) -> Dict[str, float]:
    """Sum sales and costs by branch from the day's book entries."""
    sales = 0.0
    costs = 0.0
    for entry in entries or ():
        if not isinstance(entry, dict):
            continue
        kind = str(entry.get("entry_type") or "")
        amount = _number(entry.get("amount") or 0, "amount")
        if kind in ("sale", "taking"):
            sales += amount
        elif kind in ("cost", "expense"):
            costs += amount
    return {"sales": round(sales, 4), "costs": round(costs, 4), "net": round(sales - costs, 4)}


def stock_cover_days(*, quantity_on_hand: Any, daily_usage: Any) -> float:
    """How many days of cover a branch holds."""
    on_hand = _number(quantity_on_hand, "quantity_on_hand")
    usage = _number(daily_usage, "daily_usage")
    if usage <= 0:
        raise FormulaError("daily_usage must be greater than zero")
    if on_hand < 0:
        raise FormulaError("quantity_on_hand cannot be negative")
    return round(on_hand / usage, 4)


def reorder_required(*, quantity_on_hand: Any, reorder_threshold: Any) -> bool:
    """True when a branch has fallen to or below its reorder threshold."""
    on_hand = _number(quantity_on_hand, "quantity_on_hand")
    threshold = _number(reorder_threshold, "reorder_threshold")
    if threshold < 0:
        raise FormulaError("reorder_threshold cannot be negative")
    return on_hand <= threshold


def delivery_capacity(*, cars: int = 2, bikes: int = 10) -> Dict[str, int]:
    """Fleet capacity for the pilot's two cars and ten bikes."""
    return {"cars": int(cars), "bikes": int(bikes), "vehicles": int(cars) + int(bikes)}


def deposit_outstanding(*, deposit_amount: Any, order_total: Any) -> float:
    """Deposit still owed on an event order."""
    deposit = _number(deposit_amount or 0, "deposit_amount")
    total = _number(order_total, "order_total")
    if total < 0 or deposit < 0:
        raise FormulaError("amounts cannot be negative")
    return round(max(0.0, total - deposit), 4)


def evaluate(name: str, **kwargs: Any) -> Dict[str, Any]:
    """Named evaluation used by the books capability."""
    library = {
        "margin_percent": margin_percent,
        "unit_cost": unit_cost,
        "stock_cover_days": stock_cover_days,
        "deposit_outstanding": deposit_outstanding,
        "reorder_required": reorder_required,
    }
    fn = library.get(str(name or ""))
    if fn is None:
        raise FormulaError("unknown formula: " + str(name))
    return {"formula": name, "result": fn(**kwargs)}
