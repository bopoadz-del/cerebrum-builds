"""Tenant-scoped persistence for the hotel operations platform.

One persistence root: ``STORAGE_PATH``. The connection itself comes from
``app.db`` -- DATABASE_URL set means Postgres, absent means the SQLite file
under STORAGE_PATH -- so the store can never disagree with the deployment
about which database it is writing to. Schema is applied by Alembic
(``alembic/versions/``), never here: this module issues no DDL at all, and
connect() (app/db.py) applies ``PRAGMA journal_mode=WAL`` and
``PRAGMA busy_timeout`` -- the durability settings the migrations and the
FastAPI sync threadpool both rely on.

Every row carries the ``tenant_id`` resolved from the authenticated principal
(app.tenancy). Reads and writes are scoped by it, so a record belonging to
another tenant is invisible rather than forbidden (404, never 403).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.db import backend_name, connect, is_postgres, sqlite_path

#: Entity -> its domain columns (the columns alembic 0001 created, minus id
#: and tenant_id which the store owns).
TABLES: Tuple[str, ...] = (
    "property_and_room_registry",
    "front_desk_and_guest_stay",
    "housekeeping_and_maintenance",
    "guest_engagement_and_segmentation",
    "document_and_knowledge_answers",
    "operations_billing",
    "operations_oversight_dashboard",
    "external_integration_adapter",
)

COLUMNS: Dict[str, List[str]] = {'property_and_room_registry': ['reference', 'status', 'property_name', 'building', 'floor', 'room_number', 'room_type', 'capacity', 'room_status', 'notes'], 'front_desk_and_guest_stay': ['reference', 'status', 'guest_name', 'room_number', 'arrival_date', 'departure_date', 'guests_count', 'stay_status', 'folio_currency', 'notes'], 'housekeeping_and_maintenance': ['reference', 'status', 'title', 'work_type', 'room_number', 'priority', 'due_date', 'assigned_to', 'work_status', 'notes'], 'guest_engagement_and_segmentation': ['reference', 'status', 'guest_name', 'recency_days', 'frequency', 'monetary', 'segment', 'delivery_channel', 'offer_code', 'notes'], 'document_and_knowledge_answers': ['reference', 'status', 'title', 'document_kind', 'question', 'document_text', 'attachment_path', 'answer', 'source_document', 'authority_label', 'notes'], 'operations_billing': ['setting', 'reference', 'status', 'folio_reference', 'charge_type', 'amount', 'currency', 'tax_rate_percent', 'total_amount', 'notes'], 'operations_oversight_dashboard': ['reference', 'status', 'dashboard_name', 'widget', 'window_days', 'operator_role', 'occupancy_percent', 'open_work_orders', 'notes'], 'external_integration_adapter': ['reference', 'status', 'system', 'resource', 'direction', 'payload_format', 'endpoint_url', 'records_seen', 'notes']}

#: Matched to the FastAPI sync threadpool: one writer, readers proceed.
SQLITE_BUSY_TIMEOUT_MS = 30000
SQLITE_CONNECT_TIMEOUT_S = 30.0
FASTAPI_SYNC_THREADPOOL = 40


def db_path():
    """The SQLite file this platform uses when DATABASE_URL is unset.

    The path lives in app/db.py (one place decides); this accessor exists so
    callers/tests can ask the store where its data is without opening a
    second database.
    """
    return sqlite_path()


class StoreError(RuntimeError):
    """The store refused a request. The message names the reason."""


class QueryError(ValueError):
    """A caller asked for a column or ordering this entity does not have."""


def _sql(sqlite_sql: str) -> str:
    """Translate ``?`` placeholders for the configured backend."""
    if is_postgres():
        return sqlite_sql.replace("?", "%s")
    return sqlite_sql


def _fetchall(conn: Any, sqlite_sql: str, params: Sequence[Any]) -> List[Dict[str, Any]]:
    cur = conn.execute(_sql(sqlite_sql), tuple(params))
    rows = cur.fetchall()
    out: List[Dict[str, Any]] = []
    for row in rows:
        mapping = getattr(row, "_mapping", None)
        out.append(dict(mapping) if mapping is not None else dict(row))
    return out


def _fetchone(conn: Any, sqlite_sql: str, params: Sequence[Any]) -> Optional[Dict[str, Any]]:
    rows = _fetchall(conn, sqlite_sql, params)
    return rows[0] if rows else None


def _columns(entity: str) -> List[str]:
    try:
        return COLUMNS[entity]
    except KeyError as exc:
        raise StoreError(
            f"unknown entity {entity!r}; known: {', '.join(sorted(COLUMNS))}"
        ) from exc


def save(entity: str, record: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
    """Insert one tenant-scoped record and return it with its assigned id."""
    cols = _columns(entity)
    tenant = str(tenant_id or "").strip()
    if not tenant:
        raise StoreError("tenant_id is required: tenancy is never inferred")
    values = [tenant, *(record.get(name) for name in cols)]
    placeholders = ", ".join("?" for _ in values)
    conn = connect()
    try:
        cur = conn.execute(
            _sql(
                f"INSERT INTO {entity} (tenant_id, {', '.join(cols)}) "
                f"VALUES ({placeholders})"
            ),
            tuple(values),
        )
        try:
            new_id = cur.lastrowid
        except Exception:  # pragma: no cover - SQLAlchemy result has no lastrowid
            new_id = None
        conn.commit()
        if new_id is None:
            row = _fetchone(
                conn,
                f"SELECT id FROM {entity} WHERE tenant_id = ? ORDER BY id DESC LIMIT 1",
                [tenant],
            )
            new_id = (row or {}).get("id")
        return {
            "id": new_id,
            "tenant_id": tenant,
            **{name: record.get(name) for name in cols},
        }
    finally:
        conn.close()


def get(entity: str, record_id: int, tenant_id: str) -> Optional[Dict[str, Any]]:
    """One record for this tenant, or None. Another tenant's row is not found."""
    _columns(entity)
    conn = connect()
    try:
        return _fetchone(
            conn,
            f"SELECT * FROM {entity} WHERE id = ? AND tenant_id = ?",
            [record_id, tenant_id],
        )
    finally:
        conn.close()


