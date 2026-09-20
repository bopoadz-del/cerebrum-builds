"""Persisted work queue processed through execute_action.

Enqueue writes a pending row. Process runs the capability through the
vendored kernel and records processed|failed plus the ActionResult.
A handler that returns ok without changing status is a hollow queue (F5).
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from app.store import connect

TABLE = 'work_queue'
IDEMPOTENCY = 'idempotency'
PENDING = "pending"
PROCESSING = "processing"
PROCESSED = "processed"
FAILED = "failed"


def enqueue(
    capability_id: str,
    payload: Dict[str, Any],
    *,
    idempotency_key: str | None = None,
    tenant_id: str,
) -> Dict[str, Any]:
    conn = connect()
    try:
        cur = conn.execute(
            f"INSERT INTO {TABLE} (capability_id, tenant_id, payload, status, result, "
            "idempotency_key) VALUES (?, ?, ?, ?, ?, ?)",
            (
                capability_id,
                tenant_id,
                json.dumps(payload, sort_keys=True),
                PENDING,
                None,
                idempotency_key,
            ),
        )
        conn.commit()
        item_id = int(cur.lastrowid)
    finally:
        conn.close()
    item = get(item_id)
    if item is None:
        raise RuntimeError("work_queue enqueue did not persist")
    return item


def _as_item_id(item_id: Any) -> int:
    """Queue ids are integers. JSON / sqlite / FastAPI may hand us a str."""
    return int(item_id)


def get(item_id: int, *, tenant_id: str | None = None) -> Dict[str, Any] | None:
    """One queue item. With ``tenant_id``, only that tenant's: another
    tenant's item reads as absent -- a 404, never someone else's work."""
    item_id = _as_item_id(item_id)
    conn = connect()
    try:
        if tenant_id is None:
            row = conn.execute(
                f"SELECT * FROM {TABLE} WHERE id = ?", (item_id,)
            ).fetchone()
        else:
            row = conn.execute(
                f"SELECT * FROM {TABLE} WHERE id = ? AND tenant_id = ?",
                (item_id, tenant_id),
            ).fetchone()
        return _row(row) if row else None
    finally:
        conn.close()


def list_all(*, tenant_id: str) -> List[Dict[str, Any]]:
    """The caller's queue. Required, never defaulted: an unscoped list
    returned every tenant's items to any authenticated caller."""
    conn = connect()
    try:
        rows = conn.execute(
            f"SELECT * FROM {TABLE} WHERE tenant_id = ? ORDER BY id", (tenant_id,)
        ).fetchall()
        return [_row(r) for r in rows]
    finally:
        conn.close()


def claim_pending(item_id: int, *, tenant_id: str) -> Dict[str, Any] | None:
    """Claim a pending item the caller's tenant owns. Another tenant's id
    claims nothing -- it used to claim anything, and processing then ran
    that item as its owner on a stranger's request."""
    item_id = _as_item_id(item_id)
    conn = connect()
    try:
        cur = conn.execute(
            f"UPDATE {TABLE} SET status = ? WHERE id = ? AND status = ? AND tenant_id = ?",
            (PROCESSING, item_id, PENDING, tenant_id),
        )
        conn.commit()
        if cur.rowcount == 0:
            return None
    finally:
        conn.close()
    return get(item_id, tenant_id=tenant_id)


def mark(
    item_id: int,
    status: str,
    result: Dict[str, Any] | None,
    *,
    from_status: str | None = None,
) -> Dict[str, Any] | None:
    item_id = _as_item_id(item_id)
    conn = connect()
    try:
        if from_status is None:
            cur = conn.execute(
                f"UPDATE {TABLE} SET status = ?, result = ? WHERE id = ?",
                (
                    status,
                    json.dumps(result, sort_keys=True) if result is not None else None,
                    item_id,
                ),
            )
        else:
            cur = conn.execute(
                f"UPDATE {TABLE} SET status = ?, result = ? WHERE id = ? AND status = ?",
                (
                    status,
                    json.dumps(result, sort_keys=True) if result is not None else None,
                    item_id,
                    from_status,
                ),
            )
        conn.commit()
        if cur.rowcount == 0:
            return None
    finally:
        conn.close()
    return get(item_id)


def recall(key: str) -> Dict[str, Any] | None:
    conn = connect()
    try:
        row = conn.execute(
            f"SELECT * FROM {IDEMPOTENCY} WHERE key = ?", (key,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def remember(key: str, entity: str, record_id: int) -> None:
    conn = connect()
    try:
        conn.execute(
            f"INSERT OR REPLACE INTO {IDEMPOTENCY} (key, entity, record_id) "
            "VALUES (?, ?, ?)",
            (key, entity, record_id),
        )
        conn.commit()
    finally:
        conn.close()


def _row(row: Any) -> Dict[str, Any]:
    item = dict(row)
    if item.get("id") is not None:
        try:
            item["id"] = int(item["id"])
        except (TypeError, ValueError):
            pass
    raw_payload = item.get("payload")
    if isinstance(raw_payload, str):
        try:
            item["payload"] = json.loads(raw_payload)
        except json.JSONDecodeError:
            pass
    raw_result = item.get("result")
    if isinstance(raw_result, str) and raw_result:
        try:
            item["result"] = json.loads(raw_result)
        except json.JSONDecodeError:
            pass
    return item
