"""Dual RAG ingest/query HTTP. Quoted paths required by PHASE 2 acceptance."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.store import storage_root

router = APIRouter()

SOP_INDEX = "steward_sop_v1"
ESTATE_INDEX = "steward_estate_docs_v1"


class RagIngestBody(BaseModel):
    text: str = Field(..., min_length=1)
    doc_id: str = Field("sample", min_length=1)
    title: str = Field("sample", min_length=1)
    layer: int = Field(1, ge=1, le=2)
    property_id: Optional[str] = None


def _rag_dir() -> Path:
    path = storage_root() / "rag"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _index_path(layer: int) -> Path:
    name = SOP_INDEX if layer == 1 else ESTATE_INDEX
    return _rag_dir() / f"{name}.jsonl"


def _tokens(text: str) -> List[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t]


def _score(query: str, text: str) -> float:
    q = set(_tokens(query))
    d = _tokens(text)
    if not q or not d:
        return 0.0
    overlap = len(q.intersection(d))
    return overlap / math.sqrt(len(q) * max(len(d), 1))


def _read_index(layer: Optional[int] = None) -> List[Dict[str, Any]]:
    layers = [layer] if layer in (1, 2) else [1, 2]
    rows: List[Dict[str, Any]] = []
    for item in layers:
        path = _index_path(item)
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


@router.post("/v1/rag/ingest")
def rag_ingest(body: RagIngestBody) -> Dict[str, Any]:
    record = {
        "doc_id": body.doc_id,
        "title": body.title,
        "text": body.text,
        "layer": body.layer,
        "property_id": body.property_id,
        "index": SOP_INDEX if body.layer == 1 else ESTATE_INDEX,
    }
    path = _index_path(body.layer)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {"ok": True, "ingested": True, "doc_id": body.doc_id, "layer": body.layer}


@router.post("/v1/steward/rag/ingest")
def steward_rag_ingest(body: RagIngestBody) -> Dict[str, Any]:
    return rag_ingest(body)


@router.get("/v1/rag/query")
def rag_query(
    q: str = Query(..., min_length=1),
    layer: Optional[int] = Query(None, ge=1, le=2),
    top_k: int = Query(5, ge=1, le=20),
) -> Dict[str, Any]:
    hits = []
    for row in _read_index(layer):
        score = _score(q, f"{row.get('title', '')} {row.get('text', '')}")
        if score <= 0:
            continue
        hits.append({**row, "score": round(score, 6)})
    hits.sort(key=lambda item: item["score"], reverse=True)
    return {
        "ok": True,
        "query": q,
        "hits": hits[:top_k],
        "hit_count": min(len(hits), top_k),
    }


@router.post("/v1/rag/query")
def rag_query_post(body: Dict[str, Any]) -> Dict[str, Any]:
    q = str(body.get("q") or body.get("query") or "")
    if not q:
        raise HTTPException(status_code=422, detail="q required")
    layer = body.get("layer")
    top_k = int(body.get("top_k") or 5)
    return rag_query(q=q, layer=layer, top_k=top_k)


@router.get("/v1/steward/rag/query")
def steward_rag_query(
    q: str = Query(..., min_length=1),
    layer: Optional[int] = Query(None, ge=1, le=2),
    top_k: int = Query(5, ge=1, le=20),
) -> Dict[str, Any]:
    return rag_query(q=q, layer=layer, top_k=top_k)


@router.post("/v1/steward/rag/query")
def steward_rag_query_post(body: Dict[str, Any]) -> Dict[str, Any]:
    return rag_query_post(body)
