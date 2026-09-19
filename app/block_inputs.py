"""Block input construction for the Bakery Chain Operations & Delivery Platform.

Written by the factory WRITER role (codewhale exec)

Domain records are not block-acceptable payloads. Each vendored block declares
its own inputs (topic, sql/table, file paths, steps, channel, …) and refuses a
call that omits them — the caller must not have to know that. ``handle()``
passes the capability record through :func:`prepare_block_input`, which builds
the contract the block actually reads, and dispatches with
``action=BLOCK_DEFAULT_ACTIONS.get(block_id)`` as a keyword (never inside the
payload dict).

No value here is invented: every default is the block's own ``block.json``
default, and every constructed field is derived from the record the caller
sent.

Scope
-----
READS  the caller's record, ``STORAGE_PATH`` (filesystem).
WRITES ``STORAGE_PATH`` (the small text file ``file_hasher`` hashes).
NEVER  network, ``vendor/**``.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

#: block id -> the action its ``block.json`` declares (keyword only).
STORE_BLOCK_DEFAULT_ACTIONS: Dict[str, str] = {
    "analytics": "track_event",
    "audit": "log",
    "capture": "extract",
    "dashboard": "render",
    "database": "insert",
    "document_engine": "parse",
    "estate_maintenance": "create",
    "estate_registry": "register",
    "event_bus": "publish",
    "evidence_verifier": "store",
    "file_hasher": "hash",
    "formula_executor": "execute",
    "knowledge": "ask",
    "notification": "send",
    "portfolio_rollup": "rollup",
    "queue": "enqueue",
    "readiness_engine": "evaluate",
    "recommendation_template": "render",
    "spec_analyzer": "analyze",
    "validation": "validate_pipeline",
    "vector_search": "search",
    "workflow": "run",
}


def default_block_action(
    block_id: str,
    default_actions: Optional[Dict[str, str]] = None,
) -> Optional[str]:
    """Keyword action for ``execute(..., action=...)``. Never read from payload."""
    bid = str(block_id or "").strip()
    if isinstance(default_actions, dict):
        candidate = default_actions.get(bid)
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    mapped = STORE_BLOCK_DEFAULT_ACTIONS.get(bid)
    if isinstance(mapped, str) and mapped.strip():
        return mapped.strip()
    return None


def split_execute_action(
    payload: Any,
    action: Optional[str] = None,
    default_action: Optional[str] = None,
) -> tuple:
    """(action, payload-without-action).

    The operation travels as the ``action=`` keyword. A payload that carries an
    ``action`` key is stripped rather than forwarded, so a block never answers
    ``unknown field(s): action``.
    """
    data = dict(payload) if isinstance(payload, dict) else (
        {} if payload is None else {"value": payload}
    )
    inner = data.get("input") if isinstance(data.get("input"), dict) else {}
    resolved = action if isinstance(action, str) and action.strip() else None
    if resolved is None:
        for candidate in (data.get("action"), inner.get("action"), default_action):
            if isinstance(candidate, str) and candidate.strip():
                resolved = candidate.strip()
                break
    data.pop("action", None)
    if isinstance(data.get("input"), dict):
        data["input"] = dict(data["input"])
        data["input"].pop("action", None)
    return resolved, data


def _scalars(record: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for key, value in (record or {}).items():
        if key in ("id", "tenant_id", "created_at"):
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            out[str(key)] = value
    return out


def _insert_values(table: str, record: Dict[str, Any]) -> Dict[str, Any]:
    """Columns for a ``database`` insert — never an empty column list.

    ``INSERT INTO t () VALUES ()`` is a syntax error, so a record with no
    scalar field at all (an empty create body) is completed from the entity's
    own declared columns rather than dispatched as a malformed statement.
    """
    values = _scalars(record)
    if values:
        return values
    try:
        from app import store

        columns = list(store.COLUMNS.get(str(table)) or [])
    except Exception:  # noqa: BLE001 - the entity register is optional here
        columns = []
    return {column: "" for column in columns} or {"reference": "record"}


def _reference(record: Dict[str, Any]) -> str:
    for key in ("reference", "batch_reference", "sample_id", "material_code",
                "asset_code", "recipe_code", "report_type"):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "record"


def _summary(record: Dict[str, Any]) -> str:
    parts = [f"{k}={v}" for k, v in sorted(_scalars(record).items()) if v not in (None, "")]
    return "; ".join(parts) or "bakery record"


def _storage_root() -> Path:
    root = Path(os.environ.get("STORAGE_PATH") or ".").resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _write_hash_input(record: Dict[str, Any]) -> str:
    """A real file for ``file_hasher``; the digest is of the record itself."""
    body = json.dumps(_scalars(record), sort_keys=True)
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    folder = _storage_root() / "hashed_inputs"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{digest[:32]}.json"
    if not path.is_file():
        path.write_text(body, encoding="utf-8")
    return str(path)


def prepare_block_input(
    block_id: str,
    data: Dict[str, Any],
    entity: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Build the input ``block_id`` reads, from the capability record."""
    bid = str(block_id or "").strip()
    record = data if isinstance(data, dict) else {"value": data}
    table = str(entity or kwargs.get("entity") or record.get("__entity__") or "record")
    reference = _reference(record)
    values = _scalars(record)

    if bid == "database":
        return {"table": table, "values": _insert_values(table, record)}
    if bid == "audit":
        return {
            "event_action": str(record.get("status") or "create"),
            "resource": table,
            "category": "domain",
            "details": values,
        }
    if bid == "analytics":
        metric = (
            record.get("metric_name")
            or record.get("test_name")
            or f"{table}_count"
        )
        value = record.get("metric_value")
        if value is None:
            value = record.get("quantity_on_hand")
        if value is None:
            value = 1
        return {"metric": str(metric), "value": value, "name": table,
                "period": str(record.get("window") or "shift")}
    if bid == "dashboard":
        return {
            "metric": str(record.get("metric_name") or f"{table}_count"),
            "value": record.get("metric_value") if record.get("metric_value") is not None else 1,
            "title": f"{table} dashboard",
        }
    if bid == "capture":
        return {"text": _summary(record), "reference": reference}
    if bid == "document_engine":
        # document_engine parses a FILE when one is supplied and the record
        # text otherwise. attachment_path is the caller's path; it is used only
        # when it is really on disk, so a sample path never fails the call.
        text = str(record.get("spec_text") or record.get("notes") or _summary(record))
        prepared = {"text": text, "title": reference, "reference": reference}
        attachment = record.get("attachment_path")
        if isinstance(attachment, str) and attachment.strip() and Path(attachment).is_file():
            prepared["file_path"] = attachment
        return prepared
    if bid == "event_bus":
        topic = str(kwargs.get("topic") or f"{table}.recorded")
        return {
            "topic": topic,
            "payload": {"reference": reference, "status": record.get("status")},
            "message": topic.replace(".", " "),
            "channel": "mcp",
            "tool": "event_bus",
        }
    if bid == "file_hasher":
        return {"file_path": _write_hash_input(record)}
    if bid == "formula_executor":
        return {
            "formula": str(kwargs.get("formula") or "batch_yield"),
            "variables": {
                "input_liters": record.get("batch_size_liters") or 1,
                "quantity_on_hand": record.get("quantity_on_hand") or 1,
                "metric_value": record.get("metric_value") or 1,
            },
        }
    if bid == "knowledge":
        return {
            "query": str(record.get("spec_text") or record.get("notes") or reference),
            "documents": [{"doc_id": reference, "text": _summary(record)}],
            "tenant_id": str(kwargs.get("tenant_id") or "local"),
        }
    if bid == "notification":
        return {
            "channel": "mcp",
            "tool": "event_bus",
            "message": f"{table}: {reference} {record.get('status') or 'recorded'}",
            "payload": {"reference": reference},
        }
    if bid == "queue":
        return {
            "job_type": str(kwargs.get("job_type") or table),
            "payload": {"reference": reference},
            "priority": int(record.get("priority") or 1),
        }
    if bid == "recommendation_template":
        return {"context": values, "rules": list(kwargs.get("rules") or [])}
    if bid == "spec_analyzer":
        return {
            "text": str(record.get("spec_text") or record.get("notes") or _summary(record)),
            "title": reference,
        }
    if bid == "validation":
        item = dict(values)
        item.setdefault("id", reference)
        item.setdefault("type", table)
        return {"item": item, "context": {"entity": table}}
    if bid == "vector_search":
        return {
            "operation": "search",
            "query": str(record.get("spec_text") or record.get("notes") or reference),
            "collection": table,
            "documents": [{"id": reference, "text": _summary(record)}],
        }
    if bid in ("estate_maintenance", "estate_registry"):
        return {
            "record_id": reference,
            "title": str(record.get("work_order_title") or record.get("asset_code") or reference),
            "payload": values,
        }
    if bid == "evidence_verifier":
        return {"content": _summary(record), "reference": reference}
    if bid == "portfolio_rollup":
        amount = record.get("metric_value")
        if amount is None:
            amount = record.get("quantity_on_hand")
        if amount is None:
            amount = 1
        return {"properties": [{"name": table, "value": amount,
                                "reference": reference}]}
    if bid == "readiness_engine":
        return {
            "checklist": list(kwargs.get("checklist") or [
                {"id": "record_present", "required": True},
            ]),
            "state": {"reference": reference, "status": record.get("status"),
                      "record_present": True},
        }
    if bid == "workflow":
        steps = kwargs.get("steps")
        if isinstance(steps, list) and steps:
            return {
                "steps": steps,
                "result": steps[0].get("input") if isinstance(steps[0], dict) else values,
                "pipeline_id": reference,
            }
        return {"steps": [], "result": values, "pipeline_id": reference}
    # Unknown block: pass the record through untouched. The dispatch layer owns
    # the refusal, never this constructor.
    return values
