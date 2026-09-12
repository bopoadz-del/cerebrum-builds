"""house_manual_sop — House Manual / SOP corpus. REUSE document_engine + knowledge + vector_search."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import document_engine_input, knowledge_input, vector_search_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, file.local.read, file.input_document, config.runtime, database.vector, llm.provider
# WRITES: caller.output, file.local.write, file.temp, database.vector
# NEVER: (none)

BLOCK_IDS = ["document_engine", "knowledge", "vector_search"]


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Index a House Manual SOP record through document + knowledge + vector search."""
    blocks = {
        "document_engine": execute(
            "document_engine",
            document_engine_input(payload),
            action=BLOCK_DEFAULT_ACTIONS.get("document_engine"),
        ),
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
    }
    return ok_envelope("house_manual_sop", payload, blocks)
