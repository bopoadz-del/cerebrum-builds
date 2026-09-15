"""Construct block inputs from a domain record. Never demand block-specific keys."""

from __future__ import annotations

from typing import Any, Dict, List


def _ref(payload: Dict[str, Any]) -> str:
    return str(payload.get("reference") or "sample")


def _status(payload: Dict[str, Any]) -> str:
    return str(payload.get("status") or "open")


def _summary(payload: Dict[str, Any]) -> str:
    title = payload.get("title") or payload.get("resource") or _ref(payload)
    return f"note {_ref(payload)} title={title} status={_status(payload)}"


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
        "event_bus": event_bus_input,
        "workflow": workflow_input,
    }
    builder = builders.get(block_id)
    if builder is None:
        return {"result": _result_seed(payload), "reference": _ref(payload)}
    return builder(payload)


def audit_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "category": "data_access",
        "user_id": str(payload.get("actor") or payload.get("user_id") or "operator"),
        "event_action": str(payload.get("event_action") or payload.get("capability") or "audit"),
        "resource": str(payload.get("resource") or _ref(payload)),
        "details": {
            "status": _status(payload),
            "summary": _summary(payload),
            "title": payload.get("title") or _ref(payload),
        },
        "result": _result_seed(payload),
    }


def event_bus_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    topic = str(
        payload.get("event")
        or payload.get("event_type")
        or payload.get("event_name")
        or payload.get("note_op")
        or f"note.{_ref(payload)}"
    )
    return {
        "topic": topic,
        "payload": {
            "reference": _ref(payload),
            "title": payload.get("title") or _ref(payload),
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
        "pipeline_id": f"note-{_ref(payload)}",
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
