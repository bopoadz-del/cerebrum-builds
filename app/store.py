"""SQLite persistence for the domain models.

stdlib sqlite3 and a local file. Schema is applied by Alembic
(app/migrations.py + alembic/versions/), never by this module.
Connect-time table creation is forbidden here: a missing revision is
a deploy failure, not a silent create.

Durability: WAL + busy_timeout matched to the FastAPI sync
threadpool (40 workers). One writer; readers
proceed. STORAGE_PATH relocates the file onto the mounted disk.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

TABLES: Tuple[str, ...] = ('audit_trail', 'checkin_notifications', 'daily_checkin_summary', 'guest_notes_and_preferences', 'record_checkin', 'room_availability_check', 'todays_arrivals_board')
COLUMNS: Dict[str, List[str]] = {'record_checkin': ['reference', 'guest_name', 'room_number', 'nights', 'arrival_time', 'notes', 'status'], 'todays_arrivals_board': ['reference', 'arrival_date', 'guest_name', 'room_number', 'arrived', 'arrivals_count', 'status'], 'room_availability_check': ['reference', 'room_number', 'check_in_date', 'check_out_date', 'is_available', 'status'], 'guest_notes_and_preferences': ['reference', 'guest_name', 'room_number', 'preference', 'note', 'status'], 'checkin_notifications': ['reference', 'guest_name', 'room_number', 'channel', 'recipient', 'status'], 'daily_checkin_summary': ['reference', 'summary_date', 'arrivals_count', 'occupancy_percent', 'no_show_count', 'status'], 'audit_trail': ['reference', 'actor', 'change_type', 'subject_capability', 'changed_at', 'status']}
SQLITE_BUSY_TIMEOUT_MS = 30000
SQLITE_CONNECT_TIMEOUT_S = 30.0
FASTAPI_SYNC_THREADPOOL = 40


def db_path() -> Path:
    root = Path(os.getenv("STORAGE_PATH", "./data"))
    root.mkdir(parents=True, exist_ok=True)
    return root / "platform.db"


def connect() -> sqlite3.Connection:
    """Open the file. Does not create domain tables."""
    conn = sqlite3.connect(  # STORAGE_PATH/platform.db -- the one persistence root
        str(db_path()),
        timeout=SQLITE_CONNECT_TIMEOUT_S,
        check_same_thread=False,
        isolation_level="DEFERRED",
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


#: Tables the platform's own surfaces own (corpus) in addition to the
#: capability entities in COLUMNS/TABLES above.
EXTRA_TABLES: Tuple[str, ...] = ("corpus_documents", "work_queue", "idempotency_keys", "lifecycle_audit")


def save(entity: str, record: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
    """Insert a record for one tenant and return it with its assigned id."""
    cols = COLUMNS[entity]
    values = [tenant_id, *(record.get(c) for c in cols)]
    placeholders = ", ".join("?" for _ in cols)
    conn = connect()
    try:
        cur = conn.execute(
            f"INSERT INTO {entity} (tenant_id, {', '.join(cols)}) VALUES (?, {placeholders})",
            values,
        )
        conn.commit()
        return {"id": cur.lastrowid, "tenant_id": tenant_id, **{c: record.get(c) for c in cols}}
    finally:
        conn.close()


def list_all(entity: str, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Read every row of one entity, oldest first.

    ``tenant_id`` is the tenant resolved from the authenticated principal --
    never a client-supplied name. Every HTTP caller passes it explicitly
    (app/routes.py, app/domain_ops.py, tests/helpers.py), and a supplied
    tenant scopes the SELECT to that tenant.

    It is optional so a caller with no request principal can still read the
    entity: the factory's one-record round-trip read, a migration or backup
    drill, and an operator's own diagnostics all run outside a request, where
    there is no principal to resolve a tenant from. Those callers read across
    tenants on purpose; the result never serves an HTTP response and never
    decides an authorisation.
    """
    conn = connect()
    try:
        if tenant_id is None:
            rows = conn.execute(f"SELECT * FROM {entity} ORDER BY id").fetchall()
        else:
            rows = conn.execute(
                f"SELECT * FROM {entity} WHERE tenant_id = ? ORDER BY id",
                (tenant_id,),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


class QueryError(ValueError):
    """A caller asked for a column or ordering this entity does not have."""


def query(
    entity: str,
    tenant_id: str,
    *,
    filters: Dict[str, Any] | None = None,
    sort: str | None = None,
    order: str = "asc",
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """Filter, sort and page one entity.

    Column names are whitelisted against COLUMNS, never interpolated from
    caller input: an unknown field raises QueryError instead of reaching
    SQL. Values always travel as bound parameters.
    """
    cols = COLUMNS[entity]
    where, params = ["tenant_id = ?"], [tenant_id]
    for name, value in (filters or {}).items():
        if name not in cols:
            raise QueryError("unknown filter field: " + str(name))
        where.append(name + " = ?")
        params.append(value)
    if sort is not None and sort not in cols and sort != "id":
        raise QueryError("unknown sort field: " + str(sort))
    direction = str(order or "asc").lower()
    if direction not in ("asc", "desc"):
        raise QueryError("order must be asc or desc")
    if limit < 1 or limit > 500:
        raise QueryError("limit must be between 1 and 500")
    if offset < 0:
        raise QueryError("offset must be >= 0")
    clause = (" WHERE " + " AND ".join(where)) if where else ""
    column = sort or "id"
    conn = connect()
    try:
        total = conn.execute(
            "SELECT COUNT(*) FROM " + entity + clause, params
        ).fetchone()[0]
        rows = conn.execute(
            "SELECT * FROM " + entity + clause
            + " ORDER BY " + column + " " + direction.upper()
            + " LIMIT ? OFFSET ?",
            [*params, limit, offset],
        ).fetchall()
        return {
            "items": [dict(r) for r in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    finally:
        conn.close()


def get(entity: str, record_id: int, tenant_id: str) -> Dict[str, Any] | None:
    conn = connect()
    try:
        row = conn.execute(
            f"SELECT * FROM {entity} WHERE id = ? AND tenant_id = ?", (record_id, tenant_id)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update(entity: str, record_id: int, record: Dict[str, Any], tenant_id: str) -> Dict[str, Any] | None:
    """Overwrite a persisted row. Returns None when the id does not exist."""
    cols = COLUMNS[entity]
    assignments = ", ".join(f"{c} = ?" for c in cols)
    values = [record.get(c) for c in cols]
    conn = connect()
    try:
        cur = conn.execute(
            f"UPDATE {entity} SET {assignments} WHERE id = ? AND tenant_id = ?",
            [*values, record_id, tenant_id],
        )
        conn.commit()
        if cur.rowcount == 0:
            return None
    finally:
        conn.close()
    return get(entity, record_id, tenant_id)


def delete(entity: str, record_id: int, tenant_id: str) -> bool:
    """Delete a persisted row. True when a row was removed."""
    conn = connect()
    try:
        cur = conn.execute(
            f"DELETE FROM {entity} WHERE id = ? AND tenant_id = ?", (record_id, tenant_id)
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()
