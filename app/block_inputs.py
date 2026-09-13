"""Construct block inputs from a domain record. Never demand block-specific keys."""

from __future__ import annotations

from typing import Any, Dict, List


def _ref(payload: Dict[str, Any]) -> str:
    return str(payload.get("reference") or "sample")


def _status(payload: Dict[str, Any]) -> str:
    return str(payload.get("status") or "open")


def _sku(payload: Dict[str, Any]) -> str:
    return str(payload.get("sku") or _ref(payload))


def _summary(payload: Dict[str, Any]) -> str:
    return (
        f"retail ops {_ref(payload)} sku={_sku(payload)} "
        f"status={_status(payload)}"
    )


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
        "database": database_input,
        "validation": validation_input,
        "audit": audit_input,
        "workflow": workflow_input,
        "queue": queue_input,
        "notification": notification_input,
        "dashboard": dashboard_input,
        "analytics": analytics_input,
        "event_bus": event_bus_input,
        "knowledge": knowledge_input,
        "memory": memory_input,
        "storage": storage_input,
    }
    builder = builders.get(block_id)
    if builder is None:
        return {"result": _result_seed(payload), "reference": _ref(payload)}
    return builder(payload)


def database_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    table = str(payload.get("capability") or "inventory_tracking")
    return {
        "table": table,
        "filters": {"reference": _ref(payload)},
        "result": _result_seed(payload),
    }


def validation_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    item = {
        "id": _ref(payload),
        "type": "retail_sku",
        "quantity": int(payload.get("quantity_on_hand") or 0),
        "sku": _sku(payload),
        "status": _status(payload),
    }
    return {
        "item": item,
        "context": {"channel": "mcp", "summary": _summary(payload)},
        "result": _result_seed(payload),
    }


def audit_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    actor = str(payload.get("actor") or payload.get("user_id") or "unattributed")
    return {
        "category": payload.get("category") or "ops",
        "user_id": actor,
        "event_action": payload.get("event_action") or "persist",
        "resource": _ref(payload),
        "details": {
            "status": _status(payload),
            "summary": _summary(payload),
            "sku": _sku(payload),
            "actor": actor,
            "actor_role": payload.get("actor_role"),
            "capability": payload.get("capability"),
        },
        "result": _result_seed(payload),
    }


def queue_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "job_type": "fulfill_order",
        "queue": "orders",
        "payload": {
            "reference": _ref(payload),
            "order_number": payload.get("order_number") or _ref(payload),
            "status": _status(payload),
        },
        "result": _result_seed(payload),
    }


def notification_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    message = (
        payload.get("message")
        or f"Retail ops notice for {_ref(payload)} ({_sku(payload)})"
    )
    return {
        "channel": "mcp",
        "message": str(message),
        "tool": "event_bus",
        "block": "event_bus",
        "payload": {
            "reference": _ref(payload),
            "sku": _sku(payload),
            "status": _status(payload),
        },
        "params": {"action": "publish", "topic": f"retail.{_ref(payload)}"},
        "result": _result_seed(payload),
    }


def event_bus_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    topic = str(
        payload.get("event")
        or payload.get("event_type")
        or payload.get("event_name")
        or payload.get("alert_kind")
        or payload.get("reminder_type")
        or f"retail.{_ref(payload)}"
    )
    return {
        "topic": topic,
        "payload": {
            "reference": _ref(payload),
            "sku": _sku(payload),
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


def workflow_input(payload: Dict[str, Any]) -> Dict[str, Any]:
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
        "pipeline_id": f"order-{_ref(payload)}",
        "result": seed,
        "steps": [queue_step, notify_step],
    }


def dashboard_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "user_id": str(payload.get("actor") or payload.get("user_id") or "operator"),
        "title": f"Retail ops {_ref(payload)}",
        "theme": "light",
        "layout": "grid",
        "summary": _summary(payload),
        "result": _result_seed(payload),
    }


def analytics_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    qty = payload.get("quantity_on_hand")
    try:
        value = float(qty)
    except (TypeError, ValueError):
        value = 1.0
    return {
        "metric": "retail_ops_events",
        "value": value,
        "tags": {
            "reference": _ref(payload),
            "horizon": str(payload.get("horizon") or "today"),
            "status": _status(payload),
        },
        "result": _result_seed(payload),
    }


def knowledge_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    question = (
        payload.get("note_body")
        or payload.get("note_title")
        or _summary(payload)
    )
    return {
        "question": str(question),
        "query": str(question),
        "result": _result_seed(payload),
    }


def memory_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "key": f"pilot_ops:{_ref(payload)}",
        "value": {
            "reference": _ref(payload),
            "note_title": payload.get("note_title") or "sample",
            "status": _status(payload),
        },
        "result": _result_seed(payload),
    }


def storage_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    body = payload.get("note_body") or _summary(payload)
    return {
        "filename": f"{_ref(payload)}.md",
        "content": str(body),
        "metadata": {
            "reference": _ref(payload),
            "note_title": payload.get("note_title") or "sample",
            "status": _status(payload),
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
    """Log a Principal-attributed audit event. Does not persist to a phantom entity."""
    from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute

    extra = dict(details or {})
    payload = {
        "reference": resource,
        "status": extra.pop("status", "open"),
        "actor": principal.subject,
        "actor_role": principal.role,
        "event_action": action,
        "category": extra.pop("category", "ops"),
        **extra,
    }
    execute("audit", audit_input(payload), action=BLOCK_DEFAULT_ACTIONS.get("audit"))
    return payload


def prepared_inputs(block_ids: List[str], payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {block_id: prepare_block_input(block_id, payload) for block_id in block_ids}
