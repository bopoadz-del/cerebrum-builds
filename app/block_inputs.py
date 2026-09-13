"""Construct block inputs from a domain record. Never demand block-specific keys."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

# Minimal PDF so document_engine parse has a real file without caller paths.
_MINIMAL_PDF = (
    b"%PDF-1.1\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj\n"
    b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n"
    b"0000000058 00000 n \n0000000115 00000 n \n"
    b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF\n"
)


def _ref(payload: Dict[str, Any]) -> str:
    return str(payload.get("reference") or "sample")


def _status(payload: Dict[str, Any]) -> str:
    return str(payload.get("status") or "open")


def _summary(payload: Dict[str, Any]) -> str:
    stand = payload.get("stand_id") or payload.get("flight_reference") or _ref(payload)
    return (
        f"airport ops {_ref(payload)} stand={stand} "
        f"status={_status(payload)}"
    )


def _result_seed(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Store workflow / kit shims read input['result']. Schema sample omits it."""
    return {
        "reference": _ref(payload),
        "status": _status(payload),
        "summary": _summary(payload),
    }


def _scratch_dir() -> Path:
    from app.store import storage_root

    path = storage_root() / "scratch"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_scratch(name: str, content: bytes | str) -> str:
    path = _scratch_dir() / name
    if isinstance(content, str):
        path.write_text(content, encoding="utf-8")
    else:
        path.write_bytes(content)
    return str(path)


