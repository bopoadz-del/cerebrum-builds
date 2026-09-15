"""productivity_core — GENERATE notes kernel (no Store block ids)."""

from __future__ import annotations

from typing import Any, Dict

from app.domain import allowed_next_status, envelope_status, note_summary, preview, word_count
from app.persist import ok_envelope

# READS: caller.input
# WRITES: caller.output, database.sql
# NEVER: (none)

BLOCK_IDS: list[str] = []
CAPABILITY_ID = "productivity_core"


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Save a note with title and body, then persist it to productivity_core."""
    status = envelope_status(payload)
    title = str(payload.get("title") or payload.get("reference") or "sample")
    body = str(payload.get("body") or "")
    words = word_count(title, body)
    record = {
        **payload,
        "status": status,
        "title": title,
        "body": body,
        "word_count": words,
        "char_count": len(title) + len(body),
        "preview": preview(body or title),
        "summary": note_summary(title, body, status),
        "capability": CAPABILITY_ID,
        "channel": "mcp",
        "note": {
            "title": title,
            "body": body,
            "word_count": words,
            "preview": preview(body or title),
            "allowed_next_status": list(allowed_next_status(status)),
        },
    }
    return ok_envelope(CAPABILITY_ID, record, {})
