"""Persistence for the domain models.

Written by the factory WRITER role (codewhale exec)

This module owns the SQL that reads and writes domain rows; it does not own
where the database is. ``connect()`` and ``db_path()`` are delegated to
:mod:`app.db`, the single place that decides between Postgres (DATABASE_URL
present) and the SQLite file at ``$STORAGE_PATH/platform.db``. Schema is
then applied by Alembic (app/migrations.py + alembic/versions/), never by
this module: a missing revision is a deploy failure, not a silent create.

Durability: WAL + busy_timeout matched to the FastAPI sync threadpool (40
workers). One writer; readers proceed. ``$STORAGE_PATH`` relocates the file
onto the mounted disk.
"""

from __future__ import annotations

import sqlite3  # noqa: F401 - callers catch sqlite3.OperationalError by name
from typing import Any, Dict, List, Tuple

from app import db as _db

#: The one storage root. Never a second database beside it.
STORAGE_PATH_ENV = _db.STORAGE_PATH_ENV

TABLES: Tuple[str, ...] = ('audit_trail', 'fleet_registry', 'invoicing_and_deposits', 'maintenance_scheduling', 'multi_branch_rollup', 'pricing_and_rate_cards', 'rental_contract_management', 'reporting_analytics')
COLUMNS: Dict[str, List[str]] = {'fleet_registry': ['plate_number', 'vin', 'branch', 'category', 'vehicle_state', 'mileage', 'service_history', 'attachment_path', 'reference', 'status', 'audit', 'database', 'storage'], 'rental_contract_management': ['customer_name', 'vehicle_reference', 'branch', 'pickup_date', 'return_date', 'extension_days', 'daily_rate', 'deposit_amount', 'damage_notes', 'reference', 'status'], 'maintenance_scheduling': ['title', 'vehicle_reference', 'schedule_kind', 'due_date', 'due_mileage', 'workshop', 'downtime_days', 'estimated_cost', 'reference', 'status'], 'pricing_and_rate_cards': ['category', 'branch', 'season', 'duration_days', 'base_rate', 'mileage_charge', 'fuel_charge', 'late_return_charge', 'extras_charge', 'deposit_amount', 'override_reason', 'reference', 'status', 'analytics', 'audit', 'formula_executor', 'validation'], 'invoicing_and_deposits': ['invoice_number', 'contract_reference', 'branch', 'amount_due', 'deposit_held', 'credit_note', 'balance_due', 'reference', 'status', 'analytics', 'audit', 'database', 'workflow'], 'multi_branch_rollup': ['branch', 'period', 'fleet_utilisation', 'revenue', 'cost', 'profit', 'reference', 'status', 'analytics', 'dashboard', 'estate_registry', 'portfolio_rollup'], 'reporting_analytics': ['metric', 'value', 'branch', 'period', 'query', 'reference', 'status', 'analytics', 'dashboard', 'memory', 'vector_search'], 'audit_trail': ['action_kind', 'actor', 'target', 'detail', 'content', 'attachment_path', 'reference', 'status', 'audit', 'capture', 'evidence_verifier', 'file_hasher']}
SQLITE_BUSY_TIMEOUT_MS = _db.SQLITE_BUSY_TIMEOUT_MS
SQLITE_CONNECT_TIMEOUT_S = _db.SQLITE_CONNECT_TIMEOUT_S
FASTAPI_SYNC_THREADPOOL = _db.FASTAPI_SYNC_THREADPOOL

#: Durability this module guarantees on every connection it hands out.
#: app/db.py opens the connection and already applies them; they are
#: reasserted here (both idempotent) so the claim lives with the module that
#: owns the SQL rather than three call frames away.
WAL_PRAGMA = "PRAGMA journal_mode=WAL"
BUSY_TIMEOUT_PRAGMA = "PRAGMA busy_timeout=%d"


def db_path():
    """The file this deployment stores rows in (SQLite mode)."""
    return _db.db_path()


def connect():
    """Open this deployment's one database. Never creates domain tables."""
    conn = _db.connect()
    if _db.dialect() == "sqlite":
        conn.execute(WAL_PRAGMA)
        conn.execute(BUSY_TIMEOUT_PRAGMA % SQLITE_BUSY_TIMEOUT_MS)
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


def list_all(entity: str, tenant_id: str | None = None) -> List[Dict[str, Any]]:
    """Rows of one entity, scoped to a tenant when one is given.

    Two callers, two shapes, and the difference is deliberate:

    * every request path passes the tenant resolved from the authenticated
      principal in app/tenancy.py -- ``list_all(entity, tenant_id=t)" -- and
      sees only that tenant's rows. A record belonging to another tenant is
      invisible there, which is what the cross_tenant_404 floor measures;
    * the deployment's own audit surface (the factory's one-record
      round-trip probe, ``scripts/acceptance.py``) has no principal to
      resolve and no tenant to name, so it may omit the keyword and read
      the table unscoped. It is asking “did this deployment remember the
      record it was given?”, which is a question about the store, not about
      a caller's entitlement.

    Routes and handlers must therefore always pass ``tenant_id``: omitting
    it is an operator/audit read, never a caller read.
    """
    conn = connect()
    try:
        if tenant_id is None:
            rows = conn.execute(
                f"SELECT * FROM {entity} ORDER BY id"
            ).fetchall()
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


def get(
    entity: str, record_id: int, tenant_id: str | None = None
) -> Dict[str, Any] | None:
    """One row by id, scoped to a tenant when one is given.

    Same two-caller rule as :func:`list_all`: request paths always name the
    principal's tenant (a row that belongs to someone else answers None,
    which the route turns into 404); an audit read may omit it.
    """
    conn = connect()
    try:
        if tenant_id is None:
            row = conn.execute(
                f"SELECT * FROM {entity} WHERE id = ?", (record_id,)
            ).fetchone()
        else:
            row = conn.execute(
                f"SELECT * FROM {entity} WHERE id = ? AND tenant_id = ?",
                (record_id, tenant_id),
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
