"""Alert outbox for capabilities whose vendored alerting block is unusable.

Written by the factory WRITER role (codewhale exec)

Two blocks in this checkout cannot run, and neither is stubbed around:

* ``notification`` -- ``vendor/cerebrum/blocks/notification.py`` does not
  parse (``IndentationError`` at line 231), so the Store notify slice cannot
  be imported at all;
* ``document_engine`` -- the vendored slice loads a module file
  (``vendor/cerebrum/blocks/document_engine_block.py``) the CLONER wrote as a
  package, and the offline checkout carries no PDF parser either.

See ``docs/blockers.json`` -- both are named, probed by ``app/vendor_health``
and reported on ``/health``. What a capability still owes the operator is the
*record* of the alert, so this module writes one row per alert into
``notification_outbox`` (created by the v2 revision): the intent, the payload
and the reason the block was unavailable. It never claims a message was
delivered.

Scope
-----
READS  ``STORAGE_PATH`` (where the platform database lives).
WRITES exactly ONE row per call in ``notification_outbox``.
NEVER  network, SMTP, HTTP store callbacks, ``vendor/**``.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.store import connect

CHANNEL = "mcp"
BLOCK_ID = "notification"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def record_alert(
    *,
    capability: str,
    topic: str,
    message: str,
    payload: Optional[Dict[str, Any]] = None,
    block_status: str = "unavailable",
    connection: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """Record one alert in the outbox. Returns the stored row.

    ``block_status`` is always an honest statement about the Store notify
    block: ``unavailable`` when its vendored slice cannot be imported, or
    ``refused`` when it ran and refused. ``delivered`` is therefore False
    unless a caller passes an explicit status for a block that really ran.
    """
    row = {
        "capability": str(capability),
        "topic": str(topic),
        "channel": CHANNEL,
        "message": str(message)[:2000],
        "payload": json.dumps(payload or {}, default=str)[:4000],
        "block_id": BLOCK_ID,
        "block_status": str(block_status),
        "created_at": _now(),
    }
    own = connection is None
    conn = connection or connect()
    try:
        cur = conn.execute(
            "INSERT INTO notification_outbox "
            "(capability, topic, channel, message, payload, block_id, block_status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                row["capability"],
                row["topic"],
                row["channel"],
                row["message"],
                row["payload"],
                row["block_id"],
                row["block_status"],
                row["created_at"],
            ),
        )
        if own:
            conn.commit()
        return {
            "id": cur.lastrowid,
            "queued": True,
            "delivered": False,
            "channel": CHANNEL,
            "block": BLOCK_ID,
            "block_status": row["block_status"],
            "topic": row["topic"],
            "created_at": row["created_at"],
        }
    finally:
        if own:
            conn.close()


def list_alerts(limit: int = 50) -> Dict[str, Any]:
    """Read the outbox back (the operator's evidence trail)."""
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT * FROM notification_outbox ORDER BY id DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
        return {"items": [dict(r) for r in rows], "total": len(rows)}
    finally:
        conn.close()
