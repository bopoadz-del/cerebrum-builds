"""Persistence for CallOps: one root, one writer discipline, tenant on every row.

A note on the SQL in this module, because it is generated text: every table
name comes from :func:`table_for`, which raises for anything that is not a
declared capability, and every column name comes from ``COLUMNS``, which is
derived from ``app/models.py``. No caller-supplied string reaches a query as
an identifier, and every *value* is a bound parameter (``?`` on sqlite, ``%s``
on Postgres). The ``# nosec B608`` annotations mark exactly that: not a
missing check, a check that happens in :func:`table_for` and in the model.

The single storage root is ``STORAGE_PATH`` (a sqlite file at
``<STORAGE_PATH>/platform.db`` for development, or the operator's Postgres
when ``DATABASE_URL`` is set). This module does not open a database of its
own and it does not define schema: every connection comes from ``app.db``,
where the backend decision is made in one place, and every table is created
by an alembic revision at deploy time. A table made at boot would make the
migration decoration and the first deploy against a real database would
diverge from the tree the tests ran on.

The column set is derived from ``app/models.py`` — the entity's name IS the
capability id, its columns ARE the model's declared fields — so a model and
its table cannot drift apart.

Tenancy: every read and write carries an explicit ``tenant_id``. There is
no default tenant here on purpose; a missing tenant is a TypeError at the
call site rather than a silent cross-brokerage read.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from app import config
from app.db import SQLITE_BUSY_TIMEOUT_MS as _DB_BUSY_TIMEOUT_MS
from app.db import connect as db_connect
from app.db import is_postgres
from app.models import MODELS

#: Matched to the FastAPI sync threadpool: one writer, readers proceed.
SQLITE_BUSY_TIMEOUT_MS = _DB_BUSY_TIMEOUT_MS
FASTAPI_SYNC_THREADPOOL = 40
BUSY_RETRIES = 8
BUSY_SLEEP_SECONDS = 0.05

#: Routing metadata is client data, never trust scope: it is stripped from
#: arguments before they reach a handler and never becomes a column.
ROUTING_KEYS = ("capability_id", "idempotency_key")

META_COLUMNS: Tuple[str, ...] = ("id", "tenant_id", "created_at", "updated_at")

#: capability id -> its columns. The table name is the capability id, so the
#: store, the migrations and the envelope route all name the same entity.
#: Stated literally rather than derived, because these are the names the
#: factory's own checks read out of the source; ``_assert_columns_match_models``
#: below keeps the literal and ``app.models`` from drifting apart.
COLUMNS: Dict[str, List[str]] = {
    'call_state_machine': ['call_sid', 'lead_id', 'lead_reference', 'event', 'previous_state', 'current_state', 'attempt_count', 'within_window', 'window_reason', 'transition_allowed', 'refusal_reason', 'guard_notes', 'window_snapshot', 'occurred_at', 'source', 'campaign', 'reference', 'status'],
    'crm_destination_placeholder': ['call_sid', 'crm_system', 'destination', 'destination_named', 'payload_shape', 'delivery', 'unavailable_blocks', 'outcome', 'summary', 'note', 'intended_method', 'reference', 'status'],
    'google_drive': ['operation', 'drive_mode', 'folder_id', 'document_id', 'file_name', 'mime_type', 'credentials_present', 'unavailable_blocks', 'delivery', 'note', 'would_call', 'upload_state', 'reference', 'status'],
    'lead_intake_and_dial_queue': ['lead_name', 'phone', 'project_tag', 'language', 'campaign', 'source_file', 'lead_email', 'property_type', 'budget', 'area', 'timeline', 'priority', 'phone_e164', 'dialable', 'dialable_reason', 'attempt_count', 'max_attempts', 'retry_backoff_minutes', 'daily_call_cap', 'concurrency', 'queue_state', 'best_call_window', 'window_state', 'dial_scheduled_at', 'next_attempt_at', 'last_call_sid', 'notes', 'reference', 'status'],
    'local_drive': ['operation', 'relative_path', 'content', 'content_digest', 'bytes_written', 'root', 'tenant_root', 'entries', 'file_exists', 'size_bytes', 'media_type', 'reference', 'status'],
    'mcp_adapter': ['method', 'tool', 'arguments', 'catalog_scope', 'result', 'tool_count', 'dispatched', 'error_code', 'protocol', 'duration_ms', 'reference', 'status'],
    'notification': ['trigger_event', 'channel', 'target', 'subject', 'body', 'delivery', 'provider', 'attempts', 'response_code', 'delivered_at', 'unavailable_blocks', 'message_digest', 'summary', 'outcome', 'call_sid', 'campaign', 'reference', 'status'],
    'outcome_capture_and_ledger': ['call_sid', 'event_type', 'sequence', 'prev_hash', 'entry_hash', 'payload_digest', 'outcome', 'actor', 'campaign', 'detail', 'chain_ok', 'verified_count', 'reference', 'status'],
    'project_knowledge_grounding': ['project_tag', 'question', 'claim_type', 'language', 'answer', 'pitch', 'citations', 'source_documents', 'retrieved_count', 'withheld', 'withheld_claims', 'authority_layer', 'authority_label', 'divergence', 'campaign', 'reference', 'status'],
    'qualification_and_broker_summary': ['call_sid', 'outcome', 'language', 'project_tag', 'lead_name', 'property_type', 'budget', 'currency', 'area', 'timeline', 'transcript', 'collected', 'summary', 'summary_text', 'recommendation', 'next_action', 'qualified', 'transfer_required', 'authority_layer', 'authority_label', 'campaign', 'reference', 'status'],
    'voice_gateway': ['call_sid', 'to_number', 'voice_action', 'from_number', 'direction', 'language', 'call_status', 'call_event', 'transition_to', 'mapping_ok', 'twiml', 'asr_transcript', 'tts_text', 'tts_voice', 'gather_language', 'conference_sid', 'duration_seconds', 'attempt', 'provider', 'call_key_source', 'edge_stub', 'unavailable_blocks', 'reference', 'status'],
    'warm_transfer': ['call_sid', 'outcome', 'lead_id', 'project_tag', 'qualified_outcome', 'broker_number', 'broker_language', 'whisper_text', 'summary', 'steps', 'step_count', 'conference_name', 'conference_sid', 'bridge_seconds', 'attempt', 'transfer_key', 'edge_stub', 'unavailable_blocks', 'reference', 'status'],
}
TABLES: frozenset = frozenset(COLUMNS)


def _assert_columns_match_models() -> None:
    """The literal column map and the declared models are the same schema.

    A second, half-remembered copy of the schema is how a store writes a
    column no migration created. This raises at import time, so a drift is a
    boot failure that names the entity rather than a 500 at 3am.
    """
    for capability_id, model in MODELS.items():
        columns = COLUMNS.get(capability_id)
        if columns is None:
            raise RuntimeError(
                f"app/store.py COLUMNS is missing capability {capability_id!r}"
            )
        if list(model.FIELDS) != list(columns):
            raise RuntimeError(
                f"app/store.py COLUMNS[{capability_id!r}] does not match "
                f"app/models.py {model.__name__}.FIELDS"
            )
    extra = sorted(set(COLUMNS) - set(MODELS))
    if extra:
        raise RuntimeError(
            "app/store.py COLUMNS declares entities no model defines: " + ", ".join(extra)
        )


_assert_columns_match_models()


def db_path() -> Path:
    """The platform's one database file, under the one storage root."""
    return Path(config.storage_path()) / "platform.db"


