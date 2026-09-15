"""productivity_core — GENERATE notes kernel (no block ids)."""

from __future__ import annotations

from typing import Any, Dict

from app.domain import (
    allowed_next_status,
    envelope_status,
    normalize_note,
    note_op,
    search_notes,
)
from app.persist import ok_envelope
from app.schema import get_spec
from app.store import delete as store_delete
from app.store import get as store_get
from app.store import list_all

# READS: caller.input, config.runtime, database.sql
# WRITES: caller.output, database.sql
# NEVER: (none)

CAPABILITY_ID = "productivity_core"
BLOCK_IDS: list[str] = []
ENTITY = get_spec(CAPABILITY_ID)["entity"]


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Save, list, search, or delete a note. Empty payload is a schema-sample create."""
    incoming = dict(payload or {})
    incoming.setdefault("reference", "sample")
    incoming.setdefault("status", envelope_status(incoming))
    incoming.setdefault("title", incoming.get("reference") or "sample")
    incoming.setdefault("body", "sample")
    incoming.setdefault("note_op", "create")
    record = normalize_note(incoming)
    op = note_op(record)

    if op == "search":
        hits = search_notes(list_all(ENTITY), record.get("keyword") or "")
        record["matches"] = hits
        record["match_count"] = len(hits)
        return ok_envelope(CAPABILITY_ID, record, {})

    if op == "delete":
        target = incoming.get("target_id") or incoming.get("note_id")
        removed = False
        if target is not None:
            removed = store_delete(ENTITY, target)
        else:
            rows = [
                row
                for row in list_all(ENTITY)
                if row.get("reference") == record["reference"]
            ]
            if rows:
                removed = store_delete(ENTITY, rows[-1]["id"])
        record["deleted"] = bool(removed)
        return ok_envelope(CAPABILITY_ID, record, {})

    if op == "update":
        target = incoming.get("target_id") or incoming.get("note_id")
        existing = store_get(ENTITY, target) if target is not None else None
        if existing:
            record = normalize_note({**existing, **incoming, "note_op": "update"})
        record["updated"] = existing is not None
        record["allowed_next_status"] = list(allowed_next_status(record["status"]))
        return ok_envelope(CAPABILITY_ID, record, {})

    record["saved"] = True
    return ok_envelope(CAPABILITY_ID, record, {})
