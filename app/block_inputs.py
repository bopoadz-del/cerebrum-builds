"""Construct block inputs from a domain record. Never demand block-specific keys."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List


def _ref(payload: Dict[str, Any]) -> str:
    return str(payload.get("reference") or "sample")


def _summary(payload: Dict[str, Any]) -> str:
    carrier = payload.get("carrier_code") or "RX"
    hub = payload.get("hub_city") or payload.get("station") or "Riyadh"
    return (
        f"airops record {_ref(payload)} carrier={carrier} hub={hub} "
        f"status={payload.get('status', 'open')}"
    )


def _artifact_dir() -> Path:
    from app.store import storage_root

    path = storage_root() / "artifacts"
    path.mkdir(parents=True, exist_ok=True)
    return path


def working_text_file(payload: Dict[str, Any], *, suffix: str = ".txt", body: str = "") -> str:
    """Write a local artifact from the domain record. Callers never supply paths."""
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in _ref(payload))
    path = _artifact_dir() / f"{safe}{suffix}"
    text = body or _summary(payload)
    path.write_text(text, encoding="utf-8")
    return str(path)


def working_pdf_file(payload: Dict[str, Any], body: str = "") -> str:
    """Minimal PDF so document_engine parse has a real local file."""
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in _ref(payload))
    path = _artifact_dir() / f"{safe}.pdf"
    note = (body or _summary(payload)).replace("(", " ").replace(")", " ")
    pdf = (
        "%PDF-1.1\n"
        "1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n"
        "2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n"
        "3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] "
        f"/Contents 4 0 R >>endobj\n"
        f"4 0 obj<< /Length {20 + len(note)} >>stream\n"
        f"BT /F1 12 Tf 10 100 Td ({note[:80]}) Tj ET\n"
        "endstream\nendobj\n"
        "trailer<< /Root 1 0 R >>\n%%EOF\n"
    )
    path.write_bytes(pdf.encode("latin-1", errors="replace"))
    return str(path)


def prepared_event_bus_step(payload: Dict[str, Any], topic: str, message: str) -> Dict[str, Any]:
    """Factory-grounded event_bus child. Never forward the raw schema sample."""
    return {
        "block": "event_bus",
        "action": "publish",
        "params": {"action": "publish"},
        "input": {
            "topic": topic,
            "payload": {"reference": _ref(payload)},
            "message": message,
            "channel": "mcp",
            "tool": "event_bus",
        },
    }


def workflow_input(payload: Dict[str, Any], steps: List[Dict[str, Any]], pipeline_id: str) -> Dict[str, Any]:
    """Attach result from the first prepared step so Store workflow can persist."""
    first = steps[0]["input"] if steps else {"reference": _ref(payload)}
    return {
        "pipeline_id": pipeline_id,
        "result": first if isinstance(first, dict) else {"reference": _ref(payload)},
        "steps": steps,
    }


def audit_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    actor = str(payload.get("actor") or payload.get("user_id") or "unattributed")
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
        "user_id": str(payload.get("actor") or payload.get("user_id") or "operator"),
        "title": f"AirOps portfolio {_ref(payload)}",
        "theme": "light",
        "layout": "grid",
        "summary": _summary(payload),
    }


def gdpr_audit_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    actor = str(payload.get("actor") or payload.get("user_id") or "unattributed")
    return {
        "category": "data_access",
        "user_id": actor,
        "event_action": payload.get("event_action") or "gdpr_privacy_review",
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
            "capability": "gdpr_privacy_audit",
        },
    }


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


def file_hasher_input(payload: Dict[str, Any], body: str = "") -> Dict[str, Any]:
    return {"file_path": working_text_file(payload, suffix=".txt", body=body)}


def database_input(payload: Dict[str, Any], table: str) -> Dict[str, Any]:
    return {"table": table, "filters": {"reference": _ref(payload)}}


def validation_input(payload: Dict[str, Any], item_type: str) -> Dict[str, Any]:
    return {
        "item": {
            "id": _ref(payload),
            "type": item_type,
            "reference": _ref(payload),
            "status": payload.get("status", "open"),
        },
        "context": {"channel": "mcp", "summary": _summary(payload)},
    }


def team_input(payload: Dict[str, Any], team_name: str) -> Dict[str, Any]:
    actor = str(payload.get("actor") or payload.get("user_id") or "operator")
    return {
        "user_id": actor,
        "name": team_name,
        "slug": f"airops-{_ref(payload)}".lower(),
    }


def notification_input(payload: Dict[str, Any], message: str) -> Dict[str, Any]:
    return {
        "channel": "mcp",
        "message": message,
        "tool": "memory",
        "block": "memory",
        "payload": {"action": "set", "key": f"notify:{_ref(payload)}", "value": message},
        "params": {"action": "set"},
    }


def document_engine_input(payload: Dict[str, Any], body: str = "") -> Dict[str, Any]:
    return {"file_path": working_pdf_file(payload, body=body), "pdf_path": working_pdf_file(payload, body=body)}


def storage_input(payload: Dict[str, Any], filename: str, content: str) -> Dict[str, Any]:
    return {
        "filename": filename,
        "content": content,
        "metadata": {"reference": _ref(payload), "status": payload.get("status", "open")},
    }


def analytics_input(payload: Dict[str, Any], metric: str, value: float) -> Dict[str, Any]:
    return {
        "metric": metric,
        "value": value,
        "tags": {"reference": _ref(payload), "status": str(payload.get("status", "open"))},
    }


def knowledge_input(payload: Dict[str, Any], question: str) -> Dict[str, Any]:
    return {"question": question, "query": question}


def vector_search_input(payload: Dict[str, Any], query: str) -> Dict[str, Any]:
    return {"query": query, "text": query, "collection": "aviation_safety"}


def memory_input(payload: Dict[str, Any], key: str, value: Any) -> Dict[str, Any]:
    return {"key": key, "value": value, "ttl": 3600}
