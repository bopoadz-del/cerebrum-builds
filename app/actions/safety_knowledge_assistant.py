"""safety_knowledge_assistant — REUSE knowledge + vector_search + memory."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import knowledge_input, memory_input, vector_search_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, env.process, config.runtime, network.http.outbound,
#        database.vector, llm.provider, credential.env, memory.cache
# WRITES: caller.output, database.vector, memory.cache
# NEVER: (none)

BLOCK_IDS = ["knowledge", "vector_search", "memory"]

CORPUS_HINT = {
    "asrs": "NASA ASRS narrative patterns for aviation safety",
    "sms": "operator safety management system findings",
    "sop": "standard operating procedure excerpts",
}


def _corpus(payload: Dict[str, Any]) -> str:
    value = str(payload.get("corpus") or "asrs")
    return value if value in CORPUS_HINT else "asrs"


def _question(payload: Dict[str, Any]) -> str:
    raw = payload.get("question")
    if raw in (None, "", "sample"):
        return f"What safety lesson applies to {payload.get('reference') or 'sample'}?"
    return str(raw)


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Ask the safety corpus, search vectors, and cache the session answer."""
    corpus = _corpus(payload)
    question = _question(payload)
    reference = str(payload.get("reference") or "sample")
    query = f"{question} corpus={CORPUS_HINT[corpus]}"
    blocks = {
        "knowledge": execute(
            "knowledge",
            knowledge_input(payload, query),
            action=BLOCK_DEFAULT_ACTIONS.get("knowledge"),
        ),
        "vector_search": execute(
            "vector_search",
            vector_search_input(payload, query),
            action=BLOCK_DEFAULT_ACTIONS.get("vector_search"),
        ),
        "memory": execute(
            "memory",
            memory_input(payload, f"safety:{reference}", {"question": question, "corpus": corpus}),
            action=BLOCK_DEFAULT_ACTIONS.get("memory"),
        ),
    }
    knowledge_result = blocks["knowledge"].get("result") if isinstance(blocks["knowledge"], dict) else {}
    answer = ""
    if isinstance(knowledge_result, dict):
        answer = str(knowledge_result.get("answer") or "")
    record = {
        **payload,
        "safety_answer": {
            "corpus": corpus,
            "corpus_hint": CORPUS_HINT[corpus],
            "question": question,
            "answer_preview": answer[:240],
            "cached": True,
            "channel": "mcp",
        },
    }
    return ok_envelope("safety_knowledge_assistant", record, blocks)
