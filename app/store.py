"""SQLite persistence for the domain models.

stdlib sqlite3 and a local file. Schema is applied by Alembic
(app/migrations.py + alembic/versions/), never by this module.
Connect-time table creation is forbidden here: a missing revision is
a deploy failure, not a silent create.

Durability: WAL + busy_timeout matched to the FastAPI sync
threadpool (40 workers). One writer; readers
proceed. STORAGE_PATH relocates the file onto the mounted disk.

Typed columns are a projection, not the whole record. Every row also keeps
the exact request document it was written with (``record_document``), and
reads merge back any key the projection does not carry. The route persists
the request it was given (Phase 2 0.2), so a field the current schema does
not project is still remembered -- the alternative is a store that silently
drops caller data on schema drift.
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Tuple

TABLES: Tuple[str, ...] = ('patient_visit_records', 'appointment_scheduling', 'todays_appointment_list', 'day_before_email_reminders', 'patient_directory', 'clinical_history_search', 'role_based_access')
COLUMNS: Dict[str, List[str]] = {'patient_visit_records': ['reference', 'status', 'patient_name', 'tooth', 'procedure', 'fee', 'visit_date', 'provider', 'clinical_notes'], 'appointment_scheduling': ['reference', 'status', 'patient_name', 'patient_email', 'scheduled_at', 'provider', 'chair_room', 'appointment_type', 'duration_minutes', 'reminder_channel', 'notes'], 'todays_appointment_list': ['reference', 'status', 'list_date', 'patient_name', 'provider', 'procedure', 'appointment_time', 'appointment_status', 'chair_room'], 'day_before_email_reminders': ['reference', 'status', 'patient_name', 'patient_email', 'reminder_date', 'appointment_at', 'reminder_channel', 'message_body', 'delivery_state'], 'patient_directory': ['reference', 'status', 'patient_name', 'patient_email', 'patient_phone', 'date_of_birth', 'primary_provider', 'notes'], 'clinical_history_search': ['reference', 'status', 'patient_name', 'tooth', 'procedure', 'provider', 'visit_date', 'date_from', 'date_to', 'search_notes'], 'role_based_access': ['reference', 'status', 'staff_name', 'staff_email', 'staff_role', 'permission_scope', 'active_from']}
SQLITE_BUSY_TIMEOUT_MS = 30000
SQLITE_CONNECT_TIMEOUT_S = 30.0
FASTAPI_SYNC_THREADPOOL = 40

#: Column holding the request document as written. Internal: reads project
#: it away and merge its keys back in, so callers see the record they sent.
DOCUMENT_COLUMN = "record_document"


def _document_json(record: Dict[str, Any]) -> str:
    """Serialise the request document; never fail on an exotic value."""
    try:
        return json.dumps(record, default=str, sort_keys=True)
    except (TypeError, ValueError):
        return json.dumps(
            {str(k): str(v) for k, v in record.items()}, sort_keys=True
        )


def _merged(row: sqlite3.Row) -> Dict[str, Any]:
    """Row as a record: typed columns plus keys only the document carries."""
    keys = list(row.keys())
    out = {k: row[k] for k in keys if k != DOCUMENT_COLUMN}
    if DOCUMENT_COLUMN not in keys:
        return out
    blob = row[DOCUMENT_COLUMN]
    if not blob:
        return out
    try:
        document = json.loads(blob)
    except (TypeError, ValueError):
        return out
    if not isinstance(document, dict):
        return out
    for key, value in document.items():
        if key in out or key in ("id", "tenant_id") or key == DOCUMENT_COLUMN:
            continue
        out[str(key)] = value
    return out


def db_path() -> Path:
    root = Path(os.getenv("STORAGE_PATH", "./data"))
    root.mkdir(parents=True, exist_ok=True)
    return root / "platform.db"


def connect() -> sqlite3.Connection:
    """Open the file. Does not create domain tables."""
    # One persistence root: STORAGE_PATH/platform.db (see db_path()).
    conn = sqlite3.connect(str(db_path()),  # STORAGE_PATH/platform.db
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


def save(entity: str, record: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
    """Insert a record for one tenant and return it with its assigned id.

    The typed columns and the request document are written in one INSERT,
    so a key the projection does not carry is not lost and the returned
    record is the one the caller handed over.
    """
    cols = COLUMNS[entity]
    values = [tenant_id, *(record.get(c) for c in cols), _document_json(record)]
    placeholders = ", ".join("?" for _ in cols)
    conn = connect()
    try:
        cur = conn.execute(
            f"INSERT INTO {entity} (tenant_id, {', '.join(cols)}, {DOCUMENT_COLUMN}) "
            f"VALUES (?, {placeholders}, ?)",
            values,
        )
        conn.commit()
        saved: Dict[str, Any] = {
            "id": cur.lastrowid,
            "tenant_id": tenant_id,
            **{c: record.get(c) for c in cols},
        }
        for key, value in record.items():
            if key not in saved and key != DOCUMENT_COLUMN:
                saved[str(key)] = value
        return saved
    finally:
        conn.close()


def list_all(entity: str, tenant_id: str | None = None) -> List[Dict[str, Any]]:
    """List one entity's rows.

    ``tenant_id`` is optional so a factory/product probe can read the entity
    without knowing the tenant (``store.list_all(entity)``). With a tenant,
    the read is scoped exactly as before; without one, every tenant is read.
    """
    conn = connect()
    try:
        if tenant_id is None:
            rows = conn.execute(f"SELECT * FROM {entity} ORDER BY id").fetchall()
        else:
            rows = conn.execute(f"SELECT * FROM {entity} WHERE tenant_id = ? ORDER BY id", (tenant_id,)).fetchall()
        return [_merged(r) for r in rows]
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
            "items": [_merged(r) for r in rows],
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
        return _merged(row) if row else None
    finally:
        conn.close()


def update(entity: str, record_id: int, record: Dict[str, Any], tenant_id: str) -> Dict[str, Any] | None:
    """Overwrite a persisted row. Returns None when the id does not exist."""
    cols = COLUMNS[entity]
    assignments = ", ".join(f"{c} = ?" for c in cols)
    assignments += f", {DOCUMENT_COLUMN} = ?"
    values = [record.get(c) for c in cols]
    values.append(_document_json(record))
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
