"""Construct block inputs from a domain record. Never demand block-specific keys."""

from __future__ import annotations

from typing import Any, Dict, List


_MINIMAL_PDF = (
    b"%PDF-1.1\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n"
    b"trailer<</Size 4/Root 1 0 R>>\n"
    b"%%EOF\n"
)


def _ref(payload: Dict[str, Any]) -> str:
    return str(payload.get("reference") or "sample")


def _status(payload: Dict[str, Any]) -> str:
    return str(payload.get("status") or "open")


def _summary(payload: Dict[str, Any]) -> str:
    unit = (
        payload.get("property_name")
        or payload.get("room_label")
        or payload.get("destination")
        or payload.get("guest_name")
        or payload.get("view_name")
        or _ref(payload)
    )
    return f"hotel {_ref(payload)} unit={unit} status={_status(payload)}"


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
        "dashboard": dashboard_input,
        "database": database_input,
        "document_engine": document_engine_input,
        "event_bus": event_bus_input,
        "formula_executor": formula_executor_input,
        "notification": notification_input,
        "queue": queue_input,
        "recommendation_template": recommendation_template_input,
        "storage": storage_input,
        "vector_search": vector_search_input,
        "workflow": workflow_input,
    }
    builder = builders.get(block_id)
    if builder is None:
        return {"result": _result_seed(payload), "reference": _ref(payload)}
    return builder(payload)


def analytics_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    value = payload.get("night_rate")
    if value is None:
        value = payload.get("stay_total")
    if value is None:
        value = payload.get("revpar")
    if value is None:
        value = payload.get("review_score")
    if value is None:
        value = payload.get("match_score")
    try:
        metric_value = float(value)
    except (TypeError, ValueError):
        metric_value = 1.0
    return {
        "metric": "hotel_booking_events",
        "value": metric_value,
        "tags": {
            "reference": _ref(payload),
            "property_name": str(payload.get("property_name") or _ref(payload)),
            "horizon": str(payload.get("horizon") or payload.get("season") or "today"),
            "status": _status(payload),
        },
        "result": _result_seed(payload),
    }


def dashboard_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "user_id": str(payload.get("actor") or payload.get("user_id") or "operator"),
        "title": f"Hotel {_ref(payload)}",
        "theme": "light",
        "layout": "grid",
        "summary": _summary(payload),
        "result": _result_seed(payload),
    }


def database_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    table = str(payload.get("capability") or "booking_management")
    return {
        "sql": "SELECT 1 AS ok",
        "table": table,
        "params": (),
        "result": _result_seed(payload),
    }


