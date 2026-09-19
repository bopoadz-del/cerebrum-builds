"""Local retrieval surface: ingest clinic documents, query them back.

Written by the factory WRITER role (codewhale exec).

Offline by construction: the index is lexical (token overlap with inverse
document frequency weighting) inside the platform sqlite file -- no
embedding provider, no network call, no LLM. That is the honest capability
this platform can run under P1; it is a keyword index, not a semantic one,
and it says so rather than pretending otherwise.

Tenancy is the platform's single path (§0.2): both routes resolve the
tenant from the authenticated principal (app.security.authenticate) and
never from the request body, and every read is scoped by ``tenant_id``, so
one clinic can neither plant into nor read another clinic's corpus.

Routes (the /v1/steward/rag/* twins keep the Store kit contract):

    POST /v1/rag/ingest          POST /v1/steward/rag/ingest
    GET  /v1/rag/query           GET  /v1/steward/rag/query
    POST /v1/rag/query           POST /v1/steward/rag/query
"""

from __future__ import annotations

import json
import math
import re
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException, Request

from app.store import connect

router = APIRouter(tags=["retrieval"])

#: Quoted route paths (phase-2 contract: ingest + query on app/**/*.py).
RAG_INGEST_PATHS: Tuple[str, ...] = ("/v1/rag/ingest", "/v1/steward/rag/ingest")
RAG_QUERY_PATHS: Tuple[str, ...] = ("/v1/rag/query", "/v1/steward/rag/query")

_TABLE = "rag_chunks"
_TOKEN_RE = re.compile(r"[a-z0-9]+")
CHUNK_WORDS = 80
DEFAULT_TOP_K = 5
MAX_TOP_K = 50


def _principal(request: Request) -> str:
    """The authenticated tenant. Missing/unknown token is HTTP 401."""
    from app.security import authenticate

    return authenticate(request).tenant_id


def _tokens(text: Any) -> List[str]:
    return _TOKEN_RE.findall(str(text or "").lower())


def _chunks(text: Any, size: int = CHUNK_WORDS) -> List[str]:
    """Split a document on word boundaries. Deterministic, no overlap."""
    words = str(text or "").split()
    if not words:
        return []
    step = max(1, int(size))
    return [" ".join(words[i : i + step]) for i in range(0, len(words), step)]


