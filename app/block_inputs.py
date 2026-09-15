"""Construct block inputs from a domain record. Never demand block-specific keys."""

from __future__ import annotations

from typing import Any, Dict, List


def _ref(payload: Dict[str, Any]) -> str:
    return str(payload.get("reference") or "sample")


def _status(payload: Dict[str, Any]) -> str:
    return str(payload.get("status") or "open")


def _summary(payload: Dict[str, Any]) -> str:
    unit = (
        payload.get("branch")
        or payload.get("view_name")
        or payload.get("desk")
        or payload.get("note")
        or _ref(payload)
    )
    return f"automotive {_ref(payload)} unit={unit} status={_status(payload)}"


def _result_seed(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Store workflow / kit shims read input['result']. Schema sample omits it."""
    return {
        "reference": _ref(payload),
        "status": _status(payload),
        "summary": _summary(payload),
    }


def prepare_block_input(block_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    builders = {
        "audit": audit_input,
        "dashboard": dashboard_input,
        "team": team_input,
        "event_bus": event_bus_input,
        "workflow": workflow_input,
    }
    builder = builders.get(block_id)
    if builder is None:
        return {"result": _result_seed(payload), "reference": _ref(payload)}
    return builder(payload)


def audit_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "category": str(payload.get("category") or "data_access"),
        "user_id": str(payload.get("actor") or payload.get("user_id") or "operator"),
        "event_action": str(payload.get("capability") or "automotive_mutate"),
        "resource": _ref(payload),
        "details": {
            "status": _status(payload),
            "summary": _summary(payload),
            "note": str(payload.get("note") or _summary(payload)),
        },
        "result": _result_seed(payload),
    }


def dashboard_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "user_id": str(payload.get("actor") or payload.get("user_id") or "operator"),
        "title": f"Automotive {_ref(payload)}",
        "theme": "light",
        "layout": "grid",
        "summary": _summary(payload),
        "result": _result_seed(payload),
    }


def team_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    name = str(payload.get("branch") or payload.get("desk") or payload.get("reference") or "sample")
    suffix = str(payload.get("reference") or "sample")
    return {
        "user_id": str(payload.get("actor") or payload.get("user_id") or "operator"),
        "name": f"Auto {name} {suffix}",
        "plan": "free",
        "result": _result_seed(payload),
    }


def event_bus_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    topic = str(
        payload.get("event")
        or payload.get("event_type")
        or payload.get("event_name")
        or payload.get("reminder_type")
        or f"automotive.{_ref(payload)}"
    )
    return {
        "topic": topic,
        "payload": {
            "reference": _ref(payload),
            "branch": payload.get("branch") or _ref(payload),
            "status": _status(payload),
        },
        "message": _summary(payload),
        "channel": "mcp",
        "tool": "event_bus",
        "result": _result_seed(payload),
    }


def prepared_event_bus_step(payload: Dict[str, Any], *, step_id: str = "step_0") -> Dict[str, Any]:
    prepared = event_bus_input(payload)
    return {
        "id": step_id,
        "block": "event_bus",
        "action": "publish",
        "params": {"action": "publish"},
        "input": {
            "topic": prepared["topic"],
            "payload": {"reference": _ref(payload)},
            "message": prepared["message"],
            "channel": "mcp",
            "tool": "event_bus",
            "result": _result_seed(payload),
        },
    }


def workflow_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    seed = _result_seed(payload)
    return {
        "pipeline_id": f"automotive-{_ref(payload)}",
        "result": seed,
        "steps": [
            prepared_event_bus_step(payload, step_id="step_0"),
            prepared_event_bus_step(payload, step_id="step_1"),
            prepared_event_bus_step(payload, step_id="step_2"),
        ],
    }


def record_mutation_audit(
    principal: Any,
    *,
    action: str,
    resource: str,
    details: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
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
