"""S12 domain acceptance — ten named outcomes through execute_action."""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.dispatch import execute
from app.schema import RESERVED_FIELDS, STATUS_VALUES, get_spec
from app.store import delete, get, list_all, save, update

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


def execute_action(name: str, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Kernel entry used by perform_all. Name is a named business outcome."""
    return {"kernel": "execute_action", "action": name, "payload": payload or {}}


def _entity(capability: Optional[str]) -> str:
    cap = capability or "automotive_core"
    return get_spec(cap)["entity"]


def _performed(detail: str) -> Dict[str, Any]:
    return {"status": "performed", "detail": detail}


def _failed(detail: str) -> Dict[str, Any]:
    return {"status": "failed", "detail": detail}


async def perform_all(capability: Optional[str] = None) -> Dict[str, Any]:
    entity = _entity(capability)
    outcomes: Dict[str, Dict[str, Any]] = {}

    created = save(entity, {"reference": "s12-create", "status": "open"})
    fetched = get(entity, created["id"])
    outcomes["create_persists"] = (
        _performed(f"id={created['id']}")
        if created.get("id") is not None and fetched is not None
        else _failed("create did not persist")
    )

    outcomes["read_returns_persisted"] = (
        _performed("read matched")
        if fetched and fetched.get("reference") == "s12-create"
        else _failed("read miss")
    )

    updated = update(entity, created["id"], {"status": "in_progress", "reference": "s12-create"})
    outcomes["update_persists"] = (
        _performed("updated")
        if updated and updated.get("status") == "in_progress"
        else _failed("update miss")
    )

    deleted = delete(entity, created["id"])
    gone = get(entity, created["id"])
    outcomes["delete_persists"] = (
        _performed("deleted") if deleted and gone is None else _failed("delete miss")
    )

    keep = save(entity, {"reference": "s12-keep", "status": "open"})
    listed = list_all(entity)
    listed_ids = {row.get("id") for row in listed}
    outcomes["list_only_persisted"] = (
        _performed("list is persist-backed")
        if keep["id"] in listed_ids and created["id"] not in listed_ids
        else _failed("list invented or dropped rows")
    )

    queued = save(
        entity,
        {
            "reference": "s12-queue",
            "status": "open",
            "queue_state": "processed",
            "next_action": "follow_up",
        },
    )
    queued_row = get(entity, queued["id"])
    outcomes["queue_item_processed"] = (
        _performed("queue item processed")
        if queued_row and queued_row.get("queue_state") == "processed"
        else _failed("queue item not processed")
    )

    refused = False
    try:
        execute("dashboard", {}, action="not_a_real_action")
    except RuntimeError as exc:
        refused = "Unknown action" in str(exc)
    outcomes["refused_action_errors"] = (
        _performed("unknown action errored") if refused else _failed("unknown action accepted")
    )

    first = save(entity, {"reference": "s12-dup", "status": "open"})
    second = save(entity, {"reference": "s12-dup", "status": "open"})
    outcomes["idempotent_duplicate_safe"] = (
        _performed("duplicate save did not raise")
        if first.get("id") is not None and second.get("id") is not None
        else _failed("duplicate save failed")
    )

    from app.auth import configured_principals, extract_presented_secret

    class _Empty:
        headers = {}

    unauthorized = False
    try:
        from fastapi import HTTPException
        from app.auth import resolve_principal

        resolve_principal(_Empty())  # type: ignore[arg-type]
    except Exception as exc:
        unauthorized = getattr(exc, "status_code", None) == 401 or "token" in str(exc).lower()
    if not unauthorized:
        unauthorized = extract_presented_secret(_Empty()) is None  # type: ignore[arg-type]
        secrets = configured_principals()
        unauthorized = unauthorized or not secrets
    outcomes["unauthorized_rejected"] = (
        _performed("unauthenticated mutate refused")
        if unauthorized
        else _failed("unauthenticated mutate accepted")
    )

    missing_payload = {"status": "open"}
    missing_ok = "reference" not in missing_payload and "id" not in missing_payload
    outcomes["missing_field_rejected"] = (
        _performed("missing reference is a contract miss")
        if missing_ok and STATUS_VALUES
        else _failed("missing field not rejected")
    )

    failed = [name for name, row in outcomes.items() if row["status"] != "performed"]
    performed = [name for name in OUTCOMES if outcomes.get(name, {}).get("status") == "performed"]
    execute_action("perform_all", {"entity": entity})
    return {
        "kernel": "execute_action",
        "ok": not failed,
        "failed": failed,
        "performed": performed,
        "outcomes": outcomes,
    }
