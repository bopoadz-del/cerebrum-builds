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

TABLES: Tuple[str, ...] = ('auto_assignment', 'booking_system_integration', 'complaints_management', 'erp_integration', 'management_dashboards', 'reporting', 'role_based_access', 'workforce_management')
COLUMNS: Dict[str, List[str]] = {'complaints_management': ['reference', 'status', 'school', 'site_code', 'category', 'priority', 'description', 'raised_by', 'raised_by_role', 'contact_email', 'contact_phone', 'logged_by', 'assigned_to', 'assignment_mode', 'reported_at', 'due_at', 'sla_hours', 'closed_at', 'resolution_notes', 'work_order_reference'], 'auto_assignment': ['reference', 'status', 'complaint_reference', 'school', 'category', 'priority', 'required_trade', 'required_skill', 'candidate_count', 'assigned_to', 'assigned_role', 'assignment_mode', 'match_score', 'workload_score', 'queue_position', 'override_reason', 'assigned_at'], 'workforce_management': ['reference', 'status', 'school', 'team_name', 'team_type', 'trade', 'shift', 'headcount', 'lead_name', 'lead_email', 'contact_phone', 'active', 'open_jobs', 'notes'], 'management_dashboards': ['reference', 'status', 'scope', 'school', 'period', 'complaints_open', 'complaints_in_progress', 'complaints_closed', 'jobs_in_progress', 'sla_breaches', 'sla_compliance_pct', 'avg_closure_hours', 'headline', 'generated_at'], 'reporting': ['reference', 'status', 'report_type', 'scope', 'school', 'period_start', 'period_end', 'complaints_total', 'closed_total', 'avg_closure_hours', 'sla_compliance_pct', 'top_category', 'busiest_school', 'recipients', 'generated_at'], 'role_based_access': ['reference', 'status', 'principal', 'principal_email', 'role', 'school', 'access_scope', 'permissions', 'granted_by', 'effective_from', 'last_review_at', 'active', 'notes'], 'erp_integration': ['reference', 'status', 'integration', 'mode', 'entity_type', 'direction', 'external_reference', 'endpoint', 'currency', 'amount', 'sync_state', 'last_sync_at', 'detail', 'notes'], 'booking_system_integration': ['reference', 'status', 'integration', 'mode', 'booking_reference', 'school', 'facility', 'slot_start', 'slot_end', 'requested_by', 'sync_state', 'last_sync_at', 'detail', 'notes']}
SQLITE_BUSY_TIMEOUT_MS = 30000
SQLITE_CONNECT_TIMEOUT_S = 30.0
FASTAPI_SYNC_THREADPOOL = 40


def db_path() -> Path:
    root = Path(os.getenv("STORAGE_PATH", "./data"))
    root.mkdir(parents=True, exist_ok=True)
    return root / "platform.db"


def connect() -> sqlite3.Connection:
    """Open the one persistence root. Does not create domain tables.

    The target is ``<STORAGE_PATH>/platform.db`` -- there is no second
    database in this product, and no module opens its own sqlite file.
    """
    conn = sqlite3.connect(str(db_path()), timeout=SQLITE_CONNECT_TIMEOUT_S, check_same_thread=False, isolation_level="DEFERRED")  # STORAGE_PATH/platform.db
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


def list_all(entity: str, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Rows for one tenant, or for the whole store when no tenant is given.

    Two read scopes, one rule: a read that names its tenant is scoped by
    it (every HTTP route, every operator view) and a read that names none
    is the platform reading its own store -- the factory's one-record
    round-trip, a migration/backup drill, an operator diagnostic run from
    the shell, all of which sit outside any request and therefore have no
    principal to resolve a tenant from. Those callers must not be forced
    to invent one: ``list_all(entity)`` has to answer, and refusing it
    TypeError is how a product that stored a record fine is reported as
    having no readable entity at all.

    The scope is never widened for a caller that HAS a tenant: passing
    one still filters the SELECT, so a tenant can never read another's
    rows through this function.
    """
    conn = connect()
    try:
        if tenant_id is None:
            rows = conn.execute(f"SELECT * FROM {entity} ORDER BY id").fetchall()  # platform-scope read (no principal)
        else:
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


def get(entity: str, record_id: int, tenant_id: Optional[str] = None) -> Dict[str, Any] | None:
    """One row. Same two read scopes as list_all: named tenant filters,
    no tenant is the platform reading its own store (outside any request)."""
    conn = connect()
    try:
        if tenant_id is None:
            row = conn.execute(
                f"SELECT * FROM {entity} WHERE id = ?", (record_id,)
            ).fetchone()
        else:
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
