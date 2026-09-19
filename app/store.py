"""SQLite persistence for the Bakery Chain Operations domain models.

Written by the factory WRITER role (codewhale exec)

stdlib ``sqlite3`` and one local file under ``STORAGE_PATH``. The schema is
applied by Alembic (``app/migrations.py`` + ``alembic/versions/``) and never by
this module: connect-time DDL would turn a missing revision into a silent success,
which is how a product ships a table nobody migrated.

One tenant per request: ``save``/``list_all``/``get`` take the tenant from the
caller (the route, which resolved it from the authenticated principal) and
filter on the ``tenant_id`` column. A caller that passes no tenant reads the
whole file; a route never does.

Scope
-----
READS  ``STORAGE_PATH`` (filesystem), the database file.
WRITES the database file only.
NEVER  network, a second database file, ``vendor/**``.
"""

from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.models import ENTITIES

TABLES: Tuple[str, ...] = tuple(sorted(ENTITIES.values()))

#: capability entity -> domain columns (mirrors alembic 0001_baseline).
COLUMNS: Dict[str, List[str]] = {
    "stock_inventory_management": [
        "reference",
        "shop_code",
        "item_code",
        "item_name",
        "quantity_on_hand",
        "reorder_threshold",
        "unit",
        "movement_type",
        "notes",
        "status",
    ],
    "delivery_dispatch_tracking": [
        "reference",
        "order_code",
        "shop_code",
        "driver_code",
        "vehicle_code",
        "vehicle_type",
        "delivery_address",
        "scheduled_at",
        "delivery_state",
        "notes",
        "status",
    ],
    "document_knowledge_qa": [
        "reference",
        "document_title",
        "document_type",
        "source_path",
        "question",
        "answer",
        "notes",
        "status",
    ],
    "fleet_cost_and_pricing": [
        "reference",
        "vehicle_code",
        "vehicle_type",
        "distance_km",
        "unit_price",
        "operating_cost",
        "price_basis",
        "notes",
        "status",
    ],
    "management_reporting_dashboard": [
        "reference",
        "metric_name",
        "metric_value",
        "shop_code",
        "reporting_period",
        "notes",
        "status",
    ],
    "user_roles_workforce": [
        "reference",
        "user_name",
        "user_email",
        "role",
        "shop_code",
        "shift",
        "notes",
        "status",
    ],
    "operational_procedures_readiness": [
        "reference",
        "procedure_code",
        "procedure_title",
        "shop_code",
        "checklist",
        "due_date",
        "notes",
        "status",
    ],
    "audit_evidence_trail": [
        "reference",
        "event_type",
        "entity_name",
        "actor",
        "evidence_path",
        "content_hash",
        "notes",
        "status",
    ],
}

SQLITE_BUSY_TIMEOUT_MS = 30000
SQLITE_CONNECT_TIMEOUT_S = 30.0
FASTAPI_SYNC_THREADPOOL = 40

DEFAULT_TENANT = "local"


class QueryError(ValueError):
    """A caller asked for a column or ordering this entity does not have."""


def db_path() -> Path:
    root = Path(os.getenv("STORAGE_PATH", "./data"))
    root.mkdir(parents=True, exist_ok=True)
    return root / "platform.db"


def connect() -> sqlite3.Connection:
    """Open the file. Does not create domain tables (Alembic owns schema).

    The PRAGMAs are themselves retried: on a brand-new file, forty threads
    switching the journal mode at once is a real lock contention point, and
    a ``PRAGMA journal_mode=WAL`` that answers ``database is locked`` would
    otherwise surface as a failed write at the FastAPI sync threadpool size.
    """
    conn = sqlite3.connect(  # STORAGE_PATH/platform.db -- the one persistence root
        str(db_path()),
        timeout=SQLITE_CONNECT_TIMEOUT_S,
        check_same_thread=False,
        isolation_level="DEFERRED",
    )
    conn.row_factory = sqlite3.Row
    for attempt in range(_LOCK_RETRIES):
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA foreign_keys=ON")
            return conn
        except sqlite3.OperationalError as exc:
            if not _is_locked(exc) or attempt == _LOCK_RETRIES - 1:
                conn.close()
                raise
            time.sleep(_LOCK_BACKOFF_S * (attempt + 1))
    conn.close()
    raise AssertionError("unreachable: connect() retry loop exited")


def _resolve_entity(entity: str) -> str:
    name = str(entity or "").replace("-", "_")
    if name not in COLUMNS:
        raise QueryError("unknown entity: " + name)
    return name


#: Attempts for a write (or a connection's PRAGMA negotiation) that finds
#: the file locked. WAL plus a 30s busy timeout covers the contention; this
#: covers the moment a fresh connection is still negotiating the WAL, which
#: is short and bounded. Six attempts at a linear backoff is ~2s of slack,
#: measured against forty concurrent writers on an empty file.
_LOCK_RETRIES = 6
_LOCK_BACKOFF_S = 0.1


