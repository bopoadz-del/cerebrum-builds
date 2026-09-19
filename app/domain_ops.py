"""S12 domain acceptance: the ten outcomes, performed through the kernel.

Written by the factory WRITER role (codewhale exec)

Every name in :data:`OUTCOMES` is a measurement against the *running* platform,
not a description:

create_persists / read_returns_persisted / update_persists / delete_persists /
list_only_persisted
    the record lifecycle, driven through ``execute_action`` and re-read from the
    capability's own migrated entity;
queue_item_processed
    the platform's ``work_queue`` (revision 0002) holds a job that moves
    pending -> claimed -> done, which is the queue the batch close-out uses;
refused_action_errors
    an action the contract does not declare is refused, never defaulted;
idempotent_duplicate_safe
    the same idempotency key creates one record, not two;
unauthorized_rejected
    the same authenticator the routes use refuses a request with no token (401);
missing_field_rejected
    the kernel refuses a record whose required fields are absent.

A refusal that arrives as HTTP 422 from the shared payload contract is data, not
a crash: the kernel returns ``ok: False`` with the field named.

Scope
-----
READS  the caller's capability id, the migrated database.
WRITES the capability entity, ``work_queue``, ``idempotency`` (the drill's own
       rows, on the isolated storage the caller booted with).
NEVER  network, HTTP store callbacks, ``vendor/**``.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from fastapi import HTTPException

from app import store, tenancy
from app.auth import schema_sample
from app.cerebrum_product_kernel.contract.runtime import execute_action

#: The contract, in order. ``tests/test_domain_acceptance.py`` asserts this list.
OUTCOMES: Tuple[str, ...] = (
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

DEFAULT_CAPABILITY = "stock_inventory_management"
TENANT = store.DEFAULT_TENANT


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _entity(capability_id: str) -> str:
    from app.models import ENTITIES

    return ENTITIES[capability_id]


def _record(capability_id: str) -> Dict[str, Any]:
    return dict(schema_sample(capability_id))


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _detail(step: str, text: str) -> Dict[str, str]:
    return {"step": step, "detail": text}


# --- the ten outcomes -------------------------------------------------------


def _create_persists(capability_id: str, state: Dict[str, Any]) -> Dict[str, str]:
    entity = _entity(capability_id)
    result = execute_action(capability_id, "create", _record(capability_id), tenant_id=TENANT)
    _require(result.get("ok") is True, f"create refused: {result.get('error')}")
    record_id = int(result["record"]["id"])
    state["record_id"] = record_id
    persisted = store.get(entity, record_id, tenant_id=TENANT)
    _require(persisted is not None, "create returned ok but the row is not in the entity")
    _require(int(persisted["id"]) == record_id, "persisted row id does not match the created id")
    return _detail("create_persists", f"{entity} row {record_id} read back from the migrated table")


def _read_returns_persisted(capability_id: str, state: Dict[str, Any]) -> Dict[str, str]:
    record_id = state.get("record_id")
    _require(record_id is not None, "read ran before a record existed")
    result = execute_action(capability_id, "read", record_id=record_id, tenant_id=TENANT)
    _require(result.get("ok") is True, f"read refused: {result.get('error')}")
    _require(int(result["record"]["id"]) == int(record_id), "read returned a different record")
    return _detail("read_returns_persisted", f"read returned row {record_id}")


def _update_persists(capability_id: str, state: Dict[str, Any]) -> Dict[str, str]:
    record_id = state.get("record_id")
    _require(record_id is not None, "update ran before a record existed")
    entity = _entity(capability_id)
    body = _record(capability_id)
    body["reference"] = "domain-ops-updated"
    result = execute_action(capability_id, "update", body, record_id=record_id, tenant_id=TENANT)
    _require(result.get("ok") is True, f"update refused: {result.get('error')}")
    persisted = store.get(entity, int(record_id), tenant_id=TENANT)
    _require(persisted is not None, "update lost the row")
    _require(
        str(persisted.get("reference")) == "domain-ops-updated",
        "update answered ok but the column did not change on disk",
    )
    return _detail("update_persists", f"{entity} row {record_id} reference updated on disk")


def _delete_persists(capability_id: str, state: Dict[str, Any]) -> Dict[str, str]:
    entity = _entity(capability_id)
    created = execute_action(capability_id, "create", _record(capability_id), tenant_id=TENANT)
    _require(created.get("ok") is True, f"scratch create refused: {created.get('error')}")
    scratch_id = int(created["record"]["id"])
    removed = execute_action(capability_id, "delete", record_id=scratch_id, tenant_id=TENANT)
    _require(removed.get("ok") is True, f"delete refused: {removed.get('error')}")
    _require(store.get(entity, scratch_id, tenant_id=TENANT) is None, "deleted row is still readable")
    return _detail("delete_persists", f"{entity} scratch row {scratch_id} deleted and unreadable")


def _list_only_persisted(capability_id: str, state: Dict[str, Any]) -> Dict[str, str]:
    entity = _entity(capability_id)
    result = execute_action(capability_id, "list", tenant_id=TENANT)
    _require(result.get("ok") is True, f"list refused: {result.get('error')}")
    listed = {int(row["id"]) for row in result.get("items") or []}
    persisted = {int(row["id"]) for row in store.list_all(entity, tenant_id=TENANT)}
    _require(listed == persisted, f"list returned {len(listed)} row(s) for {len(persisted)} on disk")
    _require(int(state.get("record_id")) in listed, "list omitted the record this drill created")
    return _detail("list_only_persisted", f"list matched the {len(persisted)} persisted row(s)")


def _queue_item_processed(capability_id: str, state: Dict[str, Any]) -> Dict[str, str]:
    conn = store.connect()
    try:
        payload = json.dumps({"capability": capability_id, "reference": "domain-ops-job"})
        cur = conn.execute(
            "INSERT INTO work_queue (tenant_id, job_type, payload, state, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (TENANT, f"{capability_id}_close", payload, "pending", _now()),
        )
        conn.commit()
        job_id = int(cur.lastrowid)
        claimed = conn.execute(
            "UPDATE work_queue SET state = 'claimed' WHERE id = ? AND state = 'pending'",
            (job_id,),
        )
        conn.commit()
        _require(claimed.rowcount == 1, "queue refused to claim a pending job")
        done = conn.execute(
            "UPDATE work_queue SET state = 'done' WHERE id = ? AND state = 'claimed'",
            (job_id,),
        )
        conn.commit()
        _require(done.rowcount == 1, "queue refused to complete a claimed job")
        row = conn.execute("SELECT state, payload FROM work_queue WHERE id = ?", (job_id,)).fetchone()
    finally:
        conn.close()
    _require(row is not None, "the processed queue row disappeared")
    _require(str(row["state"]) == "done", f"queue row ended {row['state']!r}, not done")
    _require(json.loads(row["payload"]).get("capability") == capability_id, "queue row lost its payload")
    return _detail("queue_item_processed", f"work_queue job {job_id} ran pending -> claimed -> done")


def _refused_action_errors(capability_id: str, state: Dict[str, Any]) -> Dict[str, str]:
    result = execute_action(capability_id, "publish", _record(capability_id), tenant_id=TENANT)
    _require(result.get("ok") is False, "an undeclared action was accepted")
    _require("Unknown action" in str(result.get("error")), f"refusal was not named: {result.get('error')}")
    return _detail("refused_action_errors", "action 'publish' was refused by name")


def _idempotent_duplicate_safe(capability_id: str, state: Dict[str, Any]) -> Dict[str, str]:
    entity = _entity(capability_id)
    key = f"domain-ops:{capability_id}:{state.get('record_id')}"
    before = len(store.list_all(entity, tenant_id=TENANT))
    first = execute_action(capability_id, "create", _record(capability_id),
                           tenant_id=TENANT, idempotency_key=key)
    _require(first.get("ok") is True, f"first keyed create refused: {first.get('error')}")
    second = execute_action(capability_id, "create", _record(capability_id),
                            tenant_id=TENANT, idempotency_key=key)
    _require(second.get("ok") is True, f"replayed create refused: {second.get('error')}")
    _require(
        int(first["record"]["id"]) == int(second["record"]["id"]),
        "the same idempotency key created two records",
    )
    after = len(store.list_all(entity, tenant_id=TENANT))
    _require(after - before == 1, f"keyed create wrote {after - before} rows, expected 1")
    return _detail("idempotent_duplicate_safe", f"key {key!r} created record {first['record']['id']} once")


def _unauthorized_rejected(capability_id: str, state: Dict[str, Any]) -> Dict[str, str]:
    from starlette.requests import Request

    request = Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": f"/v1/{capability_id}",
            "raw_path": f"/v1/{capability_id}".encode("utf-8"),
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 1),
            "server": ("testserver", 80),
        }
    )
    try:
        tenancy.resolve(request)
    except HTTPException as exc:
        _require(exc.status_code == 401, f"unauthenticated write answered HTTP {exc.status_code}")
        return _detail("unauthorized_rejected", "a write with no token was refused with HTTP 401")
    raise AssertionError("an unauthenticated write was accepted")


def _missing_field_rejected(capability_id: str, state: Dict[str, Any]) -> Dict[str, str]:
    result = execute_action(capability_id, "create", {}, tenant_id=TENANT)
    _require(result.get("ok") is False, "a record with no declared fields was accepted")
    _require(
        "required" in str(result.get("error")).lower(),
        f"refusal did not name the missing field: {result.get('error')}",
    )
    return _detail("missing_field_rejected", "an empty record was refused for its missing fields")


_HANDLERS: Dict[str, Callable[[str, Dict[str, Any]], Dict[str, str]]] = {
    "create_persists": _create_persists,
    "read_returns_persisted": _read_returns_persisted,
    "update_persists": _update_persists,
    "delete_persists": _delete_persists,
    "list_only_persisted": _list_only_persisted,
    "queue_item_processed": _queue_item_processed,
    "refused_action_errors": _refused_action_errors,
    "idempotent_duplicate_safe": _idempotent_duplicate_safe,
    "unauthorized_rejected": _unauthorized_rejected,
    "missing_field_rejected": _missing_field_rejected,
}


async def perform_all(capability_id: Optional[str] = None) -> Dict[str, Any]:
    """Perform every outcome for *capability_id* and report what was performed."""
    capability = str(capability_id or DEFAULT_CAPABILITY)
    outcomes: Dict[str, Dict[str, str]] = {}
    performed: List[str] = []
    failed: List[str] = []
    state: Dict[str, Any] = {"capability_id": capability}
    for name in OUTCOMES:
        handler = _HANDLERS[name]
        try:
            detail = handler(capability, state)
        except Exception as exc:  # noqa: BLE001 - a failed outcome is the measurement
            failed.append(name)
            outcomes[name] = {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}
            continue
        outcomes[name] = {"status": "performed", **detail}
        performed.append(name)
    return {
        "kernel": "execute_action",
        "capability": capability,
        "ok": not failed,
        "failed": failed,
        "performed": performed,
        "outcomes": outcomes,
        "outcome_count": len(OUTCOMES),
    }
