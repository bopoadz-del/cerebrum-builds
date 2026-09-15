"""Construct block inputs from a domain record. Never demand block-specific keys."""

from __future__ import annotations

from typing import Any, Dict, List


def _ref(payload: Dict[str, Any]) -> str:
    return str(payload.get("reference") or "sample")


def _status(payload: Dict[str, Any]) -> str:
    return str(payload.get("status") or "open")


def _summary(payload: Dict[str, Any]) -> str:
    unit = (
        payload.get("make")
        or payload.get("desk_name")
        or payload.get("view_name")
        or payload.get("resource_label")
        or payload.get("branch_code")
        or _ref(payload)
    )
    return f"auto {_ref(payload)} unit={unit} status={_status(payload)}"


def _result_seed(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Store workflow / kit shims read input['result']. Schema sample omits it."""
    return {
        "reference": _ref(payload),
        "status": _status(payload),
        "summary": _summary(payload),
    }


def prepare_block_input(block_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Factory-grounded constructed input for a declared Store block."""
    builders = {
        "audit": audit_input,
        "dashboard": dashboard_input,
        "team": team_input,
    }
    builder = builders.get(block_id)
    if builder is None:
        return {"result": _result_seed(payload), "reference": _ref(payload)}
    return builder(payload)


def audit_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "category": "data_access",
        "user_id": str(payload.get("actor") or payload.get("user_id") or "operator"),
        "event_action": str(payload.get("capability") or payload.get("event_kind") or "auto_mutate"),
        "resource": _ref(payload),
        "details": {
            "status": _status(payload),
            "summary": _summary(payload),
            "event_kind": payload.get("event_kind") or "listing",
        },
        "result": _result_seed(payload),
    }


def dashboard_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "user_id": str(payload.get("actor") or payload.get("user_id") or "operator"),
        "title": f"Lot {_ref(payload)}",
        "theme": "light",
        "layout": "grid",
        "summary": _summary(payload),
        "result": _result_seed(payload),
    }


def team_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    name = str(payload.get("desk_name") or payload.get("reference") or "sample")
    return {
        "user_id": str(payload.get("actor") or payload.get("user_id") or "operator"),
        "name": f"Desk {name}",
        "plan": "free",
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