def prepare_block_input(block_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Factory-grounded constructed input for a declared Store block."""
    builders = {
        "analytics": analytics_input,
        "audit": audit_input,
        "capture": capture_input,
        "dashboard": dashboard_input,
        "document_engine": document_engine_input,
        "event_bus": event_bus_input,
        "file_hasher": file_hasher_input,
        "knowledge": knowledge_input,
        "memory": memory_input,
        "notification": notification_input,
        "queue": queue_input,
        "recommendation_template": recommendation_template_input,
        "storage": storage_input,
        "team": team_input,
        "validation": validation_input,
        "vector_search": vector_search_input,
        "workflow": workflow_input,
    }
    builder = builders.get(block_id)
    if builder is None:
        return {"result": _result_seed(payload), "reference": _ref(payload)}
    return builder(payload)


def analytics_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "metric": "airport_ops_events",
        "value": 1.0,
        "tags": {
            "reference": _ref(payload),
            "stand_id": str(payload.get("stand_id") or _ref(payload)),
            "horizon": str(payload.get("horizon") or payload.get("readiness_window") or "today"),
            "status": _status(payload),
        },
        "result": _result_seed(payload),
    }


def audit_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    actor = str(payload.get("actor") or payload.get("user_id") or "unattributed")
    return {
        "category": payload.get("category") or "airside",
        "user_id": actor,
        "event_action": payload.get("event_action") or "persist",
        "resource": _ref(payload),
        "details": {
            "status": _status(payload),
            "summary": _summary(payload),
            "actor": actor,
            "actor_role": payload.get("actor_role"),
            "capability": payload.get("capability"),
        },
        "result": _result_seed(payload),
    }


def capture_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    note = str(payload.get("incident_note") or _summary(payload))
    return {
        "raw_text": note,
        "text": note,
        "content": note,
        "result": _result_seed(payload),
        "reference": _ref(payload),
    }


def dashboard_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "user_id": str(payload.get("actor") or payload.get("user_id") or "operator"),
        "title": f"Airport ops {_ref(payload)}",
        "theme": "light",
        "layout": "grid",
        "summary": _summary(payload),
        "result": _result_seed(payload),
    }


def document_engine_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    title = str(payload.get("document_title") or _ref(payload))
    path = _write_scratch(f"{_ref(payload)}.pdf", _MINIMAL_PDF)
    return {
        "pdf": _MINIMAL_PDF,
        "pdf_path": path,
        "file_path": path,
        "title": title,
        "result": _result_seed(payload),
    }


def event_bus_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    topic = str(
        payload.get("event")
        or payload.get("event_type")
        or payload.get("event_name")
        or payload.get("reminder_type")
        or f"airport.{_ref(payload)}"
    )
    return {
        "topic": topic,
        "payload": {
            "reference": _ref(payload),
            "flight_reference": payload.get("flight_reference") or _ref(payload),
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


def file_hasher_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    body = str(payload.get("incident_note") or _summary(payload))
    path = _write_scratch(f"{_ref(payload)}.evidence.txt", body)
    return {
        "file_path": path,
        "result": _result_seed(payload),
        "reference": _ref(payload),
    }


def knowledge_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    question = (
        payload.get("question")
        or payload.get("note_body")
        or _summary(payload)
    )
    return {
        "question": str(question),
        "query": str(question),
        "result": _result_seed(payload),
    }


def memory_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "key": f"airport_ops:{_ref(payload)}",
        "value": {
            "reference": _ref(payload),
            "question": payload.get("question") or "sample",
            "status": _status(payload),
        },
        "result": _result_seed(payload),
    }


def notification_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    message = payload.get("message") or f"Airport ops notice for {_ref(payload)}"
    topic = str(
        payload.get("event_type")
        or payload.get("event")
        or f"airport.{_ref(payload)}"
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
        "job_type": "ground_task",
        "queue": "airside",
        "payload": {
            "reference": _ref(payload),
            "work_order": payload.get("work_order") or _ref(payload),
            "crew_name": payload.get("crew_name") or "sample",
            "status": _status(payload),
        },
        "result": _result_seed(payload),
    }


def recommendation_template_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "operation": "recommend",
        "variance_data": [
            {
                "name": _ref(payload),
                "variance_pct": 0,
                "risk_level": "info",
                "delay_days": 0,
            }
        ],
        "result": _result_seed(payload),
    }


def storage_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    body = (
        payload.get("note_body")
        or payload.get("incident_note")
        or payload.get("document_title")
        or _summary(payload)
    )
    return {
        "filename": f"{_ref(payload)}.md",
        "content": str(body),
        "metadata": {
            "reference": _ref(payload),
            "status": _status(payload),
        },
        "result": _result_seed(payload),
    }


def team_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    actor = str(payload.get("actor") or payload.get("user_id") or "operator")
    name = str(payload.get("crew_name") or f"airside-{_ref(payload)}")
    return {
        "user_id": actor,
        "name": name,
        "slug": f"airside-{_ref(payload)}".replace(" ", "-").lower(),
        "result": _result_seed(payload),
    }


def validation_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    item = {
        "id": _ref(payload),
        "type": "airport_document",
        "status": _status(payload),
        "document_title": payload.get("document_title") or _ref(payload),
    }
    return {
        "item": item,
        "context": {"channel": "mcp", "summary": _summary(payload)},
        "result": _result_seed(payload),
    }


def vector_search_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    query = str(payload.get("question") or payload.get("note_body") or _summary(payload))
    return {
        "query": query,
        "text": query,
        "result": _result_seed(payload),
    }


def workflow_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Default ground-workflow pipeline. Flight orchestration overrides in-handler."""
    seed = _result_seed(payload)
    queue_step = {
        "id": "step_0",
        "block": "queue",
        "action": "enqueue",
        "params": {"action": "enqueue"},
        "input": queue_input(payload),
    }
    team_step = {
        "id": "step_1",
        "block": "team",
        "action": "create_team",
        "params": {"action": "create_team"},
        "input": team_input(payload),
    }
    return {
        "pipeline_id": f"ground-{_ref(payload)}",
        "result": seed,
        "steps": [queue_step, team_step],
    }


def flight_workflow_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Prepared event_bus children for step_0, step_1, and step_2+."""
    seed = _result_seed(payload)
    steps = [
        prepared_event_bus_step(payload, step_id="step_0"),
        prepared_event_bus_step(payload, step_id="step_1"),
        prepared_event_bus_step(payload, step_id="step_2"),
    ]
    return {
        "pipeline_id": f"flight-{_ref(payload)}",
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
        "category": extra.pop("category", "airside"),
        **extra,
    }
    execute("audit", audit_input(payload), action=BLOCK_DEFAULT_ACTIONS.get("audit"))
    return payload


def prepared_inputs(block_ids: List[str], payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {block_id: prepare_block_input(block_id, payload) for block_id in block_ids}
