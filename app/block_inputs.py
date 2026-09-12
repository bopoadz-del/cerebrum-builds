"""Construct block inputs from a domain record. Never demand block-specific keys."""

from __future__ import annotations

from typing import Any, Dict


def _ref(payload: Dict[str, Any]) -> str:
    return str(payload.get("reference") or "sample")


def _summary(payload: Dict[str, Any]) -> str:
    vin = payload.get("vin") or _ref(payload)
    deal = payload.get("deal_type") or "retail"
    return f"dealership record {_ref(payload)} vin={vin} deal={deal} status={payload.get('status', 'open')}"


def audit_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "category": "admin",
        "user_id": "operator",
        "event_action": "persist",
        "resource": _ref(payload),
        "details": {
            "status": payload.get("status", "open"),
            "summary": _summary(payload),
            "vin": payload.get("vin"),
            "deal_type": payload.get("deal_type"),
        },
    }
