"""Construct block inputs from a domain record. Never demand block-specific keys."""

from __future__ import annotations

from typing import Any, Dict, List

from app.store import storage_root

# Minimal PDF so document_engine / file_hasher have a real local file.
_MINIMAL_PDF = (
    b"%PDF-1.1\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 144]/Contents 4 0 R>>endobj\n"
    b"4 0 obj<</Length 68>>stream\n"
    b"BT /F1 12 Tf 24 100 Td (LedgerFlow personal finance record) Tj ET\n"
    b"endstream\nendobj\n"
    b"trailer<</Root 1 0 R>>\n"
    b"%%EOF\n"
)


def _ref(payload: Dict[str, Any]) -> str:
    return str(payload.get("reference") or "sample")


def _status(payload: Dict[str, Any]) -> str:
    return str(payload.get("status") or "open")


def _summary(payload: Dict[str, Any]) -> str:
    return (
        f"ledgerflow {_ref(payload)} status={_status(payload)} "
        f"account={payload.get('account_name') or 'sample'} "
        f"category={payload.get('category') or 'income'}"
    )


def _amount(payload: Dict[str, Any]) -> float:
    raw = payload.get("amount")
    if raw in (None, "", "sample"):
        return 1.0
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 1.0


def evidence_file(payload: Dict[str, Any], suffix: str = ".pdf") -> str:
    root = storage_root() / "evidence"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{_ref(payload)}{suffix}"
    if suffix == ".pdf":
        path.write_bytes(_MINIMAL_PDF)
    else:
        path.write_text(_summary(payload), encoding="utf-8")
    return str(path)


def capture_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "text": _summary(payload),
        "raw_text": _summary(payload),
        "content": _summary(payload),
        "ocr_engine": "tesseract",
        "llm_provider": "none",
    }


def storage_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "filename": f"{_ref(payload)}.json",
        "content": _summary(payload),
        "metadata": {
            "reference": _ref(payload),
            "status": _status(payload),
            "capability": payload.get("capability") or "transaction_capture",
        },
    }


def validation_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    # Block item may carry `id`; that key is refused on capability payloads.
    return {
        "item": {
            "id": _ref(payload),
            "type": "transaction",
            "amount": _amount(payload),
            "currency": payload.get("currency") or "USD",
            "reference": _ref(payload),
        },
        "context": {"source": "ledgerflow", "status": _status(payload)},
    }


def dashboard_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "user_id": str(payload.get("actor") or payload.get("user_id") or "operator"),
        "title": f"LedgerFlow dashboard {_ref(payload)}",
        "theme": "light",
        "layout": "grid",
        "summary": _summary(payload),
        "period": payload.get("period") or "month",
        "currency": payload.get("currency") or "USD",
    }


def analytics_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "metric": "ledgerflow.spend",
        "value": _amount(payload),
        "tags": {
            "reference": _ref(payload),
            "period": payload.get("period") or "month",
            "currency": payload.get("currency") or "USD",
        },
    }


def formula_executor_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    spent = _amount(payload)
    return {
        "formula_key": "earned_value",
        "input_values": {
            "bac": 1000.0,
            "pv": 500.0,
            "ev": min(500.0, spent * 10.0),
            "ac": max(1.0, spent * 12.0),
        },
        "operation": "execute",
    }


def notification_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "channel": "mcp",
        "tool": "event_bus",
        "block": "event_bus",
        "message": f"budget alert for {_ref(payload)}",
        "payload": {
            "topic": "budget.alert",
            "payload": {"reference": _ref(payload)},
            "message": f"budget alert for {_ref(payload)}",
            "channel": "mcp",
            "tool": "event_bus",
        },
        "params": {"action": "publish"},
        "to": "ops@example.com",
        "subject": f"LedgerFlow {_ref(payload)}",
    }


def prepared_event_bus_step(
    payload: Dict[str, Any], topic: str, message: str | None = None
) -> Dict[str, Any]:
    body = {
        "topic": topic,
        "payload": {"reference": _ref(payload)},
        "message": message or f"{topic} {_ref(payload)}",
        "channel": "mcp",
        "tool": "event_bus",
    }
    return {
        "block": "event_bus",
        "action": "publish",
        "params": {"action": "publish"},
        "input": body,
    }


def prepare_block_input(payload: Dict[str, Any], first_step: Dict[str, Any]) -> Dict[str, Any]:
    """Attach `result` from the first prepared step so workflow kit shims accept."""
    prepared = dict(payload)
    prepared["result"] = first_step.get("input") or first_step
    return prepared


def workflow_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    step_0 = prepared_event_bus_step(payload, "budget.opened", "budget opened")
    step_1 = prepared_event_bus_step(payload, "budget.threshold", "threshold watch")
    step_2 = prepared_event_bus_step(payload, "budget.alert", "alert published")
    steps: List[Dict[str, Any]] = [
        {**step_0, "id": "step_0"},
        {**step_1, "id": "step_1"},
        {**step_2, "id": "step_2"},
    ]
    envelope = {
        "pipeline_id": f"budget-{_ref(payload)}",
        "steps": steps,
        "result": step_0["input"],
    }
    return prepare_block_input(envelope, step_0)


def document_engine_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    path = evidence_file(payload, ".pdf")
    return {
        "pdf_path": path,
        "file_path": path,
        "text": path,
        "report_type": payload.get("report_type") or "pnl",
    }


def recommendation_template_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    spent = _amount(payload)
    return {
        "operation": "recommend",
        "variance_data": [
            {
                "item": payload.get("report_type") or "expense_breakdown",
                "variance_pct": 12.5,
                "cost_impact_usd": spent,
                "reference": _ref(payload),
            }
        ],
    }


def audit_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    actor = str(payload.get("actor") or payload.get("user_id") or "unattributed")
    return {
        "category": payload.get("category") or "admin",
        "user_id": actor,
        "event_action": payload.get("event_action") or "persist",
        "resource": _ref(payload),
        "details": {
            "status": _status(payload),
            "summary": _summary(payload),
            "actor": actor,
            "actor_role": payload.get("actor_role"),
            "capability": payload.get("capability") or "audit_and_compliance",
            "evidence_label": payload.get("evidence_label") or "sample",
        },
    }


def file_hasher_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    path = evidence_file(payload, ".pdf")
    return {"file_path": path, "algorithms": ["sha256"]}


def event_bus_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    topic = (
        str(payload.get("event") or payload.get("event_type") or payload.get("event_name") or "")
        or f"sync.{payload.get('sync_mode') or 'push'}"
    )
    return {
        "topic": topic,
        "payload": {"reference": _ref(payload)},
        "message": f"sync {_ref(payload)}",
        "channel": "mcp",
        "tool": "event_bus",
    }


def queue_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "job_type": "ledgerflow_sync",
        "queue": "sync",
        "payload": {
            "reference": _ref(payload),
            "source_name": payload.get("source_name") or "sample",
            "sync_mode": payload.get("sync_mode") or "push",
        },
        "priority": 0,
    }


def database_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "table": "sync_ledger",
        "filters": {},
        "sql": "SELECT name FROM sqlite_master WHERE type='table'",
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
    persist_record("audit_and_compliance", payload)
    return payload
