"""Deterministic rate/charge formulas for the FleetOps platform.

Written by the factory WRITER role (codewhale exec)

Scope
  READS   the caller's rate-card record.
  WRITES  the computed charges the caller asked for.
  NEVER   network, an LLM, or a second pricing engine: these are the same
          numbers the ``pricing_and_rate_cards`` handler quotes, exposed so
          invoices and reports can reuse them.

The Store ``formula_executor`` block stays bound at
``pricing_and_rate_cards``; these functions are the platform's own arithmetic
for the paths that must not depend on a block round trip (invoice totals,
report rollups).
"""

from __future__ import annotations

from typing import Any, Dict

SEASON_MULTIPLIERS: Dict[str, float] = {
    "standard": 1.0,
    "low": 0.9,
    "peak": 1.35,
    "high": 1.35,
}


class FormulaError(ValueError):
    """A formula input that must not be guessed at."""


def _num(record: Dict[str, Any], key: str) -> float:
    value = (record or {}).get(key)
    if value in (None, ""):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        raise FormulaError("%s must be numeric, got %r" % (key, value)) from None


def _days(value: Any) -> int:
    if value in (None, ""):
        return 0
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        raise FormulaError("duration_days must be an integer, got %r" % (value,)) from None


def season_multiplier(season: Any) -> float:
    key = str(season or "standard").strip().lower()
    return SEASON_MULTIPLIERS.get(key, 1.0)


def rental_charge(record: Dict[str, Any]) -> Dict[str, float]:
    """Base rental charge over the billed days, season-adjusted."""
    days = max(_days((record or {}).get("duration_days") or (record or {}).get("rental_days")), 1)
    multiplier = season_multiplier((record or {}).get("season"))
    base = _num(record, "base_rate") * days * multiplier
    return {
        "duration_days": days,
        "season_multiplier": multiplier,
        "duration_charge": round(base, 2),
    }


def extra_charges(record: Dict[str, Any]) -> Dict[str, float]:
    """Mileage, fuel, late-return and extras, summed."""
    parts = {
        key: round(_num(record, key), 2)
        for key in ("mileage_charge", "fuel_charge", "late_return_charge", "extras_charge")
    }
    parts["extra_charge_total"] = round(sum(parts.values()), 2)
    return parts


def quote(record: Dict[str, Any]) -> Dict[str, float]:
    """The full quoted total and the deposit payable on it."""
    rental = rental_charge(record)
    extras = extra_charges(record)
    total = round(rental["duration_charge"] + extras["extra_charge_total"], 2)
    return {
        **rental,
        **extras,
        "quoted_total": total,
        "deposit_payable": round(_num(record, "deposit_amount"), 2),
    }


def deposit_release(record: Dict[str, Any]) -> Dict[str, float]:
    """How much of the held deposit is released, and what stays outstanding."""
    due = round(_num(record, "amount_due"), 2)
    held = round(_num(record, "deposit_held"), 2)
    return {
        "amount_due": due,
        "deposit_held": held,
        "deposit_release_due": held,
        "outstanding_balance": round(max(due - held, 0.0), 2),
    }


def utilisation(rented_vehicles: int, fleet_size: int) -> float:
    """Fleet utilisation as a percentage, 0.0 when the fleet is empty."""
    if fleet_size <= 0:
        return 0.0
    return round(100.0 * float(rented_vehicles) / float(fleet_size), 2)
