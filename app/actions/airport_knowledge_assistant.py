"""airport_knowledge_assistant — REUSE knowledge + vector_search + recommendation_template + memory."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import (
    knowledge_input,
    memory_input,
    recommendation_template_input,
    vector_search_input,
)
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, env.process, config.runtime, database.vector, memory.cache
# WRITES: caller.output, database.vector, memory.cache
# NEVER: (none)

BLOCK_IDS = ["knowledge", "vector_search", "recommendation_template", "memory"]
CAPABILITY_ID = "airport_knowledge_assistant"


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Ask the knowledge block, search the corpus, recommend, and cache."""
    question = str(payload.get("question") or payload.get("reference") or "sample")
    note_body = str(payload.get("note_body") or question)
    record = {
        **payload,
        "question": question,
        "note_body": note_body,
        "capability": CAPABILITY_ID,
        "channel": "mcp",
    }
    blocks = {
        "knowledge": execute(
            "knowledge",
            knowledge_input(record),
            action=BLOCK_DEFAULT_ACTIONS.get("knowledge"),
        ),
        "vector_search": execute(
            "vector_search",
            vector_search_input(record),
            action=BLOCK_DEFAULT_ACTIONS.get("vector_search"),
        ),
        "recommendation_template": execute(
            "recommendation_template",
            recommendation_template_input(record),
            action=BLOCK_DEFAULT_ACTIONS.get("recommendation_template"),
        ),
        "memory": execute(
            "memory",
            memory_input(record),
            action=BLOCK_DEFAULT_ACTIONS.get("memory"),
        ),
    }
    record["assistant"] = {
        "question": question,
        "cached_key": f"airport_ops:{record.get('reference') or 'sample'}",
        "searched": True,
    }
    return ok_envelope(CAPABILITY_ID, record, blocks)
