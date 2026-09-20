"""RAG ingest/query HTTP surface for the FleetOps Back-Office Platform.

Written by the factory WRITER role (codewhale exec)

Routes:
  POST /v1/rag/ingest   -- plant a document (or a list) into a collection
  POST /v1/rag/query    -- ranked retrieval over that collection
  GET  /v1/rag/query    -- same, for a ?q= probe

No network, no external vector database: retrieval runs in-process over the
durable corpus in :mod:`app.retrieval`. Documents are optional at launch (the
operator has nothing to upload yet), so an empty corpus answers an empty hit
list rather than an error.
"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Request

from app.retrieval import RetrievalError, ingest, query

router = APIRouter(tags=["rag"])


def _texts(payload: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    for key in ("text", "content", "paragraph", "document"):
        value = (payload or {}).get(key)
        if isinstance(value, str) and value.strip():
            out.append(value)
    documents = (payload or {}).get("documents")
    if isinstance(documents, list):
        for item in documents:
            if isinstance(item, str) and item.strip():
                out.append(item)
            elif isinstance(item, dict):
                inner = item.get("text") or item.get("content")
                if isinstance(inner, str) and inner.strip():
                    out.append(inner)
    unique: List[str] = []
    for item in out:
        if item not in unique:
            unique.append(item)
    return unique


@router.post("/v1/rag/ingest")
def rag_ingest(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """Plant one or more documents. Persistence is the corpus, not the store."""
    from app.auth import require_platform_token

    require_platform_token(request)
    body = payload if isinstance(payload, dict) else {}
    texts = _texts(body)
    if not texts:
        return {"ok": False, "error": "text (or content) is required"}
    collection = str(body.get("collection") or "default")
    reference = str(body.get("reference") or "")
    metadata = body.get("metadata") if isinstance(body.get("metadata"), dict) else {}
    ids: List[str] = []
    chunks = 0
    try:
        for text in texts:
            result = ingest(
                text=text,
                collection=collection,
                reference=reference,
                metadata=metadata,
            )
            ids.extend(result["ids"])
            chunks += int(result["chunks"])
    except RetrievalError as exc:
        return {"ok": False, "error": str(exc)}
    return {
        "ok": True,
        "collection": collection,
        "documents": len(texts),
        "chunks": chunks,
        "ids": ids,
    }


@router.post("/v1/rag/query")
def rag_query_post(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token

    require_platform_token(request)
    body = payload if isinstance(payload, dict) else {}
    return _query(body.get("q") or body.get("query") or body.get("text") or "", body)


@router.get("/v1/rag/query")
def rag_query_get(request: Request) -> Dict[str, Any]:
    from app.auth import require_platform_token

    require_platform_token(request)
    params = dict(request.query_params)
    return _query(params.get("q") or params.get("query") or "", params)


def _authority(collection: str) -> Dict[str, Any]:
    """The layer a retrieved answer came from: the document layer.

    Corpus answers are document-layer evidence (rank 2 of precedence.v1).
    The label travels with the answer so an operator can see which layer
    produced it rather than taking the platform's word for it.
    """
    from app.authority import claim_label

    return {**claim_label("documents"), "collection": collection}


def _query(needle: Any, body: Dict[str, Any]) -> Dict[str, Any]:
    collection = str((body or {}).get("collection") or "default")
    try:
        top_k = int((body or {}).get("top_k") or 5)
    except (TypeError, ValueError):
        top_k = 5
    try:
        answer = query(q=str(needle or ""), collection=collection, top_k=top_k)
    except RetrievalError as exc:
        return {"ok": False, "error": str(exc)}
    label = _authority(collection)
    hits = [
        {**hit, "authority": label}
        for hit in (answer.get("hits") or [])
    ]
    return {**answer, "hits": hits, "results": hits, "authority": label}
