"""Construct block inputs from a domain record. Never demand block-specific keys."""

from __future__ import annotations

from typing import Any, Dict


def _ref(payload: Dict[str, Any]) -> str:
    return str(payload.get("reference") or "sample")


def _summary(payload: Dict[str, Any]) -> str:
    carrier = payload.get("carrier_code") or "RX"
    hub = payload.get("hub_city") or payload.get("station") or "Riyadh"
    return (
        f"airops record {_ref(payload)} carrier={carrier} hub={hub} "
        f"status={payload.get('status', 'open')}"
    )


def audit_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    actor = str(payload.get("actor") or payload.get("user_id") or "unattributed")
    return {
        "category": payload.get("category") or "admin",
        "user_id": actor,
        "event_action": payload.get("event_action") or "persist",
        "resource": _ref(payload),
        "details": {
            "status": payload.get("status", "open"),
            "summary": _summary(payload),
            "carrier_code": payload.get("carrier_code") or "RX",
            "actor": actor,
            "actor_role": payload.get("actor_role"),
            "capability": payload.get("capability"),
        },
    }


def dashboard_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "user_id": str(payload.get("actor") or payload.get("user_id") or "operator"),
        "title": f"AirOps portfolio {_ref(payload)}",
        "theme": "light",
        "layout": "grid",
        "summary": _summary(payload),
    }


def gdpr_audit_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    actor = str(payload.get("actor") or payload.get("user_id") or "unattributed")
    return {
        "category": "data_access",
        "user_id": actor,
        "event_action": payload.get("event_action") or "gdpr_privacy_review",
        "resource": _ref(payload),
        "details": {
            "status": payload.get("status", "open"),
            "lawful_basis": payload.get("lawful_basis") or "legitimate_interest",
            "data_subject": payload.get("data_subject") or "sample",
            "fail_closed_auth": True,
            "principal_audit": True,
            "cors": True,
            "actor": actor,
            "actor_role": payload.get("actor_role"),
            "capability": "gdpr_privacy_audit",
        },
    }


def record_mutation_audit(
    principal: Any,
    *,
    action: str,
    resource: str,
    details: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Persist a Principal-attributed audit event for a mutation."""
    from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
    from app.persist import persist_record

    extra = dict(details or {})
    payload = {
        "reference": resource,
        "status": extra.pop("status", "open"),
        "actor": principal.subject,
        "actor_role": principal.role,
        "event_action": action,
        "category": extra.pop("category", "admin"),
        **extra,
    }
    execute("audit", audit_input(payload), action=BLOCK_DEFAULT_ACTIONS.get("audit"))
    persist_record("audit", payload)
    return payload