def document_engine_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Synthesize a property factsheet. Do not demand file paths from the caller."""
    from app.store import storage_root

    folder = storage_root() / "docs"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{_ref(payload)}.pdf"
    if not path.is_file():
        path.write_bytes(_MINIMAL_PDF)
    return {
        "pdf_path": str(path),
        "file_path": str(path),
        "text": _summary(payload),
        "result": _result_seed(payload),
    }


def event_bus_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    topic = str(
        payload.get("event")
        or payload.get("event_type")
        or payload.get("event_name")
        or payload.get("stay_kind")
        or payload.get("notice_kind")
        or payload.get("reminder_type")
        or f"hotel.{_ref(payload)}"
    )
    return {
        "topic": topic,
        "payload": {
            "reference": _ref(payload),
            "room_label": payload.get("room_label") or payload.get("property_name") or _ref(payload),
            "status": _status(payload),
        },
        "message": _summary(payload),
        "channel": "mcp",
        "tool": "analytics",
        "result": _result_seed(payload),
    }


def prepared_event_bus_step(payload: Dict[str, Any], *, step_id: str = "step_0") -> Dict[str, Any]:
    """Exact PRODUCT event_bus-shaped workflow child. Never set input to the raw sample."""
    prepared = event_bus_input(payload)
    return {
        "id": step_id,
        "block": "notification",
        "action": "send",
        "params": {"action": "send"},
        "input": {
            **prepared,
            "channel": "mcp",
            "tool": "analytics",
            "block": "analytics",
            "message": prepared["message"],
            "params": {"action": "track_event"},
        },
    }


def formula_executor_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    rate = payload.get("night_rate")
    try:
        rate_value = float(rate)
    except (TypeError, ValueError):
        rate_value = 200.0
    nights = payload.get("stay_nights") or 1
    try:
        nights_value = float(nights)
    except (TypeError, ValueError):
        nights_value = 1.0
    return {
        "formula_key": "concrete_cost",
        "input_values": {
            "volume_m3": nights_value,
            "rate_per_m3": rate_value,
            "waste_factor": 1.0,
        },
        "result": _result_seed(payload),
    }


def notification_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    message = payload.get("message") or f"Hotel notice for {_ref(payload)}"
    topic = str(
        payload.get("stay_kind")
        or payload.get("notice_kind")
        or payload.get("event")
        or f"hotel.{_ref(payload)}"
    )
    return {
        "channel": "mcp",
        "message": str(message),
        "tool": "analytics",
        "block": "analytics",
        "topic": topic,
        "payload": {
            "metric": "hotel_notice",
            "value": 1.0,
            "reference": _ref(payload),
            "status": _status(payload),
        },
        "params": {"action": "track_event", "topic": topic},
        "result": _result_seed(payload),
    }


def queue_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "job_type": "hotel_task",
        "queue": "reservations",
        "payload": {
            "reference": _ref(payload),
            "stay_kind": payload.get("stay_kind") or payload.get("notice_kind") or "night",
            "room_label": payload.get("room_label") or _ref(payload),
            "status": _status(payload),
        },
        "result": _result_seed(payload),
    }


def recommendation_template_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    score = payload.get("match_score")
    try:
        variance = round((1.0 - float(score)) * 100.0, 2)
    except (TypeError, ValueError):
        variance = 18.0
    return {
        "operation": "recommend",
        "variance_data": [
            {
                "item": str(payload.get("destination") or _ref(payload)),
                "variance_pct": variance,
                "cost_impact_usd": 80.0,
            }
        ],
        "result": _result_seed(payload),
    }


def storage_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "content": _summary(payload),
        "filename": f"{_ref(payload)}.txt",
        "metadata": {"reference": _ref(payload), "status": _status(payload)},
        "result": _result_seed(payload),
    }


def vector_search_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    query = str(
        payload.get("destination")
        or payload.get("stay_intent")
        or payload.get("property_name")
        or _summary(payload)
    )
    return {
        "query": query,
        "text": query,
        "result": _result_seed(payload),
    }


def workflow_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Default hospitality pipeline with prepared children + result seed."""
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
        "pipeline_id": f"hotel-{_ref(payload)}",
        "result": seed,
        "steps": [queue_step, notify_step],
    }


def booking_workflow_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Prepared step_0 / step_1 / step_2+ for booking-style workflow."""
    seed = _result_seed(payload)
    steps = [
        prepared_event_bus_step(payload, step_id="step_0"),
        prepared_event_bus_step(payload, step_id="step_1"),
        prepared_event_bus_step(payload, step_id="step_2"),
    ]
    return {
        "pipeline_id": f"booking-{_ref(payload)}",
        "result": seed,
        "steps": steps,
    }


def notice_workflow_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Prepared step_0 / step_1 / step_2+ for reminder-style workflow."""
    seed = _result_seed(payload)
    steps = [
        prepared_event_bus_step(payload, step_id="step_0"),
        prepared_event_bus_step(payload, step_id="step_1"),
        prepared_event_bus_step(payload, step_id="step_2"),
    ]
    return {
        "pipeline_id": f"notice-{_ref(payload)}",
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
    """Attribute a mutation. Audit is not vendored in this kit — do not execute it."""
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
