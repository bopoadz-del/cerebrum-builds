"""dual_rag_sop — Layer 1 SOP corpus persist. REUSE knowledge + vector_search + document_engine."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import document_engine_input, knowledge_input, vector_search_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, file.local.read, database.vector, llm.provider, config.runtime
# WRITES: caller.output, file.local.write, database.vector
# NEVER: substituting vector_search for HTTP ingest/query routes

BLOCK_IDS = ["knowledge", "vector_search", "document_engine"]


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Persist a SOP-layer dual-RAG record (ingest/query lives in app/rag_routes.py)."""
    blocks = {
        "knowledge": execute(
            "knowledge",
            knowledge_input(payload),
            action=BLOCK_DEFAULT_ACTIONS.get("knowledge"),
        ),
        "vector_search": execute(
            "vector_search",
            vector_search_input(payload),
            action=BLOCK_DEFAULT_ACTIONS.get("vector_search"),
        ),
        "document_engine": execute(
            "document_engine",
            document_engine_input(payload),
            action=BLOCK_DEFAULT_ACTIONS.get("document_engine"),
        ),
    }
    record = {**payload, "rag_layer": 1, "index": "steward_sop_v1"}
    return ok_envelope("dual_rag_sop", record, blocks)
