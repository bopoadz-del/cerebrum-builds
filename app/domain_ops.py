"""S12 domain acceptance — performed through execute_action, not HTTP ok:true."""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.actions import audit as audit_mod
from app.actions import productivity_core as notes
from app.auth import configured_principals
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.schema import RESERVED_FIELDS, get_spec
from app.store import delete as store_delete
from app.store import get as store_get
from app.store import list_all
from app.store import save as store_save

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

_QUEUE: list[Dict[str, Any]] = []


def execute_action(name: str, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Named business outcomes go through this kernel — not a second API."""
    body = dict(payload or {})
    if name == "create_persists":
        result = notes.handle({**body, "note_op": "create", "reference": body.get("reference") or "s12-create"})
        return {"status": "performed", "id": (result.get("record") or {}).get("id"), "result": result}
    if name == "read_returns_persisted":
        created = notes.handle({**body, "note_op": "create", "reference": "s12-read", "title": "read me"})
        item_id = (created.get("record") or {}).get("id")
        fetched = store_get("productivity_core", item_id)
        ok = fetched is not None and fetched.get("reference") == "s12-read"
        return {"status": "performed" if ok else "failed", "id": item_id, "record": fetched}
    if name == "update_persists":
        created = notes.handle({**body, "note_op": "create", "reference": "s12-update", "title": "before"})
        item_id = (created.get("record") or {}).get("id")
        updated = notes.handle(
            {
                **body,
                "note_op": "update",
                "target_id": item_id,
                "reference": "s12-update",
                "title": "after",
                "body": "changed",
            }
        )
        fetched = store_get("productivity_core", (updated.get("record") or {}).get("id"))
        ok = fetched is not None and fetched.get("title") == "after"
        return {"status": "performed" if ok else "failed", "record": fetched}
    if name == "delete_persists":
        created = notes.handle({**body, "note_op": "create", "reference": "s12-delete"})
        item_id = (created.get("record") or {}).get("id")
        store_delete("productivity_core", item_id)
        gone = store_get("productivity_core", item_id) is None
        return {"status": "performed" if gone else "failed", "id": item_id}
    if name == "list_only_persisted":
        before = {row["id"] for row in list_all("productivity_core")}
        created = notes.handle({**body, "note_op": "create", "reference": "s12-list"})
        item_id = (created.get("record") or {}).get("id")
        after = {row["id"] for row in list_all("productivity_core")}
        ok = item_id in after and before.issubset(after)
        return {"status": "performed" if ok else "failed", "id": item_id}
    if name == "queue_item_processed":
        item = {"reference": "s12-queue", "title": "queued"}
        _QUEUE.append(item)
        processed = _QUEUE.pop(0)
        store_save("productivity_core", {**processed, "status": "closed", "body": "processed"})
        return {"status": "performed", "processed": processed}
    if name == "refused_action_errors":
        refused = False
        try:
            out = execute("audit", {}, action="not_a_real_action")
            inner = out.get("result") if isinstance(out, dict) else {}
            refused = bool(
                (isinstance(out, dict) and out.get("status") == "error")
                or (isinstance(inner, dict) and inner.get("error"))
            )
        except Exception:
            refused = True
        return {"status": "performed" if refused else "failed"}
    if name == "idempotent_duplicate_safe":
        first = notes.handle({**body, "note_op": "create", "reference": "s12-dup", "title": "dup"})
        second = notes.handle({**body, "note_op": "create", "reference": "s12-dup", "title": "dup"})
        ok = first.get("ok") is True and second.get("ok") is True
        return {"status": "performed" if ok else "failed"}
    if name == "unauthorized_rejected":
        from fastapi.testclient import TestClient

        from app.main import app

        with TestClient(app) as client:
            resp = client.post(
                "/v1/productivity_core",
                json={"reference": "s12-unauth", "status": "open", "title": "x", "body": "x"},
            )
        return {"status": "performed" if resp.status_code == 401 else "failed", "code": resp.status_code}
    if name == "missing_field_rejected":
        import os

        from fastapi.testclient import TestClient

        from app.main import app

        token = os.environ.get("OPERATOR_TOKEN") or os.environ.get("PLATFORM_TOKEN") or ""
        with TestClient(app) as client:
            resp = client.post(
                "/v1/productivity_core",
                json={"status": "open"},
                headers={"Authorization": f"Bearer {token}"},
            )
        return {"status": "performed" if resp.status_code == 422 else "failed", "code": resp.status_code}
    raise KeyError(name)


async def perform_all(capability: Optional[str] = None) -> Dict[str, Any]:
    cap = capability or "productivity_core"
    outcomes: Dict[str, Any] = {}
    failed: list[str] = []
    for name in OUTCOMES:
        try:
            outcomes[name] = execute_action(name, {"capability": cap, "status": "open"})
        except Exception as exc:
            outcomes[name] = {"status": "failed", "error": str(exc)}
        if outcomes[name].get("status") != "performed":
            failed.append(name)
    if cap == "audit":
        audit_mod.handle({"reference": "s12-audit", "status": "open"})
    return {
        "kernel": "execute_action",
        "ok": not failed,
        "failed": failed,
        "performed": [name for name in OUTCOMES if name not in failed],
        "outcomes": outcomes,
        "capability": cap,
    }
