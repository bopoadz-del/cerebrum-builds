"""The durable dial list: a queued call is a row, not a process's memory.

A restart must not lose a queued dial, and two workers must not dial the
same lead. So the queue lives in the platform's one database, a claim is a
status change with the claimant's tenant recorded on the item, and an
idempotency key makes a repeated request return the row it already made.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Mapping, Optional

from app.store import connect, placeholder

PENDING = "pending"
PROCESSING = "processing"
PROCESSED = "processed"
FAILED = "failed"

STATUSES = (PENDING, PROCESSING, PROCESSED, FAILED)


def _sql(text: str) -> str:
    return text.replace("?", placeholder())


def _row(row: Any) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    record = dict(row)
    raw = record.get("payload")
    if isinstance(raw, str) and raw:
        try:
            record["payload"] = json.loads(raw)
        except ValueError:
            pass
    result = record.get("result")
    if isinstance(result, str) and result:
        try:
            record["result"] = json.loads(result)
        except ValueError:
            pass
    return record


def enqueue(
    capability_id: str,
    payload: Mapping[str, Any],
    *,
    idempotency_key: Optional[str] = None,
    tenant_id: str,
    priority: int = 0,
) -> Dict[str, Any]:
    """Add one item, tenant-scoped. Repeating a key returns the same item."""
    if not tenant_id:
        raise ValueError("tenant_id is required: a queue item is never tenantless")
    if idempotency_key:
        for item in list_all(tenant_id=tenant_id):
            if str(item.get("idempotency_key") or "") == str(idempotency_key):
                return item
    from app.domain import utc_now

    stamp = utc_now()
    conn = connect()
    try:
        cursor = conn.execute(
            _sql(
                "INSERT INTO work_queue (tenant_id, capability_id, payload, status, "
                "idempotency_key, attempts, result, claimed_at, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            ),
            (
                tenant_id,
                str(capability_id),
                json.dumps(dict(payload or {}), sort_keys=True, default=str),
                PENDING,
                idempotency_key,
                0,
                None,
                None,
                stamp,
                stamp,
            ),
        )
        conn.commit()
        new_id = cursor.lastrowid
    finally:
        conn.close()
    item = get(int(new_id), tenant_id=tenant_id)
    if item is None:  # pragma: no cover - a write that cannot be read back
        raise RuntimeError("queue item did not read back after enqueue")
    return item


def get(item_id: int, *, tenant_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    conn = connect()
    try:
        if tenant_id:
            row = conn.execute(
                _sql("SELECT * FROM work_queue WHERE id = ? AND tenant_id = ?"),
                (int(item_id), tenant_id),
            ).fetchone()
        else:
            row = conn.execute(
                _sql("SELECT * FROM work_queue WHERE id = ?"), (int(item_id),)
            ).fetchone()
        return _row(row)
    finally:
        conn.close()


def list_all(*, tenant_id: str) -> List[Dict[str, Any]]:
    conn = connect()
    try:
        rows = conn.execute(
            _sql("SELECT * FROM work_queue WHERE tenant_id = ? ORDER BY id"), (tenant_id,)
        ).fetchall()
        return [item for item in (_row(row) for row in rows) if item]
    finally:
        conn.close()


def claim_pending(item_id: int, *, tenant_id: str) -> Optional[Dict[str, Any]]:
    """Move a pending item to processing, for this tenant only."""
    from app.domain import utc_now

    conn = connect()
    try:
        row = conn.execute(
            _sql("SELECT * FROM work_queue WHERE id = ? AND tenant_id = ?"),
            (int(item_id), tenant_id),
        ).fetchone()
        item = _row(row)
        if item is None or item.get("status") != PENDING:
            return None
        conn.execute(
            _sql(
                "UPDATE work_queue SET status = ?, attempts = ?, claimed_at = ?, updated_at = ? "
                "WHERE id = ? AND tenant_id = ? AND status = ?"
            ),
            (
                PROCESSING,
                int(item.get("attempts") or 0) + 1,
                utc_now(),
                utc_now(),
                int(item_id),
                tenant_id,
                PENDING,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return get(int(item_id), tenant_id=tenant_id)


def mark(
    item_id: int,
    status: str,
    result: Optional[Mapping[str, Any]] = None,
    *,
    from_status: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Record what happened to a claimed item. Never a silent no-op."""
    from app.domain import utc_now

    if status not in STATUSES:
        raise ValueError(f"unknown queue status: {status}")
    conn = connect()
    try:
        clauses = ["id = ?"]
        params: List[Any] = [int(item_id)]
        if tenant_id:
            clauses.append("tenant_id = ?")
            params.append(tenant_id)
        if from_status:
            clauses.append("status = ?")
            params.append(from_status)
        clause = " AND ".join(clauses)
        # nosec B608 - the clause is built from fixed literals; values are bound
        conn.execute(
            _sql(
                f"UPDATE work_queue SET status = ?, result = ?, updated_at = ? WHERE {clause}"  # nosec B608
            ),
            [
                status,
                json.dumps(dict(result or {}), sort_keys=True, default=str) if result else None,
                utc_now(),
                *params,
            ],
        )
        conn.commit()
    finally:
        conn.close()
    return get(int(item_id), tenant_id=tenant_id)


def recall(key: str, *, tenant_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """The record a previous request with this idempotency key produced."""
    conn = connect()
    try:
        if tenant_id:
            row = conn.execute(
                _sql("SELECT * FROM idempotency WHERE key = ? AND tenant_id = ?"),
                (str(key), tenant_id),
            ).fetchone()
        else:
            row = conn.execute(
                _sql("SELECT * FROM idempotency WHERE key = ? ORDER BY id LIMIT 1"), (str(key),)
            ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def remember(key: str, entity: str, record_id: int, *, tenant_id: str = "local") -> None:
    """Remember that a request made this row, so a repeat returns it."""
    from app.domain import utc_now

    conn = connect()
    try:
        conn.execute(
            _sql(
                "INSERT INTO idempotency (tenant_id, key, entity, record_id, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)"
            ),
            (tenant_id, str(key), str(entity), int(record_id), utc_now(), utc_now()),
        )
        conn.commit()
    finally:
        conn.close()


def depth(*, tenant_id: str) -> Dict[str, int]:
    items = list_all(tenant_id=tenant_id)
    counts = {status: 0 for status in STATUSES}
    for item in items:
        status = str(item.get("status") or "")
        if status in counts:
            counts[status] += 1
    counts["total"] = len(items)
    return counts
