"""HTTP surface for the front-desk knowledge corpus (ingest + query).

Written by the factory WRITER role (codewhale exec)

The desk's reference documents (house rules, room inventory notes, shift
handovers) are ingested here and retrieved here. Both routes are the tenant's
own corpus: the tenant is bound from the authenticated principal
(``app.security`` + ``app.tenancy``), never from the request, and the rows
live in the same single ``STORAGE_PATH`` database as the check-in log.

Retrieval is the deterministic keyword-scored scan in ``app.retrieval`` -- no
embedding service and no network, which is what keeps the platform offline.

Scope
-----
READS  ``corpus_documents`` / ``corpus_chunks`` for the bound tenant.
WRITES one document plus its chunks per ingest (through app.retrieval).
NEVER  network, another tenant's rows, ``vendor/**``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request

from app import retrieval, tenancy
from app.security import authenticate

router = APIRouter(tags=["rag"])

#: The desk's own vocabulary for a corpus document.
DEFAULT_TITLE = "front-desk note"
DEFAULT_SOURCE_KIND = "document"


def _bound_tenant(request: Request) -> str:
    """The tenant of the authenticated principal in flight."""
    principal = authenticate(request)
    tenancy.refuse_tenant_spoof(request, principal)
    return principal.tenant


def _first_text(payload: Dict[str, Any], keys: List[str]) -> str:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def _ingest_body(payload: Optional[Dict[str, Any]], query: Optional[str]) -> str:
    body = payload if isinstance(payload, dict) else {}
    text = _first_text(body, ["text", "content", "body", "paragraph", "document", "note"])
    if not text and query:
        text = str(query)
    return text


@router.post("/v1/rag/ingest")
def rag_ingest(payload: Optional[Dict[str, Any]] = None, request: Request = None) -> Dict[str, Any]:
    """Ingest one front-desk document into the tenant's corpus."""
    tenant = _bound_tenant(request)
    body = payload if isinstance(payload, dict) else {}
    text = _ingest_body(body, None)
    if not text.strip():
        return {
            "ok": False,
            "error": "ingest requires a document body (text, content, paragraph)",
        }
    title = _first_text(body, ["title", "name", "subject"]) or DEFAULT_TITLE
    source_kind = _first_text(body, ["source_kind", "kind"]) or DEFAULT_SOURCE_KIND
    certified = bool(body.get("certified") is True)
    with tenancy.bind(tenant):
        try:
            stored = retrieval.ingest(
                tenant=tenant,
                title=title,
                body=text,
                source_kind=source_kind,
                certified=certified,
            )
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}
    return {"ok": True, "tenant": tenant, "rag": stored, "items": [stored]}


@router.post("/v1/rag/query")
def rag_query_post(payload: Optional[Dict[str, Any]] = None, request: Request = None) -> Dict[str, Any]:
    """Retrieve the tenant's own chunks for a question."""
    body = payload if isinstance(payload, dict) else {}
    question = _first_text(body, ["q", "query", "question", "text"])
    limit = body.get("limit")
    return _query(request, question, limit)


@router.get("/v1/rag/query")
def rag_query_get(request: Request, q: Optional[str] = None, limit: Optional[int] = None) -> Dict[str, Any]:
    """Same retrieval, addressable with ``?q=``."""
    return _query(request, q or "", limit)


def _query(request: Request, question: str, limit: Any) -> Dict[str, Any]:
    tenant = _bound_tenant(request)
    if not str(question or "").strip():
        return {"ok": False, "error": "query requires q or query", "hits": [], "total": 0}
    try:
        resolved_limit = int(limit) if limit not in (None, "") else 5
    except (TypeError, ValueError):
        return {"ok": False, "error": "limit must be an integer", "hits": [], "total": 0}
    with tenancy.bind(tenant):
        hits = retrieval.retrieve(str(question), tenant=tenant, limit=resolved_limit)
    return {
        "ok": True,
        "tenant": tenant,
        "query": str(question),
        "hits": hits,
        "total": len(hits),
        "documents": retrieval.list_documents(tenant),
    }
