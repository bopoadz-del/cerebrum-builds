"""Construct block inputs from a domain record. Never demand block-specific keys."""

from __future__ import annotations

from typing import Any, Dict


def _ref(payload: Dict[str, Any]) -> str:
    return str(payload.get("reference") or "sample")


def _summary(payload: Dict[str, Any]) -> str:
    sku = payload.get("sku") or _ref(payload)
    movement = payload.get("movement") or "receive"
    return (
        f"retail inventory {_ref(payload)} sku={sku} "
        f"movement={movement} status={payload.get('status', 'open')}"
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
            "sku": payload.get("sku"),
            "movement": payload.get("movement"),
            "location": payload.get("location"),
        },
    }
