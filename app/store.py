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
from typing import Any, Dict, List, Tuple

TABLES: Tuple[str, ...] = ('appointment_scheduling', 'audit_trail', 'billing_invoicing', 'clinic_analytics', 'inventory_management', 'patient_records', 'role_management', 'treatment_management')
COLUMNS: Dict[str, List[str]] = {'patient_records': ['reference', 'status', 'pet_name', 'species', 'breed', 'owner_name', 'owner_email', 'owner_phone', 'date_of_birth', 'weight_kg', 'vaccination_status', 'allergies', 'clinical_notes'], 'appointment_scheduling': ['reference', 'status', 'pet_name', 'owner_name', 'veterinarian', 'appointment_date', 'appointment_time', 'duration_minutes', 'visit_reason', 'room', 'appointment_status'], 'treatment_management': ['reference', 'status', 'pet_name', 'veterinarian', 'treatment_type', 'diagnosis', 'procedure_notes', 'medication', 'dosage', 'treatment_date', 'follow_up_date', 'attachment_path'], 'billing_invoicing': ['reference', 'status', 'invoice_number', 'client_name', 'pet_name', 'line_items', 'subtotal', 'tax_rate', 'total_amount', 'payment_status', 'payment_method', 'invoice_date', 'attachment_path'], 'inventory_management': ['reference', 'status', 'item_name', 'sku', 'category', 'quantity', 'reorder_level', 'unit_cost', 'supplier', 'expiry_date'], 'audit_trail': ['reference', 'status', 'event_type', 'entity_name', 'entity_id', 'actor', 'actor_role', 'action_taken', 'details', 'occurred_at'], 'role_management': ['reference', 'status', 'role_name', 'display_name', 'permissions', 'access_level', 'department', 'is_active'], 'clinic_analytics': ['reference', 'status', 'metric_name', 'metric_value', 'period', 'period_start', 'period_end', 'dimension']}
SQLITE_BUSY_TIMEOUT_MS = 30000
SQLITE_CONNECT_TIMEOUT_S = 30.0
FASTAPI_SYNC_THREADPOOL = 40


def db_path() -> Path:
    root = Path(os.getenv("STORAGE_PATH", "./data"))
    root.mkdir(parents=True, exist_ok=True)
    return root / "platform.db"


def connect() -> sqlite3.Connection:
    """Open the file. Does not create domain tables."""
    conn = sqlite3.connect(  # STORAGE_PATH/platform.db — the only persistence root
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


def save(entity: str, record: Dict[str, Any]) -> Dict[str, Any]:
    """Insert a record and return it with its assigned id."""
    cols = COLUMNS[entity]
    values = [record.get(c) for c in cols]
    placeholders = ", ".join("?" for _ in cols)
    conn = connect()
    try:
        cur = conn.execute(
            f"INSERT INTO {entity} ({', '.join(cols)}) VALUES ({placeholders})",
            values,
        )
        conn.commit()
        return {"id": cur.lastrowid, **{c: record.get(c) for c in cols}}
    finally:
        conn.close()


def _handler_row(
    outcome: Any,
    record: Dict[str, Any],
) -> Dict[str, Any] | None:
    """The row a capability handler already wrote for this request, if any.

    The kernel hands back the handler's own envelope, so the row it persisted
    is visible in ``outcome['output']['stored']``. Matching is conservative: a
    single column that differs (even as a string) means this is NOT the same
    record, and the caller must insert rather than assume.
    """
    stored: Any = None
    if isinstance(outcome, dict):
        output = outcome.get("output")
        if isinstance(output, dict):
            stored = output.get("stored")
    if not isinstance(stored, dict) or stored.get("id") is None:
        return None
    for key, want in (record or {}).items():
        if key not in stored or stored[key] is None:
            continue
        got = stored[key]
        if got != want and str(got) != str(want):
            return None
    return dict(stored)


def save_request(
    entity: str,
    record: Dict[str, Any],
    outcome: Any = None,
) -> Dict[str, Any]:
    """Persist the request payload once per HTTP call.

    Two contracts meet in one call to a capability route: the handler
    persists the domain record (``_persist_record``) and the route persists
    the request (``save(payload)``). Running a plain INSERT here as well
    lands a second copy of the record the handler just wrote -- a duplicate
    invoice, a duplicate stock movement -- and this product is the clinic's
    book of record, so that is a defect, not a rounding error.

    When the handler's own row is visible in its outcome and carries the
    request's values, that row IS the request's row: it is returned and
    nothing is inserted. When the handler stored nothing (or stored a
    different record) the payload is inserted here, so the route's contract
    holds on its own. ``save`` keeps its literal insert semantics: a caller
    that writes N records on purpose still gets N rows (data-lifecycle
    drills).
    """
    existing = _handler_row(outcome, record)
    if existing is not None:
        return existing
    return save(entity, record)


def list_all(entity: str) -> List[Dict[str, Any]]:
    conn = connect()
    try:
        rows = conn.execute(f"SELECT * FROM {entity} ORDER BY id").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


class QueryError(ValueError):
    """A caller asked for a column or ordering this entity does not have."""


def query(
    entity: str,
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
    where, params = [], []
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


def get(entity: str, record_id: int) -> Dict[str, Any] | None:
    conn = connect()
    try:
        row = conn.execute(
            f"SELECT * FROM {entity} WHERE id = ?", (record_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update(entity: str, record_id: int, record: Dict[str, Any]) -> Dict[str, Any] | None:
    """Overwrite a persisted row. Returns None when the id does not exist."""
    cols = COLUMNS[entity]
    assignments = ", ".join(f"{c} = ?" for c in cols)
    values = [record.get(c) for c in cols]
    conn = connect()
    try:
        cur = conn.execute(
            f"UPDATE {entity} SET {assignments} WHERE id = ?",
            [*values, record_id],
        )
        conn.commit()
        if cur.rowcount == 0:
            return None
    finally:
        conn.close()
    return get(entity, record_id)


def delete(entity: str, record_id: int) -> bool:
    """Delete a persisted row. True when a row was removed."""
    conn = connect()
    try:
        cur = conn.execute(
            f"DELETE FROM {entity} WHERE id = ?", (record_id,)
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()
