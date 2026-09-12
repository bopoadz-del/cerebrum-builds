"""Construct block inputs from a domain record. Never demand block-specific keys."""

from __future__ import annotations

from typing import Any, Dict


def _ref(payload: Dict[str, Any]) -> str:
    return str(payload.get("reference") or "sample")


def _summary(payload: Dict[str, Any]) -> str:
    return f"finance record {_ref(payload)} status={payload.get('status', 'open')}"


def team_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    reference = _ref(payload)
    return {
        "user_id": "operator",
        "name": f"finance-{reference}",
        "slug": f"finance-{reference}".replace(" ", "-"),
        "plan": "free",
    }


def audit_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "category": "admin",
        "user_id": "operator",
        "event_action": "persist",
        "resource": _ref(payload),
        "details": {"status": payload.get("status", "open"), "summary": _summary(payload)},
    }
