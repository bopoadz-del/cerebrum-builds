"""Capability document_knowledge_qa — uploaded unit prices / procedures and answers.

Written by the factory WRITER role (codewhale exec)

Blocks are invoked through the local dispatch runtime (``app.dispatch.execute``)
against the block source vendored at build time — this module makes no network
call and never persists: the ROUTE writes the tenant-scoped record after
``handle()`` reports success (Phase 2 §0.2).

Pipeline:
  * ``document_engine`` — parses and hashes the uploaded document text;
  * ``knowledge``       — indexes the document into the tenant-scoped corpus and
    answers the operator's question over it;
  * ``vector_search``   — searches the document corpus for the closest matches;
  * ``storage``         — stores the raw document under ``STORAGE_PATH``;
  * ``memory``          — caches the last answer for the shop's session;
  * ``spec_analyzer``   — extracts structure (headings, tables, prices) from the
    document so unit prices and procedures are addressable.

The corpus is empty until documents are uploaded — an empty answer is a real
answer ("I don't have any relevant information"), never a fabricated one.

Scope
-----
READS  the caller's payload, ``STORAGE_PATH`` (documents and corpus).
WRITES ``STORAGE_PATH`` (document + corpus) through the blocks.
NEVER  network, HTTP store callbacks, ``vendor/**``.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List

from app.block_inputs import prepare_block_input
from app.dispatch import execute

CAPABILITY_ID = "document_knowledge_qa"
ENTITY = "document_knowledge_qa"
BLOCK_IDS = [
    "document_engine",
    "knowledge",
    "vector_search",
    "storage",
    "memory",
    "spec_analyzer",
]
#: Each block's declared action (keyword dispatch; never inside the payload).
BLOCK_DEFAULT_ACTIONS = {
    "document_engine": "parse",
    "knowledge": "ask",
    "vector_search": "search",
    "storage": "store",
    "memory": "set",
    "spec_analyzer": "analyze",
}
CAPABILITY_FIELDS: List[str] = [
    "reference",
    "document_title",
    "document_type",
    "source_path",
    "question",
    "answer",
    "notes",
    "status",
]

TENANT_ID = "local"


def _document_text(record: Dict[str, Any]) -> str:
    """The exact text the engine, the corpus and the digest must all cover."""
    title = str(record.get("document_title") or record.get("reference") or "document")
    kind = str(record.get("document_type") or "other")
    body = str(record.get("notes") or record.get("answer") or "")
    return "%s|%s|%s" % (title, kind, body)


def _question(record: Dict[str, Any]) -> str:
    return str(record.get("question") or record.get("document_title") or "reference")


def _document_identity(record: Dict[str, Any]) -> Dict[str, str]:
    text = _document_text(record)
    return {
        "collection": "bakery_documents",
        "doc_id": "%s:%s"
        % (
            str(record.get("document_type") or "other"),
            str(record.get("reference") or "sample"),
        ),
        "digest": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "text": text,
    }


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(payload) if isinstance(payload, dict) else {"value": payload}
    identity = _document_identity(data)
    question = _question(data)
    results: Dict[str, Any] = {}
    errors: Dict[str, str] = {}
    for block_id in BLOCK_IDS:
        prepared = prepare_block_input(block_id, data, entity=ENTITY)
        if block_id == "document_engine":
            prepared["text"] = identity["text"]
            prepared["title"] = str(data.get("document_title") or "document")
        if block_id == "knowledge":
            prepared["query"] = question
            prepared["collection"] = identity["collection"]
            prepared["tenant_id"] = TENANT_ID
            prepared["documents"] = [
                {"doc_id": identity["doc_id"], "text": identity["text"]}
            ]
        if block_id == "vector_search":
            prepared["operation"] = "search"
            prepared["query"] = question
            prepared["collection"] = identity["collection"]
            prepared["documents"] = [
                {"id": identity["doc_id"], "text": identity["text"]}
            ]
        if block_id == "storage":
            prepared["filename"] = "%s.txt" % identity["doc_id"].replace(":", "_")
            prepared["content"] = identity["text"]
            prepared["metadata"] = {
                "document_type": str(data.get("document_type") or "other"),
                "digest": identity["digest"],
            }
        if block_id == "memory":
            prepared["key"] = "answer:%s" % identity["doc_id"]
            prepared["value"] = {
                "question": question,
                "answer": data.get("answer"),
                "digest": identity["digest"],
            }
        if block_id == "spec_analyzer":
            prepared["text"] = identity["text"]
            prepared["title"] = str(data.get("document_title") or "document")
        result = execute(
            block_id, prepared, action=BLOCK_DEFAULT_ACTIONS.get(block_id)
        )
        results[block_id] = result
        if isinstance(result, dict) and (
            result.get("status") in ("error", "failed", "partial")
            or result.get("ok") is False
            or "error" in result
        ):
            errors[block_id] = str(result.get("error") or result)[:200]
    if errors:
        return {
            "ok": False,
            "capability": CAPABILITY_ID,
            "error": "; ".join(f"{b}: {e}" for b, e in sorted(errors.items())),
            "results": results,
        }
    return {"ok": True, "capability": CAPABILITY_ID, "results": results}
