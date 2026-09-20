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

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Tuple

TABLES: Tuple[str, ...] = ('job_and_site_tracking', 'commercials_and_valuations', 'document_qa_and_indexing', 'safety_and_compliance', 'progress_cost_dashboard', 'automation_reminders_escalation', 'audit_and_access_control', 'team_notifications', 'rag_chunks', 'work_queue', 'idempotency')
COLUMNS: Dict[str, List[str]] = {'job_and_site_tracking': ['reference', 'status', 'job_code', 'job_name', 'site_name', 'client_name', 'work_front', 'contract_value_aed', 'progress_percent', 'milestone', 'milestone_due_date', 'snag_open_count', 'variation_reference', 'variation_status', 'notes'], 'commercials_and_valuations': ['reference', 'status', 'valuation_number', 'job_code', 'boq_item', 'measured_quantity', 'unit_rate_aed', 'gross_value_aed', 'retention_percent', 'retention_aed', 'vat_rate_percent', 'vat_amount_aed', 'certified_value_aed', 'payment_status', 'purchase_order', 'po_party_type', 'amount_due_aed', 'due_on', 'notes'], 'document_qa_and_indexing': ['reference', 'status', 'document_title', 'document_type', 'job_code', 'revision', 'file_name', 'file_path', 'file_sha256', 'question', 'answer', 'source_reference', 'indexed_at', 'notes'], 'safety_and_compliance': ['reference', 'status', 'job_code', 'document_title', 'method_statement_ref', 'work_front', 'checklist_item', 'checklist_state', 'readiness_gate', 'incident_type', 'incident_date', 'severity', 'action_taken', 'notes'], 'progress_cost_dashboard': ['reference', 'status', 'report_date', 'job_code', 'progress_percent', 'certified_value_aed', 'cost_to_date_aed', 'variations_pending', 'snags_open', 'payments_due_aed', 'margin_percent', 'summary'], 'automation_reminders_escalation': ['reference', 'status', 'job_code', 'reminder_type', 'due_date', 'threshold_count', 'actual_count', 'escalation_state', 'channel', 'recipient_email', 'message_body', 'schedule', 'summary'], 'audit_and_access_control': ['reference', 'status', 'actor_name', 'actor_role', 'action_type', 'entity_name', 'entity_reference', 'change_summary', 'approval_state', 'occurred_at', 'notes'], 'team_notifications': ['reference', 'status', 'recipient_email', 'recipient_role', 'channel', 'subject', 'message_body', 'notification_type', 'related_reference', 'send_at', 'delivery_state']}
#: Tenant a read resolves to when no principal was presented (app/auth.py).
DEFAULT_TENANT = "local"

SQLITE_BUSY_TIMEOUT_MS = 30000
SQLITE_CONNECT_TIMEOUT_S = 30.0
FASTAPI_SYNC_THREADPOOL = 40


EXTRAS_TABLE = "record_extras"


def _encode_extra(value: Any) -> str:
    return json.dumps(value, default=str)


def _decode_extra(text: Any) -> Any:
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return text


def _write_extras(
    conn: sqlite3.Connection,
    entity: str,
    record_id: int,
    tenant_id: str,
    record: Dict[str, Any],
) -> None:
    """Persist keys the entity does not declare, so get() can return them."""
    known = set(COLUMNS[entity]) | {"id", "tenant_id"}
    for key, value in (record or {}).items():
        if key in known:
            continue
        conn.execute(
            f"INSERT INTO {EXTRAS_TABLE} (entity, tenant_id, record_id, key, value)"
            " VALUES (?, ?, ?, ?, ?)",
            (entity, tenant_id, record_id, str(key), _encode_extra(value)),
        )


