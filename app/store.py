"""SQLite persist rooted at STORAGE_PATH. Tables come from alembic, not connect()."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.schema import SPECS

COLUMNS: Dict[str, List[str]] = {
    spec["entity"]: ["reference", "status", "payload_json"] for spec in SPECS.values()
}
COLUMNS["lifecycle_audit"] = ["reference", "status", "payload_json"]

FASTAPI_SYNC_THREADPOOL = 8
SQLITE_BUSY_TIMEOUT_MS = 5000

_local = threading.local()
_write_lock = threading.Lock()


def storage_root() -> Path:
    root = Path(os.environ.get("STORAGE_PATH") or "./data").resolve()
    if root.exists() and not root.is_dir():
        raise OSError(f"STORAGE_PATH is not a directory: {root}")
    root.mkdir(parents=True, exist_ok=True)
    return root


def db_path() -> Path:
    return Path(os.environ.get("STORAGE_PATH") or "./data").resolve() / "platform.db"


def connect() -> sqlite3.Connection:
    path = db_path()
    parent = path.parent
    if parent.exists() and not parent.is_dir():
        raise OSError(f"STORAGE_PATH is not a directory: {parent}")
    if not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")
    return conn


def _cached() -> sqlite3.Connection:
    conn = getattr(_local, "conn", None)
    path = str(db_path())
    if conn is None or getattr(_local, "path", None) != path:
        if conn is not None:
            try:
                conn.close()
            except sqlite3.Error:
                pass
        conn = connect()
        _local.conn = conn
        _local.path = path
    return conn


def reset_connection() -> None:
    conn = getattr(_local, "conn", None)
    if conn is not None:
        try:
            conn.close()
        except sqlite3.Error:
            pass
    _local.conn = None
    _local.path = None


def _row_to_record(row: sqlite3.Row) -> Dict[str, Any]:
    try:
        body = json.loads(row["payload_json"] or "{}")
    except json.JSONDecodeError:
        body = {}
    if not isinstance(body, dict):
        body = {"value": body}
    body.setdefault("reference", row["reference"])
    body.setdefault("status", row["status"])
    body["id"] = row["pk"]
    return body


def save(entity: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if entity not in COLUMNS:
        raise ValueError(f"unknown entity: {entity}")
    record = {
        "reference": str(payload.get("reference", "")),
        "status": str(payload.get("status", "open")),
        "payload_json": json.dumps(payload, default=str),
    }
    with _write_lock:
        conn = _cached()
        cur = conn.cursor()
        cur.execute(
            f"INSERT INTO {entity} (reference, status, payload_json) VALUES (?, ?, ?)",
            (record["reference"], record["status"], record["payload_json"]),
        )
        pk = int(cur.lastrowid)
        saved = {**payload, "id": pk, "entity": entity}
        cur.execute(
            f"UPDATE {entity} SET payload_json = ? WHERE pk = ?",
            (json.dumps(saved, default=str), pk),
        )
        conn.commit()
    return saved


def list_all(entity: str) -> List[Dict[str, Any]]:
    if entity not in COLUMNS:
        raise ValueError(f"unknown entity: {entity}")
    conn = _cached()
    cur = conn.cursor()
    cur.execute(f"SELECT pk, reference, status, payload_json FROM {entity} ORDER BY pk")
    return [_row_to_record(row) for row in cur.fetchall()]


def get(entity: str, item_id: Any) -> Optional[Dict[str, Any]]:
    if entity not in COLUMNS:
        raise ValueError(f"unknown entity: {entity}")
    try:
        pk = int(item_id)
    except (TypeError, ValueError):
        return None
    conn = _cached()
    cur = conn.cursor()
    cur.execute(
        f"SELECT pk, reference, status, payload_json FROM {entity} WHERE pk = ?",
        (pk,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return _row_to_record(row)


def delete(entity: str, item_id: Any) -> bool:
    if entity not in COLUMNS:
        raise ValueError(f"unknown entity: {entity}")
    try:
        pk = int(item_id)
    except (TypeError, ValueError):
        return False
    with _write_lock:
        conn = _cached()
        cur = conn.cursor()
        cur.execute(f"DELETE FROM {entity} WHERE pk = ?", (pk,))
        conn.commit()
        return cur.rowcount > 0