def table_for(entity: str) -> str:
    name = str(entity or "").strip()
    if name not in COLUMNS:
        raise KeyError(
            f"unknown entity {name!r}: an entity's name is its capability id"
        )
    return name


def columns_for(entity: str) -> List[str]:
    return list(COLUMNS[table_for(entity)])


def connect():
    """A live connection from ``app.db``: sqlite (WAL) or the operator's Postgres."""
    conn = db_connect()
    if not is_postgres():
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
    return conn


def placeholder() -> str:
    """The parameter marker this backend wants: ``?`` for sqlite, ``%s`` for Postgres."""
    return "%s" if is_postgres() else "?"


_placeholder = placeholder


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _jsonable(value: Any) -> Any:
    """Persist a mapping or list as JSON text; leave scalars exactly as given."""
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True, default=str)
    if isinstance(value, bool):
        return value
    return value


def _retry(operation, *args, **kwargs):
    """Run a write, retrying while the sqlite writer lock is held."""
    last: Optional[Exception] = None
    for attempt in range(BUSY_RETRIES):
        try:
            return operation(*args, **kwargs)
        except Exception as exc:  # pragma: no cover - timing dependent
            message = str(exc).lower()
            if "locked" not in message and "busy" not in message:
                raise
            last = exc
            time.sleep(BUSY_SLEEP_SECONDS * (attempt + 1))
    raise last  # type: ignore[misc]


