"""Tenant-scoped retrieval over the property's own documents.

Written by the factory WRITER role (codewhale exec)

The corpus is the platform's own database (alembic revision
``0003_rag_corpus``): one row per document, one row per chunk. Every query is
scoped by the tenant resolved from the authenticated principal, so a
property's SOPs are invisible to another property -- the same rule app/store.py
applies to capability records.

Ranking is lexical (term frequency with inverse document frequency, computed
over the tenant's own chunks) rather than an embedding service: the platform
is offline by contract, and a shipped-on-first-boot model download is the
kind of hidden network dependency this build refuses. Every hit carries the
document it came from and that document's authority layer (precedence.v1).

When nothing matches, the result is EMPTY -- never a fabrication. The caller
(``app.llm``) refuses in that case rather than answering from memory.
"""

from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from app import authority
from app.db import connect, is_postgres

CHUNK_TARGET = 420

_WORD = re.compile(r"[a-z0-9][a-z0-9\-']+")
_STOP = frozenset(
    """a an and are as at be by for from in is it of on or that the to was were
    with this those these shall should must may can will not no if then than
    over under into out up down we you they he she them their our its""".split()
)


class RetrievalError(RuntimeError):
    """The corpus refused a request. The message names the reason."""


def tokenize(text: Any) -> List[str]:
    raw = "" if text is None else str(text)
    return [word for word in _WORD.findall(raw.lower()) if word not in _STOP]


def _sql(sql: str) -> str:
    return sql.replace("?", "%s") if is_postgres() else sql


def _rows(conn: Any, sql: str, params: Sequence[Any]) -> List[Dict[str, Any]]:
    cur = conn.execute(_sql(sql), tuple(params))
    rows = cur.fetchall()
    out: List[Dict[str, Any]] = []
    for row in rows:
        mapping = getattr(row, "_mapping", None)
        out.append(dict(mapping) if mapping is not None else dict(row))
    return out


def chunk_text(text: str, target: int = CHUNK_TARGET) -> List[str]:
    """Paragraph-aware chunking: whitespace-normalised, never empty."""
    normalised = re.sub(r"\s+", " ", str(text or "")).strip()
    if not normalised:
        return []
    paragraphs = [p.strip() for p in re.split(r"(?<=[.!?])\s{1,2}", normalised) if p.strip()]
    chunks: List[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current} {paragraph}".strip() if current else paragraph
        if len(candidate) <= target or not current:
            current = candidate
            if len(current) >= target:
                chunks.append(current)
                current = ""
            continue
        chunks.append(current)
        current = paragraph
    if current:
        chunks.append(current)
    return chunks or [normalised[:target]]


def ingest(
    *,
    title: str,
    kind: str,
    text: str,
    tenant_id: str,
    authority_label: str = "documents",
    source_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Store one document and its chunks for one tenant."""
    tenant = str(tenant_id or "").strip()
    if not tenant:
        raise RetrievalError("tenant_id is required: tenancy is never inferred")
    clean_title = str(title or "").strip() or "untitled document"
    label = str(authority_label or "documents").strip().lower()
    if label not in authority.LABELS:
        raise RetrievalError(
            "unknown authority layer "
            f"{label!r}; expected one of {', '.join(authority.LABELS)}"
        )
    chunks = chunk_text(text)
    if not chunks:
        raise RetrievalError("document text is empty: nothing to ingest")
    created = datetime.now(timezone.utc).isoformat()
    conn = connect()
    try:
        cur = conn.execute(
            _sql(
                "INSERT INTO rag_document (tenant_id, title, kind, authority_label,"
                " source_path, created_at) VALUES (?, ?, ?, ?, ?, ?)"
            ),
            (tenant, clean_title, str(kind or "other"), label, source_path, created),
        )
        mapping = getattr(cur, "lastrowid", None)
        conn.commit()
        if mapping is None:
            row = _rows(
                conn,
                "SELECT id FROM rag_document WHERE tenant_id = ? ORDER BY id DESC LIMIT 1",
                [tenant],
            )
            mapping = (row[0] if row else {}).get("id")
        document_id = mapping
        for ordinal, chunk in enumerate(chunks):
            terms = " ".join(sorted(set(tokenize(chunk))))
            conn.execute(
                _sql(
                    "INSERT INTO rag_chunk (tenant_id, document_id, ordinal, text, terms)"
                    " VALUES (?, ?, ?, ?, ?)"
                ),
                (tenant, document_id, ordinal, chunk, terms),
            )
        conn.commit()
    finally:
        conn.close()
    return {
        "ok": True,
        "document_id": document_id,
        "title": clean_title,
        "kind": str(kind or "other"),
        "authority": label,
        "chunks": len(chunks),
        "tenant_id": tenant,
    }


def corpus_terms(tenant_id: str) -> Tuple[Dict[str, int], int]:
    """Document frequency per term and the chunk count, for this tenant only."""
    conn = connect()
    try:
        rows = _rows(
            conn,
            "SELECT terms FROM rag_chunk WHERE tenant_id = ?",
            [tenant_id],
        )
    finally:
        conn.close()
    df: Dict[str, int] = {}
    for row in rows:
        for term in set(str(row.get("terms") or "").split()):
            df[term] = df.get(term, 0) + 1
    return df, len(rows)


def search(query: Any, tenant_id: str, top_k: int = 5) -> Dict[str, Any]:
    """Rank this tenant's chunks against a query. Empty when nothing matches."""
    tenant = str(tenant_id or "").strip()
    if not tenant:
        raise RetrievalError("tenant_id is required: tenancy is never inferred")
    terms = set(tokenize(query))
    limit = max(1, min(int(top_k or 5), 20))
    if not terms:
        return {"ok": True, "query": str(query or ""), "hits": [], "chunks_scanned": 0}
    df, total = corpus_terms(tenant)
    conn = connect()
    try:
        rows = _rows(
            conn,
            "SELECT c.id AS chunk_id, c.text AS chunk_text, c.ordinal AS ordinal,"
            " d.id AS document_id, d.title AS title, d.kind AS kind,"
            " d.authority_label AS authority_label, d.source_path AS source_path"
            " FROM rag_chunk c JOIN rag_document d ON d.id = c.document_id"
            " WHERE c.tenant_id = ? ORDER BY c.id",
            [tenant],
        )
    finally:
        conn.close()
    scored: List[Dict[str, Any]] = []
    for row in rows:
        chunk_terms = set(str(row.get("chunk_text") or "").lower().split())
        overlap = terms & {t for t in chunk_terms if t in terms}
        if not overlap:
            continue
        score = 0.0
        for term in overlap:
            idf = math.log((total + 1) / (df.get(term, 0) + 1)) + 1.0
            score += idf
        scored.append(
            {
                "document_id": row.get("document_id"),
                "chunk_id": row.get("chunk_id"),
                "title": row.get("title"),
                "kind": row.get("kind"),
                "authority": row.get("authority_label"),
                "rank": authority.rank_of(row.get("authority_label")),
                "score": round(score, 4),
                "text": row.get("chunk_text"),
            }
        )
    scored.sort(key=lambda item: (-item["score"], item["rank"], item["chunk_id"]))
    return {
        "ok": True,
        "query": str(query or ""),
        "hits": scored[:limit],
        "chunks_scanned": len(rows),
    }
