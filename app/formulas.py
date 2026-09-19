"""Deterministic FinOps formulas (utilisation, variance, spend split, rollup).

Written by the factory WRITER role (codewhale exec)

Pure stdlib arithmetic, no provider and no network: these are the finance
calculations the platform performs on its own records rather than sending to
the LLM. Every function refuses malformed input by name rather than
returning a number that looks authoritative; the caller sees why it could
not be computed.

Scope: READS the numbers handed in by a handler, WRITES a figure. It never
touches the store, the filesystem or the network.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

#: Standard-rate VAT applied to a gross UK spend line when splitting it.
STANDARD_VAT_RATE = 0.2


class FormulaError(ValueError):
    """A formula was asked for a figure its inputs cannot support."""


def to_number(value: Any, name: str) -> float:
    """Coerce a finance figure, or refuse by name."""
    if isinstance(value, bool) or value is None:
        raise FormulaError(f"{name} must be a number")
    try:
        return float(value)
    except (TypeError, ValueError):
        raise FormulaError(f"{name} must be a number, got {type(value).__name__}") from None


def _number(value: Any, name: str) -> float:
    return to_number(value, name)


def budget_utilisation(*, planned_amount: Any, actual_amount: Any) -> float:
    """Actual spend as a percentage of the allocation."""
    planned = _number(planned_amount, "planned_amount")
    actual = _number(actual_amount, "actual_amount")
    if planned <= 0:
        raise FormulaError("planned_amount must be greater than zero")
    if actual < 0:
        raise FormulaError("actual_amount cannot be negative")
    return round((actual / planned) * 100.0, 4)


def budget_remaining(*, planned_amount: Any, actual_amount: Any) -> float:
    """Allocation not yet committed."""
    planned = _number(planned_amount, "planned_amount")
    actual = _number(actual_amount, "actual_amount")
    return round(planned - actual, 4)


def budget_overrun(*, planned_amount: Any, actual_amount: Any) -> bool:
    """True when spend has passed the allocation."""
    planned = _number(planned_amount, "planned_amount")
    actual = _number(actual_amount, "actual_amount")
    return actual > planned


def spend_net(*, amount: Any, vat_rate: Any = STANDARD_VAT_RATE) -> float:
    """Net-of-VAT figure for a gross spend line."""
    gross = _number(amount, "amount")
    rate = _number(vat_rate, "vat_rate")
    if rate <= -1:
        raise FormulaError("vat_rate must be greater than -100%")
    if gross < 0:
        raise FormulaError("amount cannot be negative")
    return round(gross / (1.0 + rate), 4)


def spend_vat(*, amount: Any, vat_rate: Any = STANDARD_VAT_RATE) -> float:
    """VAT element of a gross spend line."""
    gross = _number(amount, "amount")
    return round(gross - spend_net(amount=gross, vat_rate=vat_rate), 4)


def variance_amount(*, budget_amount: Any, actual_amount: Any) -> float:
    """Actual minus budget. Negative is underspend (favourable)."""
    budget = _number(budget_amount, "budget_amount")
    actual = _number(actual_amount, "actual_amount")
    return round(actual - budget, 4)


def variance_percent(*, budget_amount: Any, actual_amount: Any) -> float:
    """Variance against the budget, as a percentage of the budget."""
    budget = _number(budget_amount, "budget_amount")
    if budget == 0:
        raise FormulaError("budget_amount must be non-zero for a percentage")
    return round((variance_amount(budget_amount=budget, actual_amount=actual_amount) / budget) * 100.0, 4)


def portfolio_total(
    *, spend_total: Any, commitment_total: Any = 0, forecast_total: Any = 0
) -> float:
    """Committed position: spend plus outstanding commitments."""
    spend = _number(spend_total, "spend_total")
    commitment = _number(commitment_total or 0, "commitment_total")
    forecast = _number(forecast_total or 0, "forecast_total")
    if min(spend, commitment, forecast) < 0:
        raise FormulaError("portfolio totals cannot be negative")
    return round(spend + commitment, 4)


def forecast_confidence(
    *, spend_total: Any, commitment_total: Any = 0, forecast_total: Any = 0
) -> float:
    """How much of the forecast is already evidenced by spend/commitment."""
    forecast = _number(forecast_total or 0, "forecast_total")
    if forecast <= 0:
        raise FormulaError("forecast_total must be greater than zero")
    evidenced = round(
        _number(spend_total, "spend_total") + _number(commitment_total or 0, "commitment_total"),
        4,
    )
    return round(min(1.0, evidenced / forecast), 4)


def portfolio_risk(*, spend_total: Any, forecast_total: Any = 0) -> str:
    """Risk band for a department line: low, medium or high.

    High when committed spend has already passed the forecast; medium when
    it is within 10% of it. A line with no forecast has no band to report.
    """
    forecast = _number(forecast_total or 0, "forecast_total")
    if forecast <= 0:
        return "low"
    spend = _number(spend_total, "spend_total")
    if spend > forecast:
        return "high"
    if spend >= forecast * 0.9:
        return "medium"
    return "low"


def account_rollup(lines: Iterable[Dict[str, Any]]) -> Dict[str, float]:
    """Sum spend by account code across the lines handed in."""
    totals: Dict[str, float] = {}
    for line in lines or ():
        if not isinstance(line, dict):
            continue
        code = str(line.get("account_code") or "unmapped")
        totals[code] = round(totals.get(code, 0.0) + _number(line.get("amount") or 0, "amount"), 4)
    return totals


def evaluate(name: str, **kwargs: Any) -> Dict[str, Any]:
    """Named evaluation used by the capability handlers."""
    library = {
        "budget_utilisation": budget_utilisation,
        "budget_remaining": budget_remaining,
        "budget_overrun": budget_overrun,
        "spend_net": spend_net,
        "spend_vat": spend_vat,
        "variance_amount": variance_amount,
        "variance_percent": variance_percent,
        "portfolio_total": portfolio_total,
        "forecast_confidence": forecast_confidence,
    }
    fn = library.get(str(name or ""))
    if fn is None:
        raise FormulaError("unknown formula: " + str(name))
    return {"formula": name, "result": fn(**kwargs)}
