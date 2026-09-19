"""Kernel runtime: the product.create/read/update/delete/list actions.

The routes call ``handle()`` directly and persist the request; this runtime is
the same lifecycle expressed as kernel actions so a chat surface, a script or
the acceptance harness can drive the platform without the HTTP layer.

Two contracts matter here:

* the payload contract is shared with the routes (``app.auth.validate_payload``)
  — a refusal is returned as ``ok: False`` with the field named, so a caller
  sees data rather than a stack trace;
* ``idempotency_key`` is honoured against the platform's own ``idempotency``
  table (revision 0002): replaying a keyed create returns the record the first
  call wrote instead of writing a second one.

Written by the factory WRITER role (codewhale exec)

Scope
-----
READS  the caller's payload, the migrated database.
WRITES the capability entity and the ``idempotency`` table.
NEVER  network, HTTP store callbacks, ``vendor/**``.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from fastapi import HTTPException

from app import store
from app.auth import validate_payload
from app.cerebrum_product_kernel.contract.registry import entity_for
from app.models import MODELS

ACTIONS = ("create", "read", "update", "delete", "list")


def _entity(capability_id: str) -> str:
    entity = entity_for(capability_id)
    if entity is None:
        raise ValueError("unknown capability: " + str(capability_id))
    return entity


def _checked(capability_id: str, payload: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """``(record, refusal)``: the payload contract's answer, never an exception."""
    try:
        return validate_payload(capability_id, payload), None
    except HTTPException as exc:
        return None, str(exc.detail)


def _idempotency_key(tenant_id: str, capability_id: str, key: str) -> str:
    return f"{tenant_id}:{capability_id}:{key}"


def _remembered(entity: str, scoped_key: str, tenant_id: str) -> Optional[Dict[str, Any]]:
    conn = store.connect()
    try:
        row = conn.execute(
            "SELECT record_id FROM idempotency WHERE key = ?", (scoped_key,)
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return store.get(entity, int(row[0]), tenant_id=tenant_id)


def _remember(scoped_key: str, capability_id: str, record_id: int, tenant_id: str) -> None:
    conn = store.connect()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO idempotency (key, tenant_id, capability_id, record_id, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (scoped_key, tenant_id, capability_id, int(record_id),
             datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def execute_action(
    capability_id: str,
    action: str,
    payload: Optional[Dict[str, Any]] = None,
    *,
    record_id: Optional[int] = None,
    tenant_id: str = "local",
    idempotency_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Run one kernel action for *capability_id*."""
    name = str(action or "").strip().lower()
    if name not in ACTIONS:
        return {"ok": False, "status": "error",
                "error": f"Unknown action: {action}", "available": list(ACTIONS)}
    if str(capability_id or "") not in MODELS:
        return {"ok": False, "status": "error",
                "error": f"Unknown capability: {capability_id}"}
    entity = _entity(capability_id)
    data = dict(payload or {})

    if name == "create":
        record, refusal = _checked(capability_id, data)
        if refusal is not None:
            return {"ok": False, "status": "error", "capability": capability_id,
                    "error": refusal}
        scoped_key = (
            _idempotency_key(str(tenant_id), capability_id, str(idempotency_key))
            if idempotency_key
            else None
        )
        if scoped_key:
            try:
                existing = _remembered(entity, scoped_key, str(tenant_id))
            except sqlite3.OperationalError as exc:
                return {"ok": False, "status": "error", "capability": capability_id,
                        "error": f"idempotency table unavailable: {exc}"}
            if existing is not None:
                return {"ok": True, "status": "success", "capability": capability_id,
                        "record": existing, "replayed": True}
        result = _dispatch(capability_id, record)
        if result.get("ok") is False:
            return {"ok": False, "status": "error", "capability": capability_id,
                    "error": result.get("error"), "results": result.get("results")}
        saved = store.save(entity, record, tenant_id=tenant_id)
        if scoped_key:
            try:
                _remember(scoped_key, capability_id, int(saved["id"]), str(tenant_id))
            except sqlite3.OperationalError as exc:
                return {"ok": False, "status": "error", "capability": capability_id,
                        "error": f"idempotency table unavailable: {exc}"}
        return {"ok": True, "status": "success", "capability": capability_id,
                "record": saved, "result": result.get("results", {})}

    if name == "read":
        if record_id is None:
            return {"ok": False, "status": "error", "error": "record_id required"}
        row = store.get(entity, int(record_id), tenant_id=tenant_id)
        if row is None:
            return {"ok": False, "status": "error", "error": "record_not_found"}
        return {"ok": True, "status": "success", "record": row}

    if name == "list":
        rows = store.list_all(entity, tenant_id=tenant_id)
        return {"ok": True, "status": "success", "items": rows, "total": len(rows)}

    if name == "update":
        if record_id is None:
            return {"ok": False, "status": "error", "error": "record_id required"}
        record, refusal = _checked(
            capability_id, {**data, "reference": data.get("reference") or "sample"}
        )
        if refusal is not None:
            return {"ok": False, "status": "error", "capability": capability_id,
                    "error": refusal}
        updated = store.update(entity, int(record_id), record, tenant_id=tenant_id)
        if updated is None:
            return {"ok": False, "status": "error", "error": "record_not_found"}
        return {"ok": True, "status": "success", "record": updated}

    if record_id is None:
        return {"ok": False, "status": "error", "error": "record_id required"}
    removed = store.delete(entity, int(record_id), tenant_id=tenant_id)
    return {"ok": bool(removed), "status": "success" if removed else "error",
            "deleted": bool(removed)}


def _dispatch(capability_id: str, record: Dict[str, Any]) -> Dict[str, Any]:
    from app.actions import handler_for

    return handler_for(capability_id)(record)
