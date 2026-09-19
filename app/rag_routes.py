"""RAG ingest/query surface for the Bakery Chain Operations recipe and compliance corpus.

Written by the factory WRITER role (codewhale exec)

Two honest HTTP routes over the local corpus, both quotable contracts:

* ``POST /v1/rag/ingest``  — store a paragraph of recipe/spec/SOP text;
* ``GET  /v1/rag/query``   — retrieve structured hits for a query string;
* ``POST /v1/rag/query``   — the same, with the query in the body.

Ingest writes to the tenant's own corpus file under ``STORAGE_PATH`` and query
answers from it through ``app.retrieval`` (the vendored ``vector_search`` block
remains the block of record for capability calls). No embedding service, no
network: the pilot path is deterministic so it runs inside the Store image.

Scope
-----
READS  the request body/query string, ``STORAGE_PATH`` corpus.
WRITES ``STORAGE_PATH`` (``rag_index.jsonl``).
NEVER  network, another tenant's corpus, ``vendor/**``.
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.retrieval import search as corpus_search

router = APIRouter(tags=["rag-surface"])
_LOCK = threading.Lock()


def _index_path() -> Path:
    root = Path(os.environ.get("STORAGE_PATH") or ".").resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root / "rag_index.jsonl"


def load_documents() -> List[Dict[str, Any]]:
    path = _index_path()
    if not path.is_file():
        return []
    rows: List[Dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict) and row.get("text"):
                rows.append(row)
    return rows


def persist_document(record: Dict[str, Any]) -> Dict[str, Any]:
    with _LOCK:
        with _index_path().open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    return record


class RagIngestRequest(BaseModel):
    text: Optional[str] = None
    content: Optional[str] = None
    paragraph: Optional[str] = None
    title: Optional[str] = None
    doc_id: Optional[str] = None
    layer: str = "documents"
    tenant_id: Optional[str] = None


class RagQueryRequest(BaseModel):
    q: Optional[str] = None
    query: Optional[str] = None
    text: Optional[str] = None
    top_k: int = Field(5, ge=1, le=20)


def _body_text(body: RagIngestRequest) -> str:
    for candidate in (body.text, body.content, body.paragraph):
        if candidate and str(candidate).strip():
            return str(candidate).strip()
    return ""


def _query_text(q: Optional[str], body: Optional[RagQueryRequest] = None) -> str:
    if q and str(q).strip():
        return str(q).strip()
    if body is None:
        return ""
    for candidate in (body.q, body.query, body.text):
        if candidate and str(candidate).strip():
            return str(candidate).strip()
    return ""


@router.post("/v1/rag/ingest")
def rag_ingest(body: RagIngestRequest) -> Dict[str, Any]:
    text = _body_text(body)
    if not text:
        return {"ok": False, "error": "ingest body needs text, content, or paragraph"}
    doc_id = (body.doc_id or "").strip() or ("doc-" + uuid.uuid4().hex[:12])
    title = (body.title or "").strip() or doc_id
    record = persist_document(
        {
            "doc_id": doc_id,
            "title": title,
            "text": text,
            "layer": body.layer,
            "tenant_id": body.tenant_id,
        }
    )
    return {
        "ok": True,
        "document_id": record["doc_id"],
        "title": record["title"],
        "layer": record["layer"],
        "stored": True,
        "chunk_count": 1,
        "source": "bakery rag surface",
    }


def _query_payload(query: str, top_k: int) -> Dict[str, Any]:
    if not query:
        return {"ok": False, "error": "query is required", "hits": [], "hit_count": 0}
    hits = corpus_search(query, top_k=top_k)
    return {
        "ok": True,
        "query": query,
        "hit_count": len(hits),
        "hits": hits,
        "insufficiency": len(hits) == 0,
        "source": "bakery rag surface",
    }


@router.get("/v1/rag/query")
def rag_query_get(
    q: str = Query(..., min_length=1),
    top_k: int = Query(5, ge=1, le=20),
) -> Dict[str, Any]:
    return _query_payload(q, top_k)


@router.post("/v1/rag/query")
def rag_query_post(body: RagQueryRequest) -> Dict[str, Any]:
    return _query_payload(_query_text(None, body), body.top_k)
