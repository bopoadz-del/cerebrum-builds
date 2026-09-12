"""dual_rag_estate_docs — Layer 2 estate documents persist. REUSE knowledge + vector_search + document_engine."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import document_engine_input, knowledge_input, vector_search_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, file.local.read, database.vector, llm.provider, config.runtime
# WRITES: caller.output, file.local.write, database.vector
# NEVER: mixing SOP and estate indexes

BLOCK_IDS = ["knowledge", "vector_search", "document_engine"]


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Persist an estate-document dual-RAG record on the separately indexed layer."""
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
    record = {**payload, "rag_layer": 2, "index": "steward_estate_docs_v1"}
    return ok_envelope("dual_rag_estate_docs", record, blocks)
