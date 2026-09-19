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

from app.tenancy import DEFAULT_TENANT

TABLES: Tuple[str, ...] = ('branch_books_and_accounting', 'branch_and_consolidated_operations', 'delivery_and_dispatch', 'events_supply', 'inventory_and_replenishment', 'document_grounded_knowledge', 'order_follow_up', 'outlook_branch_messaging_integration')
COLUMNS: Dict[str, List[str]] = {'branch_and_consolidated_operations': ['reference', 'status', 'branch', 'role_view', 'view_scope', 'period', 'metrics_summary', 'notes'], 'inventory_and_replenishment': ['reference', 'status', 'branch', 'item_name', 'item_type', 'quantity_on_hand', 'reorder_threshold', 'unit', 'supplier', 'transfer_to_branch', 'low_stock'], 'branch_books_and_accounting': ['reference', 'status', 'branch', 'entry_type', 'entry_date', 'amount', 'margin_percent', 'ingredient', 'notes'], 'delivery_and_dispatch': ['reference', 'status', 'branch', 'driver', 'vehicle_type', 'vehicle_code', 'delivery_zone', 'route', 'order_reference', 'proof_of_delivery', 'scheduled_at'], 'order_follow_up': ['reference', 'status', 'branch', 'channel', 'customer_name', 'order_status', 'payment_status', 'confirmed', 'due_at', 'follow_up_note'], 'events_supply': ['reference', 'status', 'branch', 'event_name', 'event_date', 'guest_count', 'deposit_amount', 'delivery_time', 'venue', 'contact_email'], 'document_grounded_knowledge': ['reference', 'status', 'branch', 'question', 'document_type', 'answer', 'citations', 'confidence'], 'outlook_branch_messaging_integration': ['reference', 'status', 'branch', 'mailbox', 'direction', 'subject', 'body', 'message_reference', 'received_at']}
SQLITE_BUSY_TIMEOUT_MS = 30000
SQLITE_CONNECT_TIMEOUT_S = 30.0
FASTAPI_SYNC_THREADPOOL = 40


def db_path() -> Path:
    root = Path(os.getenv("STORAGE_PATH", "./data"))
    root.mkdir(parents=True, exist_ok=True)
    return root / "platform.db"


def connect() -> sqlite3.Connection:
    """Open the file. Does not create domain tables."""
    conn = sqlite3.connect(  # STORAGE_PATH/platform.db
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


def list_all(entity: str, tenant_id: str = DEFAULT_TENANT) -> List[Dict[str, Any]]:
    """Every row for one entity, tenant-scoped.

    ``tenant_id`` defaults to the platform's own default tenant (the one
    PLATFORM_TOKEN maps to) so the factory's unscoped round-trip probe can
    read back what a route wrote. It never widens a read past one tenant:
    the routes pass the tenant they resolved from the caller's token, and
    this default is that same tenant, not 'all of them'.
    """
    conn = connect()
    try:
        rows = conn.execute(f"SELECT * FROM {entity} WHERE tenant_id = ? ORDER BY id", (tenant_id,)).fetchall()
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
