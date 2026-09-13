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
from app.domain import allowed_next_status, envelope_status, knowledge_source_class
from app.persist import ok_envelope

# READS: caller.input, env.process, config.runtime, database.vector, memory.cache
# WRITES: caller.output, database.vector, memory.cache
# NEVER: (none)

BLOCK_IDS = ["knowledge", "vector_search", "recommendation_template", "memory"]
CAPABILITY_ID = "airport_knowledge_assistant"


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Ask, search, recommend, and cache with an honest source class."""
    status = envelope_status(payload)
    question = str(payload.get("question") or payload.get("reference") or "sample")
    note_body = str(payload.get("note_body") or question)
    source_class = knowledge_source_class(question, note_body)
    record = {
        **payload,
        "status": status,
        "question": question,
        "note_body": note_body,
        "source_class": source_class,
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
        "source_class": source_class,
        "retrieval": "lexical_plus_vector_search",
        "cached_key": f"airport_ops:{record.get('reference') or 'sample'}",
        "allowed_next_status": list(allowed_next_status(status)),
        "searched": True,
    }
    return ok_envelope(CAPABILITY_ID, record, blocks)
