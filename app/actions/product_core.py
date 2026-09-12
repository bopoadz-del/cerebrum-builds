"""product_core — GENERATE. FP&A kernel: chart of accounts, budget vs actual."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.persist import ok_envelope

# READS: caller.input
# WRITES: caller.output
# NEVER: inventing unverified Store block ids; claiming KPI zeros without inputs

BLOCK_IDS: list[str] = []

_ASSET_KEYS = ("cash", "bank", "receivable", "inventory", "asset", "prepaid")
_LIABILITY_KEYS = ("payable", "debt", "loan", "liability", "accrual", "unearned")
_EQUITY_KEYS = ("equity", "capital", "retained", "owner")
_REVENUE_KEYS = ("revenue", "sales", "income", "fee")
_EXPENSE_KEYS = ("cogs", "expense", "opex", "cost", "payroll", "rent", "depreciation")


def _parse_amount(value: Any) -> Tuple[Optional[int], bool]:
    """Parse a money field. Missing/invalid is absent — not a silent zero KPI."""
    if value is None or value == "":
        return None, False
    try:
        amount = int(value)
    except (TypeError, ValueError):
        return None, False
    return max(amount, 0), True


def _account_type(payload: Dict[str, Any]) -> str:
    text = f"{payload.get('account_name') or ''} {payload.get('reference') or ''}".lower()
    for keys, label in (
        (_ASSET_KEYS, "asset"),
        (_LIABILITY_KEYS, "liability"),
        (_EQUITY_KEYS, "equity"),
        (_REVENUE_KEYS, "revenue"),
        (_EXPENSE_KEYS, "expense"),
    ):
        if any(key in text for key in keys):
            return label
    return "operating"


def _coa_line(payload: Dict[str, Any]) -> Dict[str, Any]:
    reference = str(payload.get("reference") or "sample")
    account_name = str(payload.get("account_name") or reference)
    account_type = _account_type(payload)
    normal_balance = "credit" if account_type in {"liability", "equity", "revenue"} else "debit"
    return {
        "code": reference,
        "name": account_name,
        "type": account_type,
        "normal_balance": normal_balance,
        "status": payload.get("status", "open"),
    }


def _ratio(numerator: Optional[int], denominator: Optional[int]) -> Optional[float]:
    if numerator is None or denominator in (None, 0):
        return None
    return round((numerator / denominator) * 100, 4)


def _budget_vs_actual(payload: Dict[str, Any], account_type: str) -> Dict[str, Any]:
    budget, budget_present = _parse_amount(payload.get("budget_amount"))
    actual, actual_present = _parse_amount(payload.get("actual_amount"))
    complete = budget_present and actual_present
    variance = (actual - budget) if complete else None
    if variance is None:
        direction = "unknown"
    elif account_type == "revenue":
        direction = "favorable" if variance >= 0 else "unfavorable"
    else:
        direction = "favorable" if variance <= 0 else "unfavorable"
    return {
        "period": str(payload.get("period") or "sample"),
        "budget": budget,
        "actual": actual,
        "variance": variance,
        "variance_pct": _ratio(variance, budget) if complete else None,
        "utilization_pct": _ratio(actual, budget) if complete else None,
        "direction": direction,
        "inputs_complete": complete,
        "status": payload.get("status", "open"),
    }


def _cash_forecast(
    payload: Dict[str, Any], account_type: str, bva: Dict[str, Any]
) -> Dict[str, Any]:
    """Derive cash from BvA inputs. Do not invent the missing side as zero."""
    opening = bva["budget"]
    actual = bva["actual"]
    if account_type in {"revenue", "asset"}:
        inflows = actual
        outflows = None
        closing = (opening + inflows) if opening is not None and inflows is not None else None
    else:
        inflows = None
        outflows = actual
        closing = (opening - outflows) if opening is not None and outflows is not None else None
    horizon_days = 30
    daily_burn = None
    if outflows is not None and outflows > 0:
        daily_burn = round(outflows / horizon_days, 4)
    runway_days = None
    if closing is not None and daily_burn:
        runway_days = round(closing / daily_burn, 4)
    return {
        "horizon_days": horizon_days,
        "opening": opening,
        "inflows": inflows,
        "outflows": outflows,
        "closing": closing,
        "daily_burn": daily_burn,
        "runway_days": runway_days,
        "basis": "budget_as_opening_actual_as_period_cash",
        "reference": payload.get("reference", "sample"),
    }


def _close_checklist(payload: Dict[str, Any], bva: Dict[str, Any]) -> List[Dict[str, Any]]:
    status = payload.get("status", "open")
    bva_ready = "closed" if bva.get("inputs_complete") else status
    return [
        {"item": "reconcile_subledgers", "status": status},
        {"item": "review_accruals", "status": status},
        {"item": "review_budget_vs_actual", "status": bva_ready},
        {"item": "lock_period", "status": "closed" if status == "closed" else status},
    ]


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Author the FinanceOps FP&A kernel from the envelope. No Store blocks are bound."""
    account_type = _account_type(payload)
    bva = _budget_vs_actual(payload, account_type)
    record = {
        **payload,
        "chart_of_accounts": [_coa_line(payload)],
        "budget_vs_actual": bva,
        "cash_forecast": _cash_forecast(payload, account_type, bva),
        "close_checklist": _close_checklist(payload, bva),
        "board_pack_intake": {
            "reference": payload.get("reference", "sample"),
            "channel": "mcp",
            "status": payload.get("status", "open"),
        },
    }
    return ok_envelope("product_core", record)
