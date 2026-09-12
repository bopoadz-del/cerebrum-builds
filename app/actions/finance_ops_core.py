"""finance_ops_core — GENERATE. FP&A kernel: CoA, budget vs actual, cash, close, intake."""

from __future__ import annotations

from typing import Any, Dict

from app.persist import ok_envelope

# READS: caller.input
# WRITES: caller.output
# NEVER: inventing unverified Store block ids

BLOCK_IDS: list[str] = []


def _coa_line(payload: Dict[str, Any]) -> Dict[str, Any]:
    reference = str(payload.get("reference") or "sample")
    account_name = str(payload.get("account_name") or reference)
    return {
        "code": reference,
        "name": account_name,
        "type": "operating",
        "status": payload.get("status", "open"),
    }


def _budget_vs_actual(payload: Dict[str, Any]) -> Dict[str, Any]:
    period = str(payload.get("period") or "sample")
    return {
        "period": period,
        "budget": 0,
        "actual": 0,
        "variance": 0,
        "status": payload.get("status", "open"),
    }


def _cash_forecast(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "horizon_days": 30,
        "opening": 0,
        "inflows": 0,
        "outflows": 0,
        "closing": 0,
        "reference": payload.get("reference", "sample"),
    }


def _close_checklist(payload: Dict[str, Any]) -> list[Dict[str, Any]]:
    status = payload.get("status", "open")
    return [
        {"item": "reconcile_subledgers", "status": status},
        {"item": "review_accruals", "status": status},
        {"item": "lock_period", "status": "closed" if status == "closed" else status},
    ]


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Author the FP&A kernel from the envelope. No Store blocks are bound."""
    record = {
        **payload,
        "chart_of_accounts": [_coa_line(payload)],
        "budget_vs_actual": _budget_vs_actual(payload),
        "cash_forecast": _cash_forecast(payload),
        "close_checklist": _close_checklist(payload),
        "board_pack_intake": {
            "reference": payload.get("reference", "sample"),
            "channel": "mcp",
            "status": payload.get("status", "open"),
        },
    }
    return ok_envelope("finance_ops_core", record)
