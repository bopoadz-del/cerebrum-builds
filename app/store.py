"""SQLite persist rooted at STORAGE_PATH. Schema is versioned — connect() never builds tables."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.schema import SPECS

COLUMNS: Dict[str, List[str]] = {
    spec["entity"]: ["id", "reference", "status", "payload_json"] for spec in SPECS.values()
}

SQLITE_BUSY_TIMEOUT_MS = 5000
FASTAPI_SYNC_THREADPOOL = 40

_local = threading.local()


def storage_root() -> Path:
    root = Path(os.environ.get("STORAGE_PATH") or "./data").resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def db_path() -> Path:
    return Path(os.environ.get("STORAGE_PATH") or "./data").resolve() / "platform.db"


def connect() -> sqlite3.Connection:
    path_obj = db_path()
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path_obj), check_same_thread=False)
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
    body["id"] = row["id"]
    body.setdefault("reference", row["reference"])
    body.setdefault("status", row["status"])
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
        cur = conn.execute(
            f"INSERT INTO {entity} (reference, status, payload_json) VALUES (?, ?, ?)",
            (record["reference"], record["status"], record["payload_json"]),
        )
        conn.commit()
        row_id = cur.lastrowid
    finally:
        conn.close()
    return {**payload, "id": row_id, "entity": entity}


def get(entity: str, item_id: Any) -> Optional[Dict[str, Any]]:
    if entity not in COLUMNS:
        raise ValueError(f"unknown entity: {entity}")
    conn = connect()
    try:
        row = conn.execute(
            f"SELECT id, reference, status, payload_json FROM {entity} WHERE id = ?",
            (item_id,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return _row_body(row)


def update(entity: str, item_id: Any, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if entity not in COLUMNS:
        raise ValueError(f"unknown entity: {entity}")
    existing = get(entity, item_id)
    if existing is None:
        return None
    merged = {**existing, **payload, "id": existing["id"]}
    conn = connect()
    try:
        conn.execute(
            f"UPDATE {entity} SET reference = ?, status = ?, payload_json = ? WHERE id = ?",
            (
                str(merged.get("reference", "")),
                str(merged.get("status", "open")),
                json.dumps(merged, default=str),
                item_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return get(entity, item_id)


def delete(entity: str, item_id: Any) -> bool:
    if entity not in COLUMNS:
        raise ValueError(f"unknown entity: {entity}")
    conn = connect()
    try:
        cur = conn.execute(f"DELETE FROM {entity} WHERE id = ?", (item_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def list_all(entity: str) -> List[Dict[str, Any]]:
    if entity not in COLUMNS:
        raise ValueError(f"unknown entity: {entity}")
    conn = connect()
    try:
        rows = conn.execute(
            f"SELECT id, reference, status, payload_json FROM {entity} ORDER BY id"
        ).fetchall()
    finally:
        conn.close()
    return [_row_body(row) for row in rows]
