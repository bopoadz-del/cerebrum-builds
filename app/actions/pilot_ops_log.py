"""pilot_ops_log — REUSE knowledge + memory + storage. Pilot notes and quirks."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import knowledge_input, memory_input, storage_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, env.process, config.runtime, memory.cache, file.local.read
# WRITES: caller.output, memory.cache, file.local.write
# NEVER: (none)

BLOCK_IDS = ["knowledge", "memory", "storage"]
CAPABILITY_ID = "pilot_ops_log"


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Store a pilot note, cache the title, and ask the knowledge block."""
    title = str(payload.get("note_title") or payload.get("reference") or "sample")
    body = str(payload.get("note_body") or f"Pilot note {title}")
    record = {
        **payload,
        "note_title": title,
        "note_body": body,
        "capability": CAPABILITY_ID,
        "channel": "mcp",
    }
    blocks = {
        "knowledge": execute(
            "knowledge",
            knowledge_input(record),
            action=BLOCK_DEFAULT_ACTIONS.get("knowledge"),
        ),
        "memory": execute(
            "memory",
            memory_input(record),
            action=BLOCK_DEFAULT_ACTIONS.get("memory"),
        ),
        "storage": execute(
            "storage",
            storage_input(record),
            action=BLOCK_DEFAULT_ACTIONS.get("storage"),
        ),
    }
    record["log_entry"] = {
        "note_title": title,
        "stored": True,
        "cached_key": f"pilot_ops:{record.get('reference') or 'sample'}",
    }
    return ok_envelope(CAPABILITY_ID, record, blocks)
