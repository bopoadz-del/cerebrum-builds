"""safety_knowledge_assistant — REUSE knowledge + vector_search + memory."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import knowledge_input, memory_input, vector_search_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, memory.cache
# WRITES: caller.output, memory.cache
# NEVER: (none)

BLOCK_IDS = ["knowledge", "vector_search", "memory"]
CAPABILITY_ID = "safety_knowledge_assistant"
LAYERS = ("sms", "asrs", "fom")


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Ask the safety corpus, search offline, and cache the question in memory."""
    layer = str(payload.get("corpus_layer") or "sms")
    if layer not in LAYERS:
        layer = "sms"
    question = str(payload.get("question") or payload.get("reference") or "sample")
    record = {
        **payload,
        "corpus_layer": layer,
        "question": question,
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
        "memory": execute(
            "memory",
            memory_input(record),
            action=BLOCK_DEFAULT_ACTIONS.get("memory"),
        ),
    }
    hits = ((blocks["vector_search"].get("result") or {}) or {}).get("total_found") or 0
    record["safety"] = {
        "corpus_layer": layer,
        "question": question,
        "hits": hits,
        "cached_key": f"safety:{record.get('reference') or 'sample'}",
        "retrieval": "lexical_offline",
    }
    return ok_envelope(CAPABILITY_ID, record, blocks)
