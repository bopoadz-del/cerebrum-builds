"""Construct block inputs from a domain record. Never demand block-specific keys."""

from __future__ import annotations

from typing import Any, Dict


def _ref(payload: Dict[str, Any]) -> str:
    return str(payload.get("reference") or "sample")


def _summary(payload: Dict[str, Any]) -> str:
    period = payload.get("period") or "sample"
    account = payload.get("account_name") or _ref(payload)
    return (
        f"financeops {_ref(payload)} period={period} "
        f"account={account} status={payload.get('status', 'open')}"
    )


def audit_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "category": "admin",
        "user_id": "operator",
        "event_action": "persist",
        "resource": _ref(payload),
        "details": {
            "status": payload.get("status", "open"),
            "summary": _summary(payload),
            "period": payload.get("period"),
            "account_name": payload.get("account_name"),
        },
    }
