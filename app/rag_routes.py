"""HTTP routes for the property's own documents: ingest and query.

Written by the factory WRITER role (codewhale exec)

    POST /v1/rag/ingest   plant a manual, SOP, rate sheet or policy
    POST /v1/rag/query    ask a question of this tenant's corpus
    GET  /v1/rag/query    the same query, by ?q=

Every answer carries its authority layer (precedence.v1) and its citations,
and the tenant is resolved from the platform token -- never from the body.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request

from app import authority, llm, retrieval

router = APIRouter(tags=["knowledge"])

KINDS = ("manual", "sop", "rate_sheet", "policy", "certified_standard", "other")


def _tenant(request: Request):
    from app.auth import require_platform_token

    return require_platform_token(request)


def _body(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return dict(payload or {})


def _text_of(payload: Dict[str, Any]) -> str:
    for key in ("text", "content", "document_text", "paragraph", "body"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


@router.post("/v1/rag/ingest")
def rag_ingest(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    tenant = _tenant(request)
    body = _body(payload)
    text = _text_of(body)
    if not text.strip():
        raise HTTPException(
            status_code=422,
            detail="Missing required field: text (or content/document_text)",
        )
    title = str(body.get("title") or body.get("name") or "").strip()
    if not title:
        title = text.strip().splitlines()[0][:120] if text.strip() else "untitled"
    kind = str(body.get("kind") or body.get("document_kind") or "other").strip().lower()
    if kind not in KINDS:
        raise HTTPException(
            status_code=422,
            detail="kind must be one of: " + ", ".join(KINDS),
        )
    authority_label = str(body.get("authority") or body.get("authority_label") or "documents").strip().lower()
    if authority_label not in authority.LABELS:
        raise HTTPException(
            status_code=422,
            detail="authority must be one of: " + ", ".join(authority.LABELS),
        )
    try:
        stored = retrieval.ingest(
            title=title,
            kind=kind,
            text=text,
            tenant_id=tenant.tenant_id,
            authority_label=authority_label,
            source_path=body.get("source_path") or body.get("attachment_path"),
        )
    except retrieval.RetrievalError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True, "capability": "document_and_knowledge_answers", **stored}


def _run_query(question: str, request: Request, top_k: int) -> Dict[str, Any]:
    tenant = _tenant(request)
    if not question.strip():
        raise HTTPException(status_code=422, detail="Missing required field: q")
    try:
        answer = llm.answer(question, tenant_id=tenant.tenant_id, top_k=top_k)
    except retrieval.RetrievalError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return answer


@router.post("/v1/rag/query")
def rag_query(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    body = _body(payload)
    question = ""
    for key in ("q", "query", "question"):
        value = body.get(key)
        if isinstance(value, str) and value.strip():
            question = value
            break
    try:
        top_k = int(body.get("top_k") or 4)
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="top_k must be an integer")
    return _run_query(question, request, top_k)


def _corpus_summary(tenant_id: str) -> Dict[str, Any]:
    """What this tenant has on file: count and layers, never another's."""
    from app.db import connect, is_postgres

    sql = (
        "SELECT id, title, kind, authority_label, created_at FROM rag_document"
        " WHERE tenant_id = ? ORDER BY id"
    )
    conn = connect()
    try:
        cur = conn.execute(sql.replace("?", "%s") if is_postgres() else sql, (tenant_id,))
        rows = cur.fetchall()
        items = []
        for row in rows:
            mapping = getattr(row, "_mapping", None)
            items.append(dict(mapping) if mapping is not None else dict(row))
    finally:
        conn.close()
    layers = sorted({str(item.get("authority_label") or "") for item in items} - {""})
    return {"items": items, "total": len(items), "layers": layers}


@router.get("/v1/rag/query")
def rag_query_get(request: Request, q: str = "", top_k: int = 4) -> Dict[str, Any]:
    """Ask this tenant's corpus, or describe the surface when no question is given.

    A GET with no ``q`` states what this surface answers FROM -- the
    precedence.v1 ladder, the layers this property's own corpus can supply,
    and the label an answer with no higher source would carry -- so an
    operator (or the console) can see which layer an answer comes from before
    asking. That is the same label every answer below carries.
    """
    if not q.strip():
        tenant = _tenant(request)
        return {
            "ok": True,
            "capability": "document_and_knowledge_answers",
            "question": None,
            "answers": [],
            "label": "documents",
            "authority": authority.ladder_document(),
            "corpus": _corpus_summary(tenant.tenant_id),
        }
    return _run_query(q, request, top_k)


@router.get("/v1/rag/corpus")
def rag_corpus(request: Request) -> Dict[str, Any]:
    """What this tenant has uploaded -- count and layers, never another's."""
    tenant = _tenant(request)
    return {"ok": True, **_corpus_summary(tenant.tenant_id)}
