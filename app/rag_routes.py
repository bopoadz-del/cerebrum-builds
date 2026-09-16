"""RAG ingest/query over the clinic's own tenant-scoped corpus.

Written by the factory WRITER role (codewhale exec).

The clinic's documents (SOPs, guidance, imported notes) are ingested here and
queried here. Both routes resolve the tenant from the authenticated principal
(app/tenancy.py) — a caller cannot name another tenant's corpus — and both are
served entirely in-process by the platform's own lexical index
(app/retrieval.py). No vector service, no outbound call.

    POST /v1/rag/ingest   {"text": "...", "doc_id": "...", "collection": "..."}
    POST /v1/rag/query    {"query": "..."}        → hits + extractive answer
    GET  /v1/rag/query?q=...                      → same, for a browser

Answers carry their citations and ``grounded``; an empty corpus answers
``grounded: false`` with no invented text.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request

from app import retrieval, tenancy

router = APIRouter()


def _tenant(request: Request) -> tenancy.Tenant:
    try:
        return tenancy.resolve_tenant(request.headers)
    except tenancy.TenantRefused:
        raise HTTPException(status_code=401, detail="authentication_required")


def _text_of(payload: Dict[str, Any]) -> str:
    for key in ("text", "content", "paragraph", "document", "body", "page"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _query_of(payload: Dict[str, Any]) -> str:
    for key in ("query", "q", "question", "text", "search"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


@router.post("/v1/rag/ingest")
def rag_ingest(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    tenant = _tenant(request)
    data = payload if isinstance(payload, dict) else {}
    text = _text_of(data)
    if not text:
        raise HTTPException(status_code=422, detail="text is required")
    try:
        tenancy.refuse_client_tenant(data)
    except tenancy.TenantRefused as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    metadata = {
        "collection": str(data.get("collection") or "clinic_corpus"),
        "title": str(data.get("title") or ""),
        "source": str(data.get("source") or "api"),
    }
    indexed = retrieval.ingest_document(
        tenant.tenant_id,
        text,
        doc_id=str(data.get("doc_id") or "") or None,
        metadata=metadata,
    )
    return {
        "ok": True,
        "tenant": tenant.to_dict(),
        "doc_id": indexed["doc_id"],
        "terms": indexed["terms"],
        "corpus_total": indexed["corpus_total"],
        "collection": metadata["collection"],
    }


def _query(tenant: tenancy.Tenant, query: str, top_k: int) -> Dict[str, Any]:
    retrieval.seed_clinic_guidance(tenant.tenant_id)
    hits = retrieval.search(tenant.tenant_id, query, top_k=top_k)
    answer = retrieval.answer(tenant.tenant_id, query, top_k=top_k)
    return {
        "ok": True,
        "tenant": tenant.to_dict(),
        "query": query,
        "hits": hits,
        "results": hits,
        "answer": answer.get("answer") or "",
        "grounded": bool(answer.get("grounded")),
        "citations": answer.get("citations") or [],
        "corpus": retrieval.index_for(tenant.tenant_id).stats(),
    }


@router.post("/v1/rag/query")
def rag_query(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    tenant = _tenant(request)
    data = payload if isinstance(payload, dict) else {}
    query = _query_of(data)
    if not query:
        raise HTTPException(status_code=422, detail="query is required")
    try:
        top_k = int(data.get("top_k") or 5)
    except (TypeError, ValueError):
        top_k = 5
    return _query(tenant, query, max(1, min(top_k, 25)))


@router.get("/v1/rag/query")
def rag_query_get(request: Request, q: str = "", top_k: int = 5) -> Dict[str, Any]:
    tenant = _tenant(request)
    if not str(q or "").strip():
        raise HTTPException(status_code=422, detail="query is required")
    return _query(tenant, str(q).strip(), max(1, min(int(top_k or 5), 25)))


@router.get("/v1/rag/stats")
def rag_stats(request: Request) -> Dict[str, Any]:
    tenant = _tenant(request)
    return {"ok": True, "tenant": tenant.to_dict(), "corpus": retrieval.index_for(tenant.tenant_id).stats()}
