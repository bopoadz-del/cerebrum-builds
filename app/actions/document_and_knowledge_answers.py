"""Handler for capability document_and_knowledge_answers.

Written by the factory WRITER role (codewhale exec)

Authored by the coder CLI (codewhale exec) — the factory WRITER coding
agent — against the vendored blocks, in this repository.

Ingests a property document and answers staff questions from ingested sources: the
vendored document engine parses it into requirements, constraints, risks and
equipment specs, the hotel engine classifies it (manual, SOP, rate sheet), and the
tenant's own corpus (app.retrieval, precedence.v1) is what actually answers.

Scope
-----
READS  this capability's own columns from the caller's record; app.dispatch
       (the local offline block runtime); app.block_inputs (block input
       construction); app.store (the ``document_and_knowledge_answers`` table, through the route's
       tenant-scoped save); app.retrieval and app.authority (the tenant corpus and precedence.v1).
WRITES app.dispatch.execute() results; exactly one row in ``document_and_knowledge_answers`` via the
       ROUTE's tenant-scoped persistence (app.routes) -- this handler has no
       tenant and never persists directly.
NEVER  unguarded network egress; ``vendor/**`` (sealed, read-only); another
       capability's table; ``tests/**``.

Blocks are action-dispatched: ``action=`` is a keyword on
``app.dispatch.execute`` (via app.block_run), never a key inside the domain
payload. Block-contract keys are constructed by
``app.block_inputs.prepare_block_input`` from this record.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.block_run import block_runner
from app.security import InputRefused, clean_text

CAPABILITY_ID = "document_and_knowledge_answers"
ENTITY = "document_and_knowledge_answers"
BLOCK_IDS = ['document_engine', 'hotel_v2']
#: Each block's declared action (block.json / the Store map). Blocks are
#: action-dispatched; calling one with no action answers "Unknown action".
#: ``knowledge`` keeps its Store default here because the capability's
#: inventory binds it; see docs/blockers.json -- the vendored knowledge block
#: cannot load offline (it requires vendor.cerebrum.core.vector_store, which
#: the runtime slice does not ship), so document_engine carries the parsing and
#: app.retrieval carries retrieval.
BLOCK_DEFAULT_ACTIONS = {'knowledge': 'search', 'document_engine': 'parse', 'hotel_v2': 'analyze'}
#: This capability's own domain columns.
CAPABILITY_FIELDS = ['reference', 'status', 'title', 'document_kind', 'question', 'document_text', 'attachment_path', 'answer', 'source_document', 'authority_label', 'notes']


def _text(data: Dict[str, Any], name: str, limit: int = 2000) -> str:
    return clean_text(data.get(name), field=name, limit=limit)

_VALID_SECTIONS = ("requirements", "constraints", "risks", "glossary", "equipment_specs")


def _document_brief(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "title": _text(data, "title", 200) or "untitled document",
        "kind": _text(data, "document_kind", 40) or "other",
        "reference": _text(data, "reference", 120),
        "question": _text(data, "question", 500),
        "path": _text(data, "attachment_path", 1000) or None,
    }


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(payload or {}) if isinstance(payload, dict) else {}
    runner = block_runner(entity=ENTITY, roster=BLOCK_IDS, default_actions=BLOCK_DEFAULT_ACTIONS)

    try:
        brief = _document_brief(data)
        body_text = _text(data, "document_text", 20000)
        if not body_text:
            return {
                "ok": False,
                "capability": CAPABILITY_ID,
                "error": "document_text is required: there is nothing to ingest",
            }
    except InputRefused as exc:
        return {"ok": False, "capability": CAPABILITY_ID, "error": str(exc)}

    parsed = runner(
        "document_engine",
        {"text": body_text, "attachment_path": brief["path"]},
        action="parse",
    )
    analysed = runner("hotel_v2", {"text": body_text}, action="analyze")

    refusal = runner.refusal()
    if refusal is not None:
        return {"ok": False, "capability": CAPABILITY_ID, **refusal}

    requirements = parsed.get("requirements") if isinstance(parsed, dict) else None
    sections = {
        name: len(parsed.get(name) or [])
        for name in _VALID_SECTIONS
        if isinstance(parsed, dict) and isinstance(parsed.get(name), list)
    }
    metrics = analysed.get("metrics") if isinstance(analysed, dict) else {}
    if not isinstance(metrics, dict):
        metrics = {}
    return {
        "ok": True,
        "capability": CAPABILITY_ID,
        "document": {
            "title": brief["title"],
            "kind": brief["kind"],
            "characters": len(body_text),
            "sections": sections,
            "requirements_found": len(requirements or []),
            "documents_parsed": parsed.get("documents_parsed") if isinstance(parsed, dict) else None,
        },
        "question": brief["question"],
        "analysis": {
            "document_type": analysed.get("document_type") if isinstance(analysed, dict) else None,
            "metric_count": len([v for v in metrics.values() if isinstance(v, dict) and v.get("value") is not None]),
        },
        "retrieval": (
            "the corpus lives in this tenant's own database (rag_document / "
            "rag_chunk); POST /v1/rag/ingest and POST /v1/rag/query answer from "
            "it with authority labels and citations (precedence.v1)"
        ),
        "authority_label": _text(data, "authority_label", 40) or "documents",
        "blocks": runner.report(),
    }
