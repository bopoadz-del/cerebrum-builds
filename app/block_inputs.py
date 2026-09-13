"""Construct block inputs from a domain record. Never demand block-specific keys."""

from __future__ import annotations

from typing import Any, Dict, List


def _ref(payload: Dict[str, Any]) -> str:
    return str(payload.get("reference") or "sample")


def _status(payload: Dict[str, Any]) -> str:
    return str(payload.get("status") or "open")


def _summary(payload: Dict[str, Any]) -> str:
    unit = (
        payload.get("clinic_unit")
        or payload.get("patient_name")
        or payload.get("slot_label")
        or _ref(payload)
    )
    return f"vetcare {_ref(payload)} unit={unit} status={_status(payload)}"


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
        "analytics": analytics_input,
        "audit": audit_input,
        "dashboard": dashboard_input,
        "event_bus": event_bus_input,
        "knowledge": knowledge_input,
        "memory": memory_input,
        "notification": notification_input,
        "queue": queue_input,
        "validation": validation_input,
        "vector_search": vector_search_input,
        "workflow": workflow_input,
    }
    builder = builders.get(block_id)
    if builder is None:
        return {"result": _result_seed(payload), "reference": _ref(payload)}
    return builder(payload)


def analytics_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    value = payload.get("clinic_load_score")
    try:
        metric_value = float(value)
    except (TypeError, ValueError):
        metric_value = 1.0
    return {
        "metric": "vetcare_clinic_events",
        "value": metric_value,
        "tags": {
            "reference": _ref(payload),
            "clinic_unit": str(payload.get("clinic_unit") or _ref(payload)),
            "horizon": str(
                payload.get("horizon") or payload.get("caseload_window") or "today"
            ),
            "status": _status(payload),
        },
        "result": _result_seed(payload),
    }


def audit_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    actor = str(payload.get("actor") or payload.get("user_id") or "unattributed")
    return {
        "category": payload.get("category")
        or payload.get("event_category")
        or "clinical",
        "user_id": actor,
        "event_action": payload.get("event_action") or "persist",
        "resource": _ref(payload),
        "details": {
            "status": _status(payload),
            "summary": _summary(payload),
            "actor": actor,
            "actor_role": payload.get("actor_role"),
            "capability": payload.get("capability"),
            "claimed_actor": payload.get("claimed_actor"),
        },
        "result": _result_seed(payload),
    }


def dashboard_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "user_id": str(payload.get("actor") or payload.get("user_id") or "operator"),
        "title": f"VetCare {_ref(payload)}",
        "theme": "light",
        "layout": "grid",
        "summary": _summary(payload),
        "result": _result_seed(payload),
    }


def event_bus_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    topic = str(
        payload.get("event")
        or payload.get("event_type")
        or payload.get("event_name")
        or payload.get("visit_type")
        or payload.get("message_kind")
        or payload.get("reminder_type")
        or f"vetcare.{_ref(payload)}"
    )
    return {
        "topic": topic,
        "payload": {
            "reference": _ref(payload),
            "patient_name": payload.get("patient_name") or _ref(payload),
            "status": _status(payload),
        },
        "message": _summary(payload),
        "channel": "mcp",
        "tool": "event_bus",
        "result": _result_seed(payload),
    }


def prepared_event_bus_step(payload: Dict[str, Any], *, step_id: str = "step_0") -> Dict[str, Any]:
    """Exact PRODUCT event_bus workflow child. Never set input to the raw sample."""
    prepared = event_bus_input(payload)
    return {
        "id": step_id,
        "block": "event_bus",
        "action": "publish",
        "params": {"action": "publish"},
        "input": prepared,
    }


def knowledge_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    question = (
        payload.get("question")
        or payload.get("patient_name")
        or payload.get("client_name")
        or _summary(payload)
    )
    return {
        "question": str(question),
        "query": str(question),
        "result": _result_seed(payload),
    }


def memory_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "key": f"vetcare:{_ref(payload)}",
        "value": {
            "reference": _ref(payload),
            "patient_name": payload.get("patient_name") or "sample",
            "status": _status(payload),
        },
        "result": _result_seed(payload),
    }


def notification_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    message = payload.get("message") or f"VetCare notice for {_ref(payload)}"
    topic = str(
        payload.get("visit_type")
        or payload.get("message_kind")
        or payload.get("event")
        or f"vetcare.{_ref(payload)}"
    )
    return {
        "channel": "mcp",
        "message": str(message),
        "tool": "event_bus",
        "block": "event_bus",
        "payload": {
            "reference": _ref(payload),
            "status": _status(payload),
        },
        "params": {"action": "publish", "topic": topic},
        "result": _result_seed(payload),
    }


def queue_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "job_type": "clinic_task",
        "queue": "clinic",
        "payload": {
            "reference": _ref(payload),
            "visit_type": payload.get("visit_type") or "wellness",
            "slot_label": payload.get("slot_label") or _ref(payload),
            "status": _status(payload),
        },
        "result": _result_seed(payload),
    }


def validation_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    item = {
        "id": _ref(payload),
        "type": "vetcare_record",
        "status": _status(payload),
        "medication_name": payload.get("medication_name") or payload.get("line_label") or _ref(payload),
    }
    return {
        "item": item,
        "context": {"channel": "mcp", "summary": _summary(payload)},
        "result": _result_seed(payload),
    }


def vector_search_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    query = str(
        payload.get("patient_name")
        or payload.get("question")
        or payload.get("note_body")
        or _summary(payload)
    )
    return {
        "query": query,
        "text": query,
        "result": _result_seed(payload),
    }


def workflow_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Default clinic pipeline. Appointment scheduling overrides in-handler."""
    seed = _result_seed(payload)
    queue_step = {
        "id": "step_0",
        "block": "queue",
        "action": "enqueue",
        "params": {"action": "enqueue"},
        "input": queue_input(payload),
    }
    notify_step = {
        "id": "step_1",
        "block": "notification",
        "action": "send",
        "params": {"action": "send"},
        "input": notification_input(payload),
    }
    return {
        "pipeline_id": f"clinic-{_ref(payload)}",
        "result": seed,
        "steps": [queue_step, notify_step],
    }


def appointment_workflow_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Prepared event_bus children for step_0, step_1, and step_2+."""
    seed = _result_seed(payload)
    steps = [
        prepared_event_bus_step(payload, step_id="step_0"),
        prepared_event_bus_step(payload, step_id="step_1"),
        prepared_event_bus_step(payload, step_id="step_2"),
    ]
    return {
        "pipeline_id": f"appointment-{_ref(payload)}",
        "result": seed,
        "steps": steps,
    }


def record_mutation_audit(
    principal: Any,
    *,
    action: str,
    resource: str,
    details: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Log a Principal-attributed audit event. Does not persist to a phantom entity."""
    from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute

    extra = dict(details or {})
    payload = {
        "reference": resource,
        "status": extra.pop("status", "open"),
        "actor": principal.subject,
        "actor_role": principal.role,
        "event_action": action,
        "category": extra.pop("category", "clinical"),
        **extra,
    }
    execute("audit", audit_input(payload), action=BLOCK_DEFAULT_ACTIONS.get("audit"))
    return payload


def prepared_inputs(block_ids: List[str], payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {block_id: prepare_block_input(block_id, payload) for block_id in block_ids}