def _documents(payload: Dict[str, Any]) -> List[Dict[str, str]]:
    """Read the documented body: one document, or a ``documents`` list.

    Accepts ``text`` / ``content`` / ``paragraph`` for a single document,
    and a list of strings or ``{text, source}`` mappings for a batch.
    """
    default_source = str(payload.get("source") or payload.get("title") or "inline")
    out: List[Dict[str, str]] = []
    single = None
    for key in ("text", "content", "paragraph", "body"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            single = value
            break
    if single is not None:
        out.append({"text": single, "source": default_source})
    raw_docs = payload.get("documents")
    if isinstance(raw_docs, list):
        for index, item in enumerate(raw_docs):
            if isinstance(item, str):
                if item.strip():
                    out.append({"text": item, "source": default_source})
                continue
            if not isinstance(item, dict):
                continue
            text = None
            for key in ("text", "content", "paragraph", "body"):
                value = item.get(key)
                if isinstance(value, str) and value.strip():
                    text = value
                    break
            if text is None:
                continue
            out.append(
                {
                    "text": text,
                    "source": str(item.get("source") or item.get("title") or default_source),
                }
            )
    return out


def _top_k(value: Any) -> int:
    try:
        k = int(value)
    except (TypeError, ValueError):
        return DEFAULT_TOP_K
    if k < 1:
        return DEFAULT_TOP_K
    return min(k, MAX_TOP_K)


def _store_documents(tenant_id: str, docs: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """Chunk, index and persist. Returns one row per stored chunk."""
    stored: List[Dict[str, Any]] = []
    conn = connect()
    try:
        for doc in docs:
            for ordinal, chunk in enumerate(_chunks(doc["text"])):
                tokens = _tokens(chunk)
                if not tokens:
                    continue
                cur = conn.execute(
                    "INSERT INTO " + _TABLE
                    + " (tenant_id, source, ordinal, text, tokens) VALUES (?, ?, ?, ?, ?)",
                    (tenant_id, doc["source"], ordinal, chunk, json.dumps(tokens)),
                )
                stored.append(
                    {
                        "id": cur.lastrowid,
                        "source": doc["source"],
                        "ordinal": ordinal,
                        "tokens": len(tokens),
                    }
                )
        conn.commit()
    finally:
        conn.close()
    return stored


def _search(tenant_id: str, query_text: Any, top_k: int) -> List[Dict[str, Any]]:
    """Lexical top-k for one tenant. No shared token means no hit."""
    query_tokens = _tokens(query_text)
    if not query_tokens:
        return []
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT id, source, ordinal, text, tokens FROM " + _TABLE
            + " WHERE tenant_id = ? ORDER BY id",
            (tenant_id,),
        ).fetchall()
    finally:
        conn.close()
    if not rows:
        return []

    parsed: List[Tuple[Any, List[str]]] = []
    document_frequency: Dict[str, int] = {}
    for row in rows:
        try:
            tokens = list(json.loads(row["tokens"]))
        except (TypeError, ValueError):
            tokens = []
        parsed.append((row, tokens))
        for token in set(tokens):
            document_frequency[token] = document_frequency.get(token, 0) + 1

    total = len(parsed)
    distinct_query = sorted(set(query_tokens))
    hits: List[Dict[str, Any]] = []
    for row, tokens in parsed:
        counts: Dict[str, int] = {}
        for token in tokens:
            counts[token] = counts.get(token, 0) + 1
        score = 0.0
        matched = 0
        for token in distinct_query:
            frequency = counts.get(token)
            if not frequency:
                continue
            matched += 1
            inverse = math.log(1.0 + total / float(document_frequency.get(token, 1)))
            score += inverse * (1.0 + math.log(frequency))
        if matched and score > 0:
            hits.append(
                {
                    "id": row["id"],
                    "source": row["source"],
                    "ordinal": row["ordinal"],
                    "score": round(score, 6),
                    "matched_terms": matched,
                    "text": row["text"],
                }
            )
    hits.sort(key=lambda hit: (-float(hit["score"]), int(hit["id"])))
    return hits[:top_k]


def _answer(tenant_id: str, query_text: Any, top_k: int) -> Dict[str, Any]:
    hits = _search(tenant_id, query_text, top_k)
    return {
        "ok": True,
        "tenant_id": tenant_id,
        "query": "" if query_text is None else str(query_text),
        "index": "lexical",
        "count": len(hits),
        "hits": hits,
    }


def _ingest(tenant_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    docs = _documents(payload if isinstance(payload, dict) else {})
    if not docs:
        raise HTTPException(
            status_code=400,
            detail="ingest requires text/content/paragraph or documents[]",
        )
    stored = _store_documents(tenant_id, docs)
    if not stored:
        raise HTTPException(status_code=400, detail="document carried no indexable text")
    return {
        "ok": True,
        "tenant_id": tenant_id,
        "index": "lexical",
        "documents": len(docs),
        "ingested": len(stored),
        "chunks": stored,
    }


@router.post("/v1/rag/ingest")
def rag_ingest(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """Index one document (or a ``documents`` batch) for this tenant."""
    return _ingest(_principal(request), payload)


@router.post("/v1/steward/rag/ingest")
def steward_rag_ingest(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """Same ingest contract under the Store kit path."""
    return _ingest(_principal(request), payload)


@router.get("/v1/rag/query")
def rag_query(request: Request, q: Optional[str] = None, k: int = DEFAULT_TOP_K) -> Dict[str, Any]:
    """Retrieve chunks for ``?q=`` — top ``k`` (default 5)."""
    tenant_id = _principal(request)
    return _answer(tenant_id, q or "", _top_k(k))


@router.post("/v1/rag/query")
def rag_query_post(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """Retrieve chunks for ``{"q": ...}`` or ``{"query": ...}``."""
    tenant_id = _principal(request)
    body = payload if isinstance(payload, dict) else {}
    text = body.get("q")
    if text in (None, ""):
        text = body.get("query")
    return _answer(tenant_id, text or "", _top_k(body.get("k")))


@router.get("/v1/steward/rag/query")
def steward_rag_query(request: Request, q: Optional[str] = None, k: int = DEFAULT_TOP_K) -> Dict[str, Any]:
    """Same query contract under the Store kit path."""
    tenant_id = _principal(request)
    return _answer(tenant_id, q or "", _top_k(k))


@router.post("/v1/steward/rag/query")
def steward_rag_query_post(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """Same query contract under the Store kit path (POST form)."""
    tenant_id = _principal(request)
    body = payload if isinstance(payload, dict) else {}
    text = body.get("q")
    if text in (None, ""):
        text = body.get("query")
    return _answer(tenant_id, text or "", _top_k(body.get("k")))
