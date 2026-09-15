"""productivity_core — GENERATE notes kernel (no Store block ids)."""

from __future__ import annotations

from typing import Any, Dict

from app.domain import compose_note, envelope_status
from app.persist import ok_envelope

# READS: caller.input, database.sql
# WRITES: caller.output, database.sql
# NEVER: (none)

BLOCK_IDS: list[str] = []
CAPABILITY_ID = "productivity_core"


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Save a note (title + body), derive kernel scalars, persist to alembic entity."""
    status = envelope_status(payload)
    note = compose_note(payload)
    record = {
        **payload,
        "status": status,
        "title": note["title"],
        "body": note["body"],
        "title_norm": note["title_norm"],
        "word_count": note["word_count"],
        "preview": note["preview"],
        "note_kind": note["note_kind"],
        "search_blob": note["search_blob"],
        "capability": CAPABILITY_ID,
        "channel": "mcp",
    }
    record["note"] = {
        "title": note["title"],
        "body": note["body"],
        "word_count": note["word_count"],
        "preview": note["preview"],
        "note_kind": note["note_kind"],
        "allowed_next_status": note["allowed_next_status"],
    }
    return ok_envelope(CAPABILITY_ID, record, {})
