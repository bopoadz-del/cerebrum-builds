"""Lifecycle audit: one row per accepted write, in the platform's own table."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app import store


def record(event: str, *, subject: Optional[str] = None,
           detail: Optional[Any] = None, tenant_id: str = "local") -> Dict[str, Any]:
    payload = json.dumps(detail, sort_keys=True, default=str) if detail is not None else None
    conn = store.connect()
    try:
        cur = conn.execute(
            "INSERT INTO lifecycle_audit (tenant_id, event, subject, detail, recorded_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (tenant_id, event, subject, payload, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        return {"id": cur.lastrowid, "event": event, "subject": subject}
    finally:
        conn.close()


def entries(tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = store.connect()
    try:
        if tenant_id:
            rows = conn.execute(
                "SELECT * FROM lifecycle_audit WHERE tenant_id = ? ORDER BY id",
                (tenant_id,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM lifecycle_audit ORDER BY id").fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