def _extras_map(
    conn: sqlite3.Connection, entity: str, tenant_id: str, ids: List[int]
) -> Dict[int, Dict[str, Any]]:
    if not ids:
        return {}
    marks = ", ".join("?" for _ in ids)
    rows = conn.execute(
        f"SELECT record_id, key, value FROM {EXTRAS_TABLE}"
        f" WHERE entity = ? AND tenant_id = ? AND record_id IN ({marks})",
        [entity, tenant_id, *ids],
    ).fetchall()
    out: Dict[int, Dict[str, Any]] = {}
    for row in rows:
        out.setdefault(int(row["record_id"]), {})[str(row["key"])] = _decode_extra(row["value"])
    return out


def _attach_extras(
    conn: sqlite3.Connection, entity: str, tenant_id: str, rows: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    ids = [int(r["id"]) for r in rows if r.get("id") is not None]
    extras = _extras_map(conn, entity, tenant_id, ids)
    for row in rows:
        extra = extras.get(int(row["id"])) if row.get("id") is not None else None
        if extra:
            row.update(extra)
    return rows


def _has_extras_table(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (EXTRAS_TABLE,),
    ).fetchone()
    return row is not None


def db_path() -> Path:
    root = Path(os.getenv("STORAGE_PATH", "./data"))
    root.mkdir(parents=True, exist_ok=True)
    return root / "platform.db"


def connect() -> sqlite3.Connection:
    """Open the file. Does not create domain tables."""
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
        saved_id = int(cur.lastrowid)
        extra: Dict[str, Any] = {}
        if _has_extras_table(conn):
            _write_extras(conn, entity, saved_id, tenant_id, record)
            extra = _extras_map(conn, entity, tenant_id, [saved_id]).get(saved_id, {})
        conn.commit()
        return {
            "id": saved_id,
            "tenant_id": tenant_id,
            **{c: record.get(c) for c in cols},
            **extra,
        }
    finally:
        conn.close()


def list_all(entity: str, tenant_id: str = DEFAULT_TENANT) -> List[Dict[str, Any]]:
    """Every row one tenant owns.

    ``tenant_id`` defaults to the platform's own tenant (``local``) so a
    read that carries no principal still resolves to a *named* tenant
    rather than to "all tenants". Writes never default: ``save``/
    ``update``/``delete`` require the tenant the authenticated principal
    resolved to, and app/store.py scopes every row it touches.
    """
    conn = connect()
    try:
        rows = conn.execute(f"SELECT * FROM {entity} WHERE tenant_id = ? ORDER BY id", (tenant_id,)).fetchall()
        out = [dict(r) for r in rows]
        if _has_extras_table(conn):
            _attach_extras(conn, entity, tenant_id, out)
        return out
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
        items = [dict(r) for r in rows]
        if _has_extras_table(conn):
            _attach_extras(conn, entity, tenant_id, items)
        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    finally:
        conn.close()


def get(entity: str, record_id: int, tenant_id: str = DEFAULT_TENANT) -> Dict[str, Any] | None:
    """One row by id, scoped to ``tenant_id`` (defaults to the platform tenant)."""
    conn = connect()
    try:
        row = conn.execute(
            f"SELECT * FROM {entity} WHERE id = ? AND tenant_id = ?", (record_id, tenant_id)
        ).fetchone()
        if not row:
            return None
        out = dict(row)
        if _has_extras_table(conn):
            out.update(_extras_map(conn, entity, tenant_id, [int(out["id"])]).get(int(out["id"]), {}))
        return out
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
        if cur.rowcount and _has_extras_table(conn):
            conn.execute(
                f"DELETE FROM {EXTRAS_TABLE} WHERE entity = ? AND tenant_id = ? AND record_id = ?",
                (entity, tenant_id, record_id),
            )
            _write_extras(conn, entity, record_id, tenant_id, record)
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
        if cur.rowcount and _has_extras_table(conn):
            conn.execute(
                f"DELETE FROM {EXTRAS_TABLE} WHERE entity = ? AND tenant_id = ? AND record_id = ?",
                (entity, tenant_id, record_id),
            )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()
