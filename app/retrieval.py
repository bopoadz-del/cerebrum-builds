"""Tenant-scoped corpus retrieval.

Written by the factory WRITER role (codewhale exec)

Documents are ingested per tenant and chunked; retrieval is a keyword-scored
scan over that tenant's chunks only. The tenant is bound from the authenticated
principal (``app.tenancy``) -- never from a client-supplied name -- so one
customer's corpus can never answer another customer's question.

Scoring is deterministic (term frequency with a length normalisation) so an
answer can be reproduced and audited; no embedding service and no network are
involved, which is what makes the platform runnable offline.

Scope
-----
READS  ``corpus_documents`` / ``corpus_chunks`` for the bound tenant.
WRITES one document plus its chunks per ingest; one ``answer_log`` row per
       answered question (through app.llm).
NEVER  network, another tenant's rows, ``vendor/**``.
"""

from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app import authority, tenancy
from app.store import connect

TOKEN_RE = re.compile(r"[a-z0-9]+")
#: Chunk size in words -- small enough to cite, large enough to mean something.
CHUNK_WORDS = 120


def tokenize(text: str) -> List[str]:
    return TOKEN_RE.findall(str(text or "").lower())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def chunks_of(body: str, size: int = CHUNK_WORDS) -> List[str]:
    words = str(body or "").split()
    if not words:
        return []
    return [" ".join(words[i : i + size]) for i in range(0, len(words), size)]


def ingest(
    *,
    tenant: str,
    title: str,
    body: str,
    source_kind: str = "document",
    certified: bool = False,
    version: str = "1.0.0",
    connection: Optional[Any] = None,
) -> Dict[str, Any]:
    """Ingest one document for one tenant. Refuses an unknown source kind."""
    tenant_id = str(tenant or "").strip()
    if not tenant_id:
        raise ValueError("tenant required")
    layer = authority.layer_of(source_kind, certified=certified)
    conn = connection or connect()
    try:
        cur = conn.execute(
            "INSERT INTO corpus_documents "
            "(tenant, title, layer, source_kind, certified, version, body, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                tenant_id,
                str(title)[:300],
                int(layer),
                str(source_kind),
                1 if certified else 0,
                str(version),
                str(body),
                _now(),
            ),
        )
        document_id = cur.lastrowid
        pieces = chunks_of(body)
        for ordinal, text in enumerate(pieces):
            conn.execute(
                "INSERT INTO corpus_chunks (tenant, document_id, ordinal, text) VALUES (?, ?, ?, ?)",
                (tenant_id, document_id, ordinal, text),
            )
        conn.commit()
        return {
            "document_id": document_id,
            "tenant": tenant_id,
            "title": title,
            "layer": layer,
            "layer_name": authority.LAYER_NAMES.get(layer, "unknown"),
            "chunks": len(pieces),
            "certified": bool(certified),
        }
    finally:
        if connection is None:
            conn.close()


def list_documents(tenant: str) -> Dict[str, Any]:
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT id, tenant, title, layer, source_kind, certified, version, created_at "
            "FROM corpus_documents WHERE tenant = ? ORDER BY id DESC",
            (str(tenant),),
        ).fetchall()
        return {"items": [dict(row) for row in rows], "total": len(rows)}
    finally:
        conn.close()


def retrieve(query: str, *, tenant: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
    """Keyword-scored chunks from this tenant's corpus, best first."""
    tenant_id = tenant or tenancy.current_tenant()
    terms = tokenize(query)
    if not terms:
        return []
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT c.id, c.text, c.document_id, d.title, d.layer, d.source_kind, d.certified "
            "FROM corpus_chunks c JOIN corpus_documents d ON d.id = c.document_id "
            "WHERE c.tenant = ? AND d.tenant = ?",
            (tenant_id, tenant_id),
        ).fetchall()
    finally:
        conn.close()
    scored: List[Dict[str, Any]] = []
    for row in rows:
        text = str(row["text"])
        words = tokenize(text)
        if not words:
            continue
        counts: Dict[str, int] = {}
        for word in words:
            counts[word] = counts.get(word, 0) + 1
        overlap = [term for term in terms if term in counts]
        if not overlap:
            continue
        score = sum(counts[term] for term in overlap) / math.sqrt(len(words))
        scored.append(
            {
                "chunk_id": row["id"],
                "document_id": row["document_id"],
                "title": row["title"],
                "layer": row["layer"],
                "source_kind": row["source_kind"],
                "certified": bool(row["certified"]),
                "matched_terms": sorted(set(overlap)),
                "score": round(score, 6),
                "text": text,
            }
        )
    scored.sort(key=lambda item: (-item["score"], item["layer"], item["chunk_id"]))
    return scored[: max(1, int(limit))]


def log_answer(
    *,
    tenant: str,
    question: str,
    answer: str,
    winner_source: str,
    labels: Any,
    divergences: Any,
    connection: Optional[Any] = None,
) -> int:
    conn = connection or connect()
    try:
        cur = conn.execute(
            "INSERT INTO answer_log "
            "(tenant, question, answer, winner_source, labels, divergences, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                str(tenant),
                str(question),
                str(answer),
                str(winner_source),
                json.dumps(labels, default=str),
                json.dumps(divergences, default=str),
                _now(),
            ),
        )
        if connection is None:
            conn.commit()
        return int(cur.lastrowid or 0)
    finally:
        if connection is None:
            conn.close()
