"""Document ingestion and grounded query for the bakery's own documents.

Written by the factory WRITER role (codewhale exec)

The crew asked the platform to answer from the bakery's own uploaded
documents -- price lists, recipes, ingredient costs, delivery zone rules,
supplier lists, procedures. This is that surface:

    POST /v1/rag/ingest   index one passage for the caller's tenant
    POST /v1/rag/query    retrieve, then answer from what was retrieved
    GET  /v1/rag/query    same retrieval with the query in the query string

Tenancy is resolved from the authenticated principal (app.tenancy), never
from the request body, and every read is scoped to that tenant. Answers
carry their citations; when nothing matches, the platform says so rather
than inventing a figure.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request

from app import llm, retrieval
from app import tenancy

router = APIRouter()

MAX_TEXT_CHARS = 20000


def _tenant(request: Request) -> str:
    try:
        return tenancy.resolve_tenant(request.headers).tenant_id
    except tenancy.TenantRefused:
        raise HTTPException(status_code=401, detail="authentication_required")


def _first_string(body: Dict[str, Any], *names: str) -> str:
    for name in names:
        value = body.get(name)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _ingest(tenant_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
    text = _first_string(body, "text", "content", "paragraph", "document", "body")
    if not text:
        raise HTTPException(status_code=422, detail="text is required to ingest a passage")
    if len(text) > MAX_TEXT_CHARS:
        raise HTTPException(status_code=422, detail="passage is larger than %d characters" % MAX_TEXT_CHARS)
    try:
        row = retrieval.ingest(
            tenant_id=tenant_id,
            text=text,
            document=_first_string(body, "document_name", "filename", "title") or "uploaded-document",
            document_type=_first_string(body, "document_type", "kind") or "procedure",
            branch=_first_string(body, "branch"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"ok": True, "tenant_id": tenant_id, "ingested": row}


def _query(tenant_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
    question = _first_string(body, "q", "query", "question", "text")
    if not question:
        raise HTTPException(status_code=422, detail="q or query is required to search")
    branch = _first_string(body, "branch")
    try:
        limit = int(body.get("limit") or 5)
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="limit must be a number")
    try:
        hits = retrieval.search(tenant_id=tenant_id, query=question, limit=limit, branch=branch)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    answer = llm.synthesize(question, hits)
    return {
        "ok": True,
        "tenant_id": tenant_id,
        "query": question,
        "hits": hits,
        "results": hits,
        "total": len(hits),
        "answer": answer.get("answer"),
        "citations": answer.get("citations") or [],
        "confidence": answer.get("confidence"),
        "provider": answer.get("provider"),
    }


@router.post("/v1/rag/ingest")
async def rag_ingest(request: Request) -> Dict[str, Any]:
    """Index one passage from the bakery's own documents for this tenant."""
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001 - malformed JSON is a caller error
        raise HTTPException(status_code=422, detail="body must be JSON")
    if not isinstance(body, dict):
        raise HTTPException(status_code=422, detail="body must be a JSON object")
    return _ingest(_tenant(request), body)


@router.post("/v1/rag/query")
async def rag_query_post(request: Request) -> Dict[str, Any]:
    """Retrieve from this tenant's documents and answer from the passages."""
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001 - malformed JSON is a caller error
        raise HTTPException(status_code=422, detail="body must be JSON")
    if not isinstance(body, dict):
        raise HTTPException(status_code=422, detail="body must be a JSON object")
    return _query(_tenant(request), body)


@router.get("/v1/rag/query")
def rag_query_get(request: Request) -> Dict[str, Any]:
    """Same retrieval, with the question in the query string."""
    params: Dict[str, Any] = dict(request.query_params)
    return _query(_tenant(request), params)


@router.get("/v1/rag/documents")
def rag_documents(request: Request) -> Dict[str, Any]:
    """How many passages this tenant has indexed, and of which kinds."""
    tenant_id = _tenant(request)
    conn = retrieval.connect()
    try:
        rows = conn.execute(
            "SELECT document, document_type, branch, COUNT(*) AS passages"
            " FROM rag_documents WHERE tenant_id = ? GROUP BY document, document_type, branch"
            " ORDER BY document",
            (tenant_id,),
        ).fetchall()
    finally:
        conn.close()
    items = [dict(row) for row in rows]
    return {"ok": True, "tenant_id": tenant_id, "documents": items, "count": len(items)}