def list_all(entity: str, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Every row for one tenant.

    ``tenant_id`` is required on every HTTP path (the route resolves it from
    the authenticated principal). It is optional here because the platform's
    own probes -- the factory's round-trip check and app.backup's row count --
    read the table without a request in hand; omitting it reads the whole
    table, and no route does that.
    """
    _columns(entity)
    if tenant_id is None:
        sql, params = f"SELECT * FROM {entity} ORDER BY id", []
    else:
        sql, params = f"SELECT * FROM {entity} WHERE tenant_id = ? ORDER BY id", [tenant_id]
    conn = connect()
    try:
        return _fetchall(conn, sql, params)
    finally:
        conn.close()


def query(
    entity: str,
    tenant_id: Optional[str] = None,
    *,
    filters: Optional[Dict[str, Any]] = None,
    sort: Optional[str] = None,
    order: str = "asc",
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """Filter, sort and page one entity for one tenant.

    Column names are whitelisted against COLUMNS and never interpolated from
    caller input; values travel as bound parameters.
    """
    cols = _columns(entity)
    where: List[str] = []
    params: List[Any] = []
    if tenant_id is not None:
        where.append("tenant_id = ?")
        params.append(tenant_id)
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
        total_row = _fetchone(
            conn, f"SELECT COUNT(*) AS n FROM {entity}{clause}", params
        )
        rows = _fetchall(
            conn,
            f"SELECT * FROM {entity}{clause} ORDER BY {column} "
            f"{direction.upper()} LIMIT ? OFFSET ?",
            [*params, limit, offset],
        )
        return {
            "ok": True,
            "entity": entity,
            "items": rows,
            "total": int((total_row or {}).get("n") or 0),
            "limit": limit,
            "offset": offset,
        }
    finally:
        conn.close()


def update(
    entity: str, record_id: int, record: Dict[str, Any], tenant_id: str
) -> Optional[Dict[str, Any]]:
    """Overwrite a persisted row. None when the id is not this tenant's."""
    cols = _columns(entity)
    assignments = ", ".join(f"{c} = ?" for c in cols)
    values = [record.get(name) for name in cols]
    conn = connect()
    try:
        cur = conn.execute(
            _sql(f"UPDATE {entity} SET {assignments} WHERE id = ? AND tenant_id = ?"),
            tuple([*values, record_id, tenant_id]),
        )
        conn.commit()
        changed = getattr(cur, "rowcount", None)
        if changed == 0:
            return None
    finally:
        conn.close()
    return get(entity, record_id, tenant_id)


def delete(entity: str, record_id: int, tenant_id: str) -> bool:
    """Delete this tenant's row. True when a row was removed."""
    _columns(entity)
    conn = connect()
    try:
        cur = conn.execute(
            _sql(f"DELETE FROM {entity} WHERE id = ? AND tenant_id = ?"),
            (record_id, tenant_id),
        )
        conn.commit()
        return bool(getattr(cur, "rowcount", 0))
    finally:
        conn.close()


def health() -> Dict[str, Any]:
    """One round trip against the configured backend, for /health."""
    conn = connect()
    try:
        row = _fetchone(conn, "SELECT 1 AS ok", [])
        return {"ok": True, "backend": backend_name(), "probe": row}
    finally:
        conn.close()
