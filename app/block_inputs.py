"""Construct block inputs from a domain record. Never demand block-specific keys."""

from __future__ import annotations

from typing import Any, Dict

from app.auth import Principal, require_principal

# Client-supplied identity claims are never the sole Principal.
_CLIENT_IDENTITY_KEYS = frozenset(
    {"actor", "user_id", "principal", "subject", "actor_role"}
)


def _ref(payload: Dict[str, Any]) -> str:
    return str(payload.get("reference") or "sample")


def _summary(payload: Dict[str, Any]) -> str:
    period = payload.get("period") or "sample"
    account = payload.get("account_name") or _ref(payload)
    return (
        f"financeops {_ref(payload)} period={period} "
        f"account={account} status={payload.get('status', 'open')}"
    )


def claimed_client_identity(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        key: payload[key]
        for key in _CLIENT_IDENTITY_KEYS
        if key in payload and payload[key] not in (None, "")
    }


def bind_payload_principal(payload: Dict[str, Any], principal: Principal) -> Dict[str, Any]:
    """Overwrite client identity with the authenticated principal."""
    claimed = claimed_client_identity(payload)
    cleaned = {key: value for key, value in payload.items() if key not in _CLIENT_IDENTITY_KEYS}
    bound = {
        **cleaned,
        "actor": principal.subject,
        "actor_role": principal.role,
    }
    if claimed:
        bound["claimed_actor"] = claimed
    return bound


def audit_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Bind user_id to the authenticated principal only. Raise if unbound."""
    principal = require_principal()
    claimed = payload.get("claimed_actor") or claimed_client_identity(payload)
    return {
        "category": "admin",
        "user_id": principal.subject,
        "event_action": payload.get("event_action") or "persist",
        "resource": _ref(payload),
        "details": {
            "status": payload.get("status", "open"),
            "summary": _summary(payload),
            "period": payload.get("period"),
            "account_name": payload.get("account_name"),
            "actor": principal.subject,
            "actor_role": principal.role,
            "claimed_actor": claimed or None,
            "capability": payload.get("capability"),
        },
    }


def record_mutation_audit(
    principal: Principal,
    *,
    action: str,
    resource: str,
    details: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Persist a Principal-attributed audit event. Fail closed — do not swallow."""
    from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
    from app.persist import persist_record

    extra = dict(details or {})
    payload = bind_payload_principal(
        {
            "reference": resource,
            "status": extra.pop("status", "open"),
            "event_action": action,
            "category": extra.pop("category", "admin"),
            **extra,
        },
        principal,
    )
    execute("audit", audit_input(payload), action=BLOCK_DEFAULT_ACTIONS.get("audit"))
    persist_record("audit", payload)
    return payload
