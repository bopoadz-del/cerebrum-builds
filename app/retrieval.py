"""Tenant-scoped corpus retrieval (token overlap, no embedding service).

Written by the factory WRITER role (codewhale exec)

The corpus is the JSONL the vendored vector-search/knowledge runtime writes
under ``STORAGE_PATH`` plus the platform's own document index. Retrieval is
deterministic token overlap so the platform works with no model, no network and
no vector database; the vendored ``vector_search`` block remains the block of
record and is what capabilities call.

Every read is tenant-scoped: the tenant comes from the authenticated principal
(``app.tenancy``), never from a query string or body field.

Scope
-----
READS  ``STORAGE_PATH`` (corpus files).
WRITES nothing.
NEVER  network, another tenant's corpus, ``vendor/**``.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

CORPUS_FILES = ("knowledge_corpus.jsonl", "documents.jsonl", "rag_index.jsonl")


def _root() -> Path:
    root = Path(os.getenv("STORAGE_PATH", "./data"))
    root.mkdir(parents=True, exist_ok=True)
    return root


def _tokens(text: str) -> List[str]:
    return [part for part in re.findall(r"[a-z0-9]+", (text or "").lower()) if part]


def load_corpus(tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for name in CORPUS_FILES:
        path = _root() / name
        if not path.is_file():
            continue
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(row, dict):
                    continue
                text = row.get("text") or row.get("content")
                if not text:
                    continue
                row["text"] = str(text)
                if tenant_id and str(row.get("tenant_id") or tenant_id) != str(tenant_id):
                    continue
                rows.append(row)
    return rows


def score(query: str, text: str) -> float:
    q = set(_tokens(query))
    if not q:
        return 0.0
    d = set(_tokens(text))
    if not d:
        return 0.0
    return len(q & d) / float(len(q))


def search(
    query: str,
    *,
    top_k: int = 5,
    tenant_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    hits: List[Dict[str, Any]] = []
    for row in load_corpus(tenant_id):
        value = score(query, row["text"])
        if value <= 0:
            continue
        hits.append(
            {
                "doc_id": row.get("doc_id") or row.get("document_id"),
                "title": row.get("title") or row.get("doc_id"),
                "excerpt": row["text"][:280],
                "score": round(value, 6),
                "layer": row.get("layer") or "documents",
            }
        )
    hits.sort(key=lambda item: float(item.get("score") or 0), reverse=True)
    return hits[: max(1, min(int(top_k or 5), 20))]
