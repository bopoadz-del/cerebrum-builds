"""Construct block inputs from a domain record. Never demand block-specific keys."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from app.store import storage_root


def _ref(payload: Dict[str, Any]) -> str:
    return str(payload.get("reference") or "sample")


def _summary(payload: Dict[str, Any]) -> str:
    carrier = payload.get("carrier_code") or "RX"
    hub = payload.get("hub_city") or payload.get("station") or "Riyadh"
    return (
        f"airops record {_ref(payload)} carrier={carrier} hub={hub} "
        f"status={payload.get('status', 'open')}"
    )


def _actor(payload: Dict[str, Any]) -> str:
    return str(payload.get("actor") or payload.get("user_id") or "operator")


def audit_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    actor = _actor(payload)
    return {
        "category": payload.get("category") or "admin",
        "user_id": actor,
        "event_action": payload.get("event_action") or "persist",
        "resource": _ref(payload),
        "details": {
            "status": payload.get("status", "open"),
            "summary": _summary(payload),
            "carrier_code": payload.get("carrier_code") or "RX",
            "actor": actor,
            "actor_role": payload.get("actor_role"),
            "capability": payload.get("capability"),
        },
    }


def dashboard_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "user_id": _actor(payload),
        "title": f"AirOps portfolio {_ref(payload)}",
        "theme": "light",
        "layout": "grid",
        "summary": _summary(payload),
    }


def gdpr_audit_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    actor = _actor(payload)
    return {
        "category": "data_access",
        "user_id": actor,
        "event_action": payload.get("event_action") or "privacy_evidence",
        "resource": _ref(payload),
        "details": {
            "status": payload.get("status", "open"),
            "lawful_basis": payload.get("lawful_basis") or "legitimate_interest",
            "data_subject": payload.get("data_subject") or "sample",
            "fail_closed_auth": True,
            "principal_audit": True,
            "cors": True,
            "actor": actor,
            "actor_role": payload.get("actor_role"),
            "capability": "privacy_compliance_evidence",
        },
    }


def team_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "user_id": _actor(payload),
        "name": f"RX {_ref(payload)}",
        "plan": "free",
    }


def queue_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "job_type": "airops.persist",
        "payload": {"reference": _ref(payload)},
        "queue": "airops",
        "priority": 0,
    }


def validation_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "item": {
            "id": _ref(payload),
            "type": "airops_record",
            "status": payload.get("status", "open"),
        },
        "context": {"surface": "airline_delivery_management"},
    }


def event_bus_input(payload: Dict[str, Any], topic: str | None = None) -> Dict[str, Any]:
    return {
        "topic": topic or f"airops.{_ref(payload)}",
        "payload": {"reference": _ref(payload)},
        "message": _summary(payload),
        "channel": "mcp",
        "tool": "event_bus",
    }


def formula_executor_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "formula_key": "earned_value",
        "input_values": {
            "bac": 12_500_000.0,
            "pv": 5_000_000.0,
            "ev": 4_500_000.0,
            "ac": 4_800_000.0,
        },
        "formula_description": _summary(payload),
    }


def analytics_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "metric": "airops.record",
        "value": 1,
        "tags": {"reference": _ref(payload), "status": str(payload.get("status") or "open")},
    }


def recommendation_template_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "operation": "recommend",
        "variance_data": [
            {
                "item": _ref(payload),
                "variance_pct": 5.0,
                "cost_impact_usd": 1000,
            }
        ],
    }


def knowledge_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"question": _summary(payload), "query": _summary(payload)}


def vector_search_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"query": _summary(payload), "text": _summary(payload)}


def memory_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"key": f"airops:{_ref(payload)}"}


def storage_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "content": _summary(payload),
        "filename": f"{_ref(payload)}.json",
        "metadata": {"reference": _ref(payload)},
    }


def database_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"sql": "SELECT 1 AS ok", "table": "sqlite_master"}


def notification_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "channel": "mcp",
        "message": _summary(payload),
        "tool": "event_bus",
        "block": "event_bus",
        "payload": {"reference": _ref(payload), "topic": "airops.notify"},
        "params": {"action": "publish", "topic": "airops.notify"},
    }


def _evidence_dir():
    path = storage_root() / "evidence"
    path.mkdir(parents=True, exist_ok=True)
    return path


def file_hasher_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    path = _evidence_dir() / f"{_ref(payload)}.txt"
    path.write_text(_summary(payload), encoding="utf-8")
    return {"file_path": str(path)}


def document_engine_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    path = _evidence_dir() / f"{_ref(payload)}.pdf"
    path.write_bytes(b"%PDF-1.1\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n")
    return {"pdf_path": str(path), "text": _summary(payload)}


def capture_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"raw_text": _summary(payload), "text": _summary(payload)}


def event_bus_step(payload: Dict[str, Any], topic: str, message: str) -> Dict[str, Any]:
    body = event_bus_input(payload, topic=topic)
    body["message"] = message
    return {
        "block": "event_bus",
        "action": "publish",
        "params": {"action": "publish"},
        "input": body,
    }


def workflow_with_event_bus(
    payload: Dict[str, Any], topics: List[Tuple[str, str]]
) -> Dict[str, Any]:
    steps = [event_bus_step(payload, topic, message) for topic, message in topics]
    first_payload = steps[0]["input"]["payload"]
    steps[0]["input"]["result"] = first_payload
    return {
        "result": first_payload,
        "pipeline_id": f"wf-{_ref(payload)}",
        "steps": steps,
    }


def workflow_with_dashboard(payload: Dict[str, Any]) -> Dict[str, Any]:
    dash = dashboard_input(payload)
    result = {"reference": _ref(payload)}
    dash["result"] = result
    return {
        "result": result,
        "pipeline_id": f"wf-{_ref(payload)}",
        "steps": [
            {
                "block": "dashboard",
                "action": "render",
                "params": {"action": "render"},
                "input": dash,
            }
        ],
    }


def prepare_block_input(block_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    builders = {
        "audit": audit_input,
        "dashboard": dashboard_input,
        "team": team_input,
        "queue": queue_input,
        "validation": validation_input,
        "event_bus": event_bus_input,
        "formula_executor": formula_executor_input,
        "analytics": analytics_input,
        "recommendation_template": recommendation_template_input,
        "knowledge": knowledge_input,
        "vector_search": vector_search_input,
        "memory": memory_input,
        "storage": storage_input,
        "database": database_input,
        "notification": notification_input,
        "file_hasher": file_hasher_input,
        "document_engine": document_engine_input,
        "capture": capture_input,
        "workflow": workflow_with_dashboard,
    }
    builder = builders.get(block_id)
    if builder is None:
        return {"reference": _ref(payload), "summary": _summary(payload)}
    return builder(payload)


def record_mutation_audit(
    principal: Any,
    *,
    action: str,
    resource: str,
    details: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Persist a Principal-attributed audit event for a mutation."""
    from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
    from app.persist import persist_record

    extra = dict(details or {})
    payload = {
        "reference": resource,
        "status": extra.pop("status", "open"),
        "actor": principal.subject,
        "actor_role": principal.role,
        "event_action": action,
        "category": extra.pop("category", "admin"),
        **extra,
    }
    execute("audit", audit_input(payload), action=BLOCK_DEFAULT_ACTIONS.get("audit"))
    persist_record("audit", payload)
    return payload
