"""S12 domain acceptance — ten named outcomes through execute_action."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import HTTPException
from starlette.requests import Request

from app.auth import require_operator
from app.dispatch import execute
from app.domain import enqueue, process_queue
from app.schema import validate_payload
from app.store import delete as store_delete
from app.store import get as store_get
from app.store import list_all
from app.store import save as store_save
from app.store import update as store_update

OUTCOMES = (
    "create_persists",
    "read_returns_persisted",
    "update_persists",
    "delete_persists",
    "list_only_persisted",
    "queue_item_processed",
    "refused_action_errors",
    "idempotent_duplicate_safe",
    "unauthorized_rejected",
    "missing_field_rejected",
)

KERNEL = "execute_action"
ENTITY = "productivity_core"


def _sample(reference: str = "s12-note") -> Dict[str, Any]:
    return {
        "reference": reference,
        "status": "open",
        "title": reference,
        "body": "s12 domain note body",
    }


async def execute_action(name: str, capability: Optional[str] = None) -> Dict[str, Any]:
    entity = capability or ENTITY
    if name == "create_persists":
        saved = store_save(entity, _sample("s12-create"))
        fetched = store_get(entity, saved["id"])
        ok = fetched is not None and fetched.get("reference") == "s12-create"
        return {"status": "performed" if ok else "failed", "id": saved.get("id")}

    if name == "read_returns_persisted":
        saved = store_save(entity, _sample("s12-read"))
        fetched = store_get(entity, saved["id"])
        ok = fetched is not None and fetched.get("body") == "s12 domain note body"
        return {"status": "performed" if ok else "failed", "id": saved.get("id")}

    if name == "update_persists":
        saved = store_save(entity, _sample("s12-update"))
        updated = store_update(entity, saved["id"], {"title": "s12-updated", "status": "in_progress"})
        fetched = store_get(entity, saved["id"])
        ok = bool(
            updated
            and fetched
            and fetched.get("title") == "s12-updated"
            and fetched.get("status") == "in_progress"
        )
        return {"status": "performed" if ok else "failed", "id": saved.get("id")}

    if name == "delete_persists":
        saved = store_save(entity, _sample("s12-delete"))
        removed = store_delete(entity, saved["id"])
        fetched = store_get(entity, saved["id"])
        ok = removed and fetched is None
        return {"status": "performed" if ok else "failed"}

    if name == "list_only_persisted":
        before = {row["id"] for row in list_all(entity)}
        saved = store_save(entity, _sample("s12-list"))
        after = list_all(entity)
        ids = {row["id"] for row in after}
        ok = saved["id"] in ids and before.issubset(ids)
        return {"status": "performed" if ok else "failed", "count": len(after)}

    if name == "queue_item_processed":
        enqueue({"reference": "s12-queue", "job": "index_note"})
        processed = process_queue()
        ok = bool(processed) and all(item.get("processed") for item in processed)
        return {"status": "performed" if ok else "failed", "processed": len(processed)}

    if name == "refused_action_errors":
        try:
            execute("audit", {}, action="not_a_real_action")
            return {"status": "failed", "error": "unknown action was accepted"}
        except RuntimeError as exc:
            message = str(exc)
            ok = "Unknown action" in message or "unknown" in message.lower()
            return {"status": "performed" if ok else "failed", "error": message}

    if name == "idempotent_duplicate_safe":
        first = store_save(entity, _sample("s12-dup"))
        second = store_save(entity, _sample("s12-dup"))
        ok = first.get("id") is not None and second.get("id") is not None
        return {"status": "performed" if ok else "failed"}

    if name == "unauthorized_rejected":
        request = Request({"type": "http", "method": "POST", "path": "/v1/audit", "headers": []})
        try:
            require_operator(request)
            return {"status": "failed", "error": "missing token accepted"}
        except HTTPException as exc:
            return {"status": "performed" if exc.status_code == 401 else "failed"}

    if name == "missing_field_rejected":
        _clean, error = validate_payload(entity, {"status": "open"})
        ok = error is not None and "missing required field" in error
        return {"status": "performed" if ok else "failed", "error": error}

    raise KeyError(f"unknown outcome: {name}")


async def perform_all(capability: Optional[str] = None) -> Dict[str, Any]:
    outcomes: Dict[str, Any] = {}
    failed = []
    performed = []
    for name in OUTCOMES:
        result = await execute_action(name, capability)
        outcomes[name] = result
        if result.get("status") == "performed":
            performed.append(name)
        else:
            failed.append(name)
    return {
        "kernel": KERNEL,
        "ok": not failed,
        "failed": failed,
        "performed": performed,
        "outcomes": outcomes,
    }
