"""productivity_core — GENERATE notes kernel. No Store block ids."""

from __future__ import annotations

from typing import Any, Dict

from app.domain import normalize_note
from app.persist import ok_envelope

# READS: caller.input
# WRITES: caller.output, database.sql
# NEVER: (none)

BLOCK_IDS: list[str] = []
CAPABILITY_ID = "productivity_core"


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Save a note (title + body) and persist it to the productivity_core entity."""
    record = normalize_note(payload if isinstance(payload, dict) else {})
    record["capability"] = CAPABILITY_ID
    return ok_envelope(CAPABILITY_ID, record, {})