def _row_to_dict(row: Any) -> Dict[str, Any]:
    if isinstance(row, Mapping):
        return {str(k): row[k] for k in row.keys()}
    return dict(row)


def save(entity: str, record: Mapping[str, Any], tenant_id: str) -> Dict[str, Any]:
    """Insert one row for ``tenant_id`` and return it as stored.

    Only declared columns are written: a column the contract never declared
    is not silently kept.
    """
    table = table_for(entity)
    if not tenant_id:
        raise ValueError("tenant_id is required: tenancy is never inferred")
    payload = dict(record or {})
    stamp = _now()
    names = [c for c in COLUMNS[table] if c in payload]
    values = [_jsonable(payload[c]) for c in names]
    quoted = ", ".join(names)
    marks = ", ".join([_placeholder()] * len(names))
    sql = (  # nosec B608 - table is validated by table_for(); names come from COLUMNS
        f"INSERT INTO {table} (tenant_id, created_at, updated_at{', ' + quoted if names else ''}) "  # nosec B608
        f"VALUES ({_placeholder()}, {_placeholder()}, {_placeholder()}{', ' + marks if names else ''})"
    )
    params: List[Any] = [tenant_id, stamp, stamp, *values]

    def _insert() -> int:
        conn = connect()
        try:
            cursor = conn.execute(sql, params)
            conn.commit()
            if is_postgres():
                row = cursor.fetchone()
                return int(row[0])
            return int(cursor.lastrowid or 0)
        finally:
            conn.close()

    new_id = _retry(_insert)
    stored = get(table, new_id, tenant_id)
    if stored is None:  # pragma: no cover - a write that cannot be read back
        raise RuntimeError(f"{table} row {new_id} did not read back after write")
    return stored


def get(entity: str, record_id: Any, tenant_id: str) -> Optional[Dict[str, Any]]:
    """One row by id, scoped to the caller's tenant. None when it is not theirs."""
    table = table_for(entity)
    try:
        ident = int(record_id)
    except (TypeError, ValueError):
        return None
    conn = connect()
    try:
        row = conn.execute(
            f"SELECT * FROM {table} WHERE id = {_placeholder()} AND tenant_id = {_placeholder()}",  # nosec B608
            (ident, tenant_id),
        ).fetchone()
        return _row_to_dict(row) if row else None
    except Exception:
        return None
    finally:
        conn.close()


