"""SQLite persist rooted at STORAGE_PATH. Tables match spec.entity / alembic 0001."""

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

FASTAPI_SYNC_THREADPOOL = 40
SQLITE_BUSY_TIMEOUT_MS = 5000

_local = threading.local()


def storage_path() -> Path:
    """Configured root. Does not create the directory."""
    return Path(os.environ.get("STORAGE_PATH") or "./data").resolve()


def storage_root() -> Path:
    root = storage_path()
    if root.exists() and not root.is_dir():
        raise OSError(f"STORAGE_PATH is not a directory: {root}")
    root.mkdir(parents=True, exist_ok=True)
    return root


def db_path() -> Path:
    return storage_path() / "platform.db"


def connect() -> sqlite3.Connection:
    path = db_path()
    if path.parent.exists() and not path.parent.is_dir():
        raise OSError(f"STORAGE_PATH is not a directory: {path.parent}")
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")
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


def _row_body(row: sqlite3.Row) -> Dict[str, Any]:
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
    conn = connect()
    try:
        cur = conn.cursor()
        cur.execute(
            f"INSERT INTO {entity} (reference, status, payload_json) VALUES (?, ?, ?)",
            (record["reference"], record["status"], record["payload_json"]),
        )
        pk = int(cur.lastrowid)
        stored = {**payload, "id": pk, "entity": entity}
        cur.execute(
            f"UPDATE {entity} SET payload_json = ? WHERE pk = ?",
            (json.dumps(stored, default=str), pk),
        )
        conn.commit()
        return stored
    finally:
        conn.close()


def get(entity: str, item_id: Any) -> Optional[Dict[str, Any]]:
    if entity not in COLUMNS:
        raise ValueError(f"unknown entity: {entity}")
    try:
        pk = int(item_id)
    except (TypeError, ValueError):
        return None
    conn = connect()
    try:
        cur = conn.cursor()
        cur.execute(
            f"SELECT pk, reference, status, payload_json FROM {entity} WHERE pk = ?",
            (pk,),
        )
        row = cur.fetchone()
        return _row_body(row) if row is not None else None
    except sqlite3.OperationalError:
        return None
    finally:
        conn.close()


def update(entity: str, item_id: Any, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    existing = get(entity, item_id)
    if existing is None:
        return None
    merged = {**existing, **payload, "id": existing["id"], "entity": entity}
    conn = connect()
    try:
        cur = conn.cursor()
        cur.execute(
            f"UPDATE {entity} SET reference = ?, status = ?, payload_json = ? WHERE pk = ?",
            (
                str(merged.get("reference", "")),
                str(merged.get("status", "open")),
                json.dumps(merged, default=str),
                int(existing["id"]),
            ),
        )
        conn.commit()
        return merged
    finally:
        conn.close()


def delete(entity: str, item_id: Any) -> bool:
    if entity not in COLUMNS:
        raise ValueError(f"unknown entity: {entity}")
    try:
        pk = int(item_id)
    except (TypeError, ValueError):
        return False
    conn = connect()
    try:
        cur = conn.cursor()
        cur.execute(f"DELETE FROM {entity} WHERE pk = ?", (pk,))
        conn.commit()
        return cur.rowcount > 0
    except sqlite3.OperationalError:
        return False
    finally:
        conn.close()


def list_all(entity: str) -> List[Dict[str, Any]]:
    if entity not in COLUMNS:
        raise ValueError(f"unknown entity: {entity}")
    conn = connect()
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT pk, reference, status, payload_json FROM {entity} ORDER BY pk")
        return [_row_body(row) for row in cur.fetchall()]
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()
