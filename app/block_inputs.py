"""Construct block inputs from a domain record. Never demand block-specific keys."""

from __future__ import annotations

from typing import Any, Dict, List


def _ref(payload: Dict[str, Any]) -> str:
    return str(payload.get("reference") or "sample")


def _status(payload: Dict[str, Any]) -> str:
    return str(payload.get("status") or "open")


def _summary(payload: Dict[str, Any]) -> str:
    title = payload.get("title") or payload.get("resource_ref") or _ref(payload)
    return f"note {_ref(payload)} title={title} status={_status(payload)}"


def _result_seed(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Store workflow / kit shims read input['result']. Schema sample omits it."""
    return {
        "reference": _ref(payload),
        "status": _status(payload),
        "summary": _summary(payload),
    }


def prepare_block_input(block_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Factory-grounded constructed input for a declared Store block."""
    if block_id == "audit":
        return audit_input(payload)
    return {"result": _result_seed(payload), "reference": _ref(payload)}


def audit_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Construct audit.log input. Do not demand block keys from the caller."""
    event_kind = str(payload.get("event_kind") or payload.get("capability") or "create")
    return {
        "category": "data_access",
        "user_id": str(payload.get("actor") or payload.get("user_id") or "operator"),
        "event_action": str(payload.get("capability") or event_kind),
        "resource": str(payload.get("resource_ref") or _ref(payload)),
        "details": {
            "status": _status(payload),
            "summary": _summary(payload),
            "event_kind": event_kind,
            "title": payload.get("title") or payload.get("resource_ref") or _ref(payload),
        },
        "result": _result_seed(payload),
    }


def record_mutation_audit(
    principal: Any,
    *,
    action: str,
    resource: str,
    details: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Attribute a mutation. Persistable audit fields — do not invent caller keys."""
    extra = dict(details or {})
    return {
        "reference": resource,
        "status": extra.pop("status", "open"),
        "actor": principal.subject,
        "actor_role": principal.role,
        "event_action": action,
        **extra,
    }


def prepared_inputs(block_ids: List[str], payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {block_id: prepare_block_input(block_id, payload) for block_id in block_ids}