def _is_locked(exc: sqlite3.OperationalError) -> bool:
    return "locked" in str(exc).lower()


def save(
    entity: str,
    record: Dict[str, Any],
    tenant_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Insert a record and return it with its assigned id.

    ``record`` is the request payload (not a handler envelope). Columns come
    from ``COLUMNS``; a field the entity does not declare is not written.
    """
    name = _resolve_entity(entity)
    cols = COLUMNS[name]
    tenant = str(tenant_id or DEFAULT_TENANT)
    values = [record.get(c) for c in cols]
    sql = (
        f"INSERT INTO {name} (tenant_id, {', '.join(cols)}) "
        f"VALUES ({', '.join('?' for _ in range(len(cols) + 1))})"
    )
    for attempt in range(_LOCK_RETRIES):
        # connect() is inside the retry on purpose: the failure mode at the
        # sync threadpool size is a connection that cannot finish negotiating
        # WAL, not only an insert that finds the write lock held.
        try:
            conn = connect()
        except sqlite3.OperationalError as exc:
            if not _is_locked(exc) or attempt == _LOCK_RETRIES - 1:
                raise
            time.sleep(_LOCK_BACKOFF_S * (attempt + 1))
            continue
        try:
            cur = conn.execute(sql, [tenant, *values])
            conn.commit()
            return {"id": cur.lastrowid, "tenant_id": tenant,
                    **{c: record.get(c) for c in cols}}
        except sqlite3.OperationalError as exc:
            if not _is_locked(exc) or attempt == _LOCK_RETRIES - 1:
                raise
            time.sleep(_LOCK_BACKOFF_S * (attempt + 1))
        finally:
            conn.close()
    raise AssertionError("unreachable: save() retry loop exited without a result")


def list_all(entity: str, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
    name = _resolve_entity(entity)
    conn = connect()
    try:
        if tenant_id:
            rows = conn.execute(
                f"SELECT * FROM {name} WHERE tenant_id = ? ORDER BY id",
                (str(tenant_id),),
            ).fetchall()
        else:
            rows = conn.execute(f"SELECT * FROM {name} ORDER BY id").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get(
    entity: str,
    record_id: int,
    tenant_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    name = _resolve_entity(entity)
    conn = connect()
    try:
        if tenant_id:
            row = conn.execute(
                f"SELECT * FROM {name} WHERE id = ? AND tenant_id = ?",
                (record_id, str(tenant_id)),
            ).fetchone()
        else:
            row = conn.execute(
                f"SELECT * FROM {name} WHERE id = ?", (record_id,)
            ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def query(
    entity: str,
    *,
    filters: Optional[Dict[str, Any]] = None,
    sort: Optional[str] = None,
    order: str = "asc",
    limit: int = 50,
    offset: int = 0,
    tenant_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Filter, sort and page one entity. Column names are whitelisted."""
    name = _resolve_entity(entity)
    cols = COLUMNS[name]
    where: List[str] = []
    params: List[Any] = []
    if tenant_id:
        where.append("tenant_id = ?")
        params.append(str(tenant_id))
    for field, value in (filters or {}).items():
        if field not in cols:
            raise QueryError("unknown filter field: " + str(field))
        where.append(field + " = ?")
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
            "SELECT COUNT(*) FROM " + name + clause, params
        ).fetchone()[0]
        rows = conn.execute(
            "SELECT * FROM " + name + clause
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


def update(
    entity: str,
    record_id: int,
    record: Dict[str, Any],
    tenant_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Overwrite a persisted row. None when the id does not exist."""
    name = _resolve_entity(entity)
    cols = COLUMNS[name]
    assignments = ", ".join(f"{c} = ?" for c in cols)
    values = [record.get(c) for c in cols]
    conn = connect()
    try:
        sql = f"UPDATE {name} SET {assignments} WHERE id = ?"
        args: List[Any] = [*values, record_id]
        if tenant_id:
            sql += " AND tenant_id = ?"
            args.append(str(tenant_id))
        cur = conn.execute(sql, args)
        conn.commit()
        if cur.rowcount == 0:
            return None
    finally:
        conn.close()
    return get(name, record_id, tenant_id)


def delete(entity: str, record_id: int, tenant_id: Optional[str] = None) -> bool:
    name = _resolve_entity(entity)
    conn = connect()
    try:
        sql = f"DELETE FROM {name} WHERE id = ?"
        args: List[Any] = [record_id]
        if tenant_id:
            sql += " AND tenant_id = ?"
            args.append(str(tenant_id))
        cur = conn.execute(sql, args)
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()
