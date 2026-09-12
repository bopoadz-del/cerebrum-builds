"""Construct block inputs from a domain record. Never demand block-specific keys."""

from __future__ import annotations

from typing import Any, Dict

from app.dispatch import storage_tempfile

_MINIMAL_PDF = (
    b"%PDF-1.1\n1 0 obj<<>>endobj\n2 0 obj<< /Length 68 >>stream\n"
    b"BT /F1 12 Tf 72 720 Td (Cerebrum Steward House Manual) Tj ET\n"
    b"endstream\nendobj\ntrailer<<>>\n%%EOF\n"
)


def _ref(payload: Dict[str, Any]) -> str:
    return str(payload.get("reference") or "sample")


def _summary(payload: Dict[str, Any]) -> str:
    return f"estate record {_ref(payload)} status={payload.get('status', 'open')}"


def prepared_event_bus_step(payload: Dict[str, Any], topic: str, index: int) -> Dict[str, Any]:
    reference = _ref(payload)
    return {
        "id": f"step_{index}",
        "block": "event_bus",
        "action": "publish",
        "input": {
            "topic": topic,
            "payload": {"reference": reference},
            "message": _summary(payload),
            "channel": "mcp",
            "tool": "event_bus",
            "result": {"reference": reference},
        },
        "params": {"action": "publish"},
    }


def database_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"sql": "SELECT 1 AS ok", "table": "estate_registry"}


def storage_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    body = _summary(payload)
    return {
        "filename": f"{_ref(payload)}.txt",
        "content": body,
        "metadata": {"reference": _ref(payload)},
    }


def validation_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "item": {"id": _ref(payload), "type": "estate_record"},
        "context": {},
    }


def document_engine_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    path = storage_tempfile(f"{_ref(payload)}.pdf", _MINIMAL_PDF)
    return {"pdf_path": path, "file_path": path, "text": _summary(payload)}


def knowledge_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"question": _summary(payload), "query": _summary(payload)}


def vector_search_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"query": _summary(payload), "text": _summary(payload)}


def formula_executor_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "formula_key": "concrete_cost",
        "input_values": {"volume_m3": 1.0, "rate_per_m3": 1.0, "waste_factor": 1.0},
    }


def audit_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "category": "estate",
        "user_id": "operator",
        "event_action": "persist",
        "resource": _ref(payload),
        "details": {"status": payload.get("status", "open")},
    }


def notification_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "channel": "mcp",
        "tool": "event_bus",
        "block": "event_bus",
        "message": _summary(payload),
        "payload": {
            "topic": f"notify.{_ref(payload)}",
            "payload": {"reference": _ref(payload)},
            "message": _summary(payload),
            "channel": "mcp",
            "tool": "event_bus",
        },
        "params": {"action": "publish"},
    }


def queue_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "job_type": "estate_task",
        "queue": "estate",
        "payload": {"reference": _ref(payload)},
    }


def team_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "user_id": "operator",
        "name": f"estate-{_ref(payload)}",
        "slug": f"estate-{_ref(payload)}".replace(" ", "-"),
        "plan": "free",
    }


def dashboard_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"title": "Principal dashboard", "reference": _ref(payload)}


def analytics_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"metric": "estate_ops", "value": 1, "tags": {"reference": _ref(payload)}}


def spec_analyzer_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "text": (
            "SECTION 03 - CONCRETE. Concrete shall be grade C30. "
            "Reinforcing steel shall conform to ASTM A615. "
            f"Record {_ref(payload)}."
        )
    }


def recommendation_template_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "variance_data": [
            {
                "item": _ref(payload),
                "variance_pct": 1.0,
                "cost_impact_usd": 1,
            }
        ]
    }


def capture_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"text": _summary(payload), "raw_text": _summary(payload)}


def event_bus_input(payload: Dict[str, Any], topic: str) -> Dict[str, Any]:
    return {
        "topic": topic,
        "payload": {"reference": _ref(payload)},
        "message": _summary(payload),
        "channel": "mcp",
        "tool": "event_bus",
    }


def workflow_event_bus_input(payload: Dict[str, Any], topics: list[str]) -> Dict[str, Any]:
    steps = [prepared_event_bus_step(payload, topic, idx) for idx, topic in enumerate(topics)]
    first = steps[0]["input"] if steps else {}
    return {
        "pipeline_id": f"pipe-{_ref(payload)}",
        "result": first.get("payload") or {"reference": _ref(payload)},
        "steps": steps,
    }