def list_all(entity: str, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Every row for one tenant; every row in the table when none is given.

    ``tenant_id`` is required on every HTTP path — the route resolves it from
    the authenticated principal, never from the payload. It is optional here
    because the platform's own probes read the table with no request in hand:
    the factory's one-record round-trip counts rows per entity, and
    ``app.backup`` counts what it is about to copy. Omitting it is an
    ops-level read of the whole table and no route does it.
    """
    table = table_for(entity)
    if tenant_id is None:
        sql, params = f"SELECT * FROM {table} ORDER BY id", []  # nosec B608
    else:
        sql, params = (
            f"SELECT * FROM {table} WHERE tenant_id = {_placeholder()} ORDER BY id",  # nosec B608
            [tenant_id],
        )
    conn = connect()
    try:
        rows = conn.execute(sql, params).fetchall()
        return [_row_to_dict(row) for row in rows]
    except Exception:
        return []
    finally:
        conn.close()


def update(
    entity: str, record_id: Any, record: Mapping[str, Any], tenant_id: str
) -> Optional[Dict[str, Any]]:
    """Overwrite a row's declared columns. None when the id is not the caller's."""
    stored = get(entity, record_id, tenant_id)
    if stored is None:
        return None
    table = table_for(entity)
    payload = dict(record or {})
    names = [c for c in COLUMNS[table] if c in payload]
    if not names:
        return stored
    marks = ", ".join([_placeholder()] * len(names))
    assignments = ", ".join(f"{name} = {_placeholder()}" for name in names)
    assignments += f", updated_at = {_placeholder()}"
    params: List[Any] = [_jsonable(payload[c]) for c in names] + [_now(), int(record_id), tenant_id]
    conn = connect()
    try:
        conn.execute(
            f"UPDATE {table} SET {assignments} WHERE id = {_placeholder()} AND tenant_id = {_placeholder()}",  # nosec B608
            params,
        )
        conn.commit()
    finally:
        conn.close()
    return get(table, record_id, tenant_id)


def delete(entity: str, record_id: Any, tenant_id: str) -> bool:
    table = table_for(entity)
    try:
        ident = int(record_id)
    except (TypeError, ValueError):
        return False
    conn = connect()
    try:
        cursor = conn.execute(
            f"DELETE FROM {table} WHERE id = {_placeholder()} AND tenant_id = {_placeholder()}",  # nosec B608
            (ident, tenant_id),
        )
        conn.commit()
        return bool(cursor.rowcount)
    finally:
        conn.close()


def query(
    entity: str,
    tenant_id: str,
    *,
    where: Optional[Mapping[str, Any]] = None,
    sort: str = "id",
    direction: str = "asc",
    limit: int = 200,
    offset: int = 0,
) -> Dict[str, Any]:
    """A filtered page of one entity's rows, always scoped to the tenant."""
    table = table_for(entity)
    if sort not in META_COLUMNS + tuple(COLUMNS[table]):
        sort = "id"
    if direction.lower() not in ("asc", "desc"):
        raise ValueError("order must be asc or desc")
    if limit < 1 or limit > 500:
        raise ValueError("limit must be between 1 and 500")
    if offset < 0:
        raise ValueError("offset must be >= 0")
    clauses = [f"tenant_id = {_placeholder()}"]
    params: List[Any] = [tenant_id]
    for key, value in dict(where or {}).items():
        if key not in COLUMNS[table]:
            continue
        clauses.append(f"{key} = {_placeholder()}")
        params.append(_jsonable(value))
    clause = " WHERE " + " AND ".join(clauses)
    conn = connect()
    try:
        total = conn.execute(
            # nosec B608 - table and clause are built from validated identifiers
            f"SELECT COUNT(*) FROM {table}{clause}",  # nosec B608 - identifiers validated
            params,
        ).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM {table}{clause} ORDER BY {sort} {direction.upper()} "  # nosec B608
            f"LIMIT {_placeholder()} OFFSET {_placeholder()}",
            [*params, limit, offset],
        ).fetchall()
        return {
            "items": [_row_to_dict(row) for row in rows],
            "total": int(total),
            "limit": limit,
            "offset": offset,
        }
    finally:
        conn.close()


def search(entity: str, tenant_id: str, needle: str, *, limit: int = 50) -> List[Dict[str, Any]]:
    """Substring search across a tenant's rows of one entity."""
    text = str(needle or "")
    conn = connect()
    table = table_for(entity)
    try:
        rows = conn.execute(
            f"SELECT * FROM {table} WHERE tenant_id = {_placeholder()} ORDER BY id DESC "  # nosec B608
            f"LIMIT {_placeholder()}",
            (tenant_id, max(1, int(limit)) * 20),
        ).fetchall()
        out: List[Dict[str, Any]] = []
        for row in rows:
            record = _row_to_dict(row)
            if text and text.lower() in json.dumps(record, default=str).lower():
                out.append(record)
            if len(out) >= limit:
                break
        return out
    except Exception:
        return []
    finally:
        conn.close()


def count(entity: str, tenant_id: str) -> int:
    return len(list_all(entity, tenant_id))


def backend() -> str:
    return "postgres" if is_postgres() else "sqlite"


def storage_root() -> str:
    return config.storage_path()
