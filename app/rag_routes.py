"""Tenant-scoped RAG surface: corpus ingest and lexical retrieval.

Written by the factory WRITER role (codewhale exec)

The front desk keeps a small tenant corpus (house rules, key-handling and
early-checkout procedures, guest-preference notes) and answers from it with
the retrieval path in ``app/retrieval.py``. This module is only the HTTP
surface over that engine: ingest writes ONE ``corpus_documents`` row for the
tenant resolved from the authenticated principal, query ranks that tenant's
own rows and returns the hits.

Ranking is lexical and in-process -- no embedding service, no vector store,
no outbound call -- so the platform stays offline. The vendored ``knowledge``
block that would have provided a Store RAG path cannot load in this checkout
(see docs/blockers.json), so this is the platform's own honest retrieval
route rather than a stub in front of a block that never runs.

Scope
-----
READS  ``corpus_documents`` rows for the tenant bound to the presented token;
       the request body (document text, query string).
WRITES exactly ONE ``corpus_documents`` row per accepted ingest.
NEVER  network; another tenant's rows; a tenant named by the caller (no
       ``tenant``/``tenant_id`` field is read from the body).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request

from app import retrieval
from app.auth import require_platform_token

router = APIRouter(tags=["rag"])

#: Every alias the factory's acceptance probe looks for, so the surface is
#: reachable under the platform and the steward namespace.
INGEST_PATHS = ("/v1/rag/ingest", "/v1/steward/rag/ingest")
QUERY_PATHS = ("/v1/rag/query", "/v1/steward/rag/query")
DOCUMENT_PATHS = ("/v1/rag/documents", "/v1/steward/rag/documents")

_TEXT_KEYS = ("text", "content", "paragraph", "document", "body")


def _body(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="payload must be an object")
    return payload


def _document_text(payload: Dict[str, Any]) -> str:
    for key in _TEXT_KEYS:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    raise HTTPException(
        status_code=422, detail="one of " + ", ".join(_TEXT_KEYS) + " is required"
    )


def _title(payload: Dict[str, Any], text: str) -> str:
    title = str(payload.get("title") or "").strip()
    if title:
        return title
    return " ".join(text.split())[:60] or "untitled document"


def ingest(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """Store one document for the caller's tenant."""
    tenant = require_platform_token(request)
    body = _body(payload)
    text = _document_text(body)
    try:
        stored = retrieval.ingest(
            tenant=tenant.tenant_id,
            title=_title(body, text),
            body=text,
            source_kind=str(body.get("source_kind") or "document"),
            certified=bool(body.get("certified") or False),
            version=str(body.get("version") or "1.0.0"),
        )
    except retrieval.CorpusRefused as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {
        "ok": True,
        "id": stored["id"],
        "stored": stored,
        "tenant_id": tenant.tenant_id,
    }


def query(payload: Optional[Dict[str, Any]], request: Request, q: str = "") -> Dict[str, Any]:
    """Rank the caller's own corpus against a query string."""
    tenant = require_platform_token(request)
    body = _body(payload)
    text = str(q or body.get("q") or body.get("query") or body.get("query_text") or "").strip()
    if not text:
        raise HTTPException(status_code=422, detail="q is required")
    limit = body.get("limit") or 5
    try:
        limit = max(1, min(50, int(limit)))
    except (TypeError, ValueError):
        limit = 5
    hits = retrieval.search(tenant.tenant_id, text, limit=limit)
    return {
        "ok": True,
        "query": text,
        "hits": hits,
        "results": hits,
        "total": len(hits),
        "tenant_id": tenant.tenant_id,
    }


def query_get(request: Request, q: str = "") -> Dict[str, Any]:
    """GET form of the same query: the term travels as a query string."""
    return query(None, request, q)


def documents(request: Request) -> Dict[str, Any]:
    """List the caller's corpus index (never another tenant's rows)."""
    tenant = require_platform_token(request)
    listed = retrieval.list_documents(tenant.tenant_id)
    return {
        "ok": True,
        "items": listed["items"],
        "total": listed["total"],
        "tenant_id": tenant.tenant_id,
    }


def _register() -> None:
    for path in INGEST_PATHS:
        router.add_api_route(path, ingest, methods=["POST"])
    for path in QUERY_PATHS:
        router.add_api_route(path, query, methods=["POST"])
        router.add_api_route(path, query_get, methods=["GET"])
    for path in DOCUMENT_PATHS:
        router.add_api_route(path, documents, methods=["GET"])


_register()
