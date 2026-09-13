"""Construct block inputs from a domain record. Never demand block-specific keys."""

from __future__ import annotations

from typing import Any, Dict, List


def _ref(payload: Dict[str, Any]) -> str:
    return str(payload.get("reference") or "sample")


def _status(payload: Dict[str, Any]) -> str:
    return str(payload.get("status") or "open")


def _tail(payload: Dict[str, Any]) -> str:
    return str(
        payload.get("tail_number")
        or payload.get("registration")
        or _ref(payload)
    )


def _summary(payload: Dict[str, Any]) -> str:
    return (
        f"aviation ops {_ref(payload)} tail={_tail(payload)} "
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
        "notification": notification_input,
        "dashboard": dashboard_input,
        "analytics": analytics_input,
        "event_bus": event_bus_input,
        "knowledge": knowledge_input,
        "memory": memory_input,
        "storage": storage_input,
        "file_hasher": file_hasher_input,
        "team": team_input,
        "document_engine": document_engine_input,
        "vector_search": vector_search_input,
    }
    builder = builders.get(block_id)
    if builder is None:
        return {"result": _result_seed(payload), "reference": _ref(payload)}
    return builder(payload)


def database_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    table = str(payload.get("capability") or "fleet_registry_management")
    return {
        "table": table,
        "filters": {"reference": _ref(payload)},
        "result": _result_seed(payload),
    }


def validation_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    item = {
        "id": _ref(payload),
        "type": str(payload.get("aircraft_type") or "narrowbody"),
        "quantity": 1,
        "status": _status(payload),
        "registration": _tail(payload),
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
            "tail_number": _tail(payload),
            "actor": actor,
            "actor_role": payload.get("actor_role"),
            "capability": payload.get("capability"),
        },
        "result": _result_seed(payload),
    }


def notification_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    message = payload.get("message") or f"Aviation ops notice for {_ref(payload)} ({_tail(payload)})"
    return {
        "channel": "mcp",
        "message": str(message),
        "tool": "event_bus",
        "block": "event_bus",
        "payload": {
            "reference": _ref(payload),
            "tail_number": _tail(payload),
            "status": _status(payload),
        },
        "params": {"action": "publish", "topic": f"aviation.{_ref(payload)}"},
        "result": _result_seed(payload),
    }


def event_bus_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    topic = str(
        payload.get("event")
        or payload.get("event_type")
        or payload.get("event_name")
        or payload.get("work_order_kind")
        or payload.get("currency_item")
        or f"aviation.{_ref(payload)}"
    )
    return {
        "topic": topic,
        "payload": {
            "reference": _ref(payload),
            "tail_number": _tail(payload),
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
    capability = str(payload.get("capability") or "")
    if capability == "crew_training_readiness":
        steps = [
            {
                "id": "step_0",
                "block": "team",
                "action": "create_team",
                "params": {"action": "create_team"},
                "input": team_input(payload),
            },
            {
                "id": "step_1",
                "block": "notification",
                "action": "send",
                "params": {"action": "send"},
                "input": notification_input(payload),
            },
        ]
        pipeline_id = f"crew-{_ref(payload)}"
    else:
        steps = [
            {
                "id": "step_0",
                "block": "audit",
                "action": "log",
                "params": {"action": "log"},
                "input": audit_input(payload),
            },
            prepared_event_bus_step(payload, step_id="step_1"),
        ]
        pipeline_id = f"mx-{_ref(payload)}"
    return {
        "pipeline_id": pipeline_id,
        "result": seed,
        "steps": steps,
    }


def dashboard_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "user_id": str(payload.get("actor") or payload.get("user_id") or "operator"),
        "title": f"Aviation ops {_ref(payload)}",
        "theme": "light",
        "layout": "grid",
        "summary": _summary(payload),
        "result": _result_seed(payload),
    }


def analytics_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    horizon = str(payload.get("horizon") or "today")
    value = {"today": 1.0, "week": 7.0, "month": 30.0}.get(horizon, 1.0)
    return {
        "metric": "aviation_ops_events",
        "value": value,
        "tags": {
            "reference": _ref(payload),
            "horizon": horizon,
            "status": _status(payload),
        },
        "result": _result_seed(payload),
    }


def knowledge_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    question = (
        payload.get("question")
        or payload.get("corpus_layer")
        or _summary(payload)
    )
    return {
        "question": str(question),
        "query": str(question),
        "result": _result_seed(payload),
    }


def memory_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "key": f"safety:{_ref(payload)}",
        "value": {
            "reference": _ref(payload),
            "question": payload.get("question") or "sample",
            "status": _status(payload),
        },
        "result": _result_seed(payload),
    }


def storage_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    body = (
        payload.get("revision")
        or payload.get("document_kind")
        or _summary(payload)
    )
    return {
        "filename": f"{_ref(payload)}.md",
        "content": str(body),
        "metadata": {
            "reference": _ref(payload),
            "document_kind": payload.get("document_kind") or "release",
            "status": _status(payload),
        },
        "result": _result_seed(payload),
    }


def file_hasher_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    content = {
        "reference": _ref(payload),
        "status": _status(payload),
        "regulation": payload.get("regulation"),
        "document_kind": payload.get("document_kind"),
        "revision": payload.get("revision"),
        "summary": _summary(payload),
    }
    return {
        "content": content,
        "filename": f"{_ref(payload)}.evidence",
        "result": _result_seed(payload),
    }


def team_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    role = str(payload.get("crew_role") or "captain")
    return {
        "name": f"crew-{_ref(payload)}",
        "members": [role, "operator"],
        "result": _result_seed(payload),
        "reference": _ref(payload),
    }


def document_engine_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    kind = str(payload.get("document_kind") or "release")
    revision = str(payload.get("revision") or "sample")
    return {
        "filename": f"{kind}-{_ref(payload)}.txt",
        "content": f"{kind} revision {revision} for {_tail(payload)}\n{_summary(payload)}",
        "result": _result_seed(payload),
    }


def vector_search_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    query = (
        payload.get("question")
        or payload.get("corpus_layer")
        or _summary(payload)
    )
    return {
        "query": str(query),
        "question": str(query),
        "n_results": 5,
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
