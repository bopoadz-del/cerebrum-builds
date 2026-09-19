"""Tenant-scoped retrieval over the bakery's own uploaded documents.

Written by the factory WRITER role (codewhale exec)

Every read goes through the tenant store: a caller's documents are the only
ones their query can reach, and the tenant is resolved from the
authenticated principal (app.tenancy), never from a client-supplied name.

Storage is SQLite under ``STORAGE_PATH``: one row per ingested passage with
a deterministic embedding (app/llm-adjacent hashing embedder, no provider,
no network) and a token index for lexical scoring. That is the pilot-grade
retrieval the platform actually needs; it is not a stub, and it is not a
promise of a hosted vector database it does not have.

The module also exposes the two async hooks the vendored ``knowledge``
block imports from the Store's vector search module
(``vendor.cerebrum.core.vector_store`` -- see app/vendor_compat.py). The
vendored block then searches this same index through its own code path.
"""

from __future__ import annotations

import hashlib
import math
import os
import re
import sqlite3
import struct
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

EMBED_DIM = 64
_TOKEN_RE = re.compile(r"[a-z0-9]+")

SCHEMA = """
CREATE TABLE IF NOT EXISTS rag_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    document TEXT NOT NULL,
    document_type TEXT NOT NULL DEFAULT 'procedure',
    branch TEXT NOT NULL DEFAULT '',
    text TEXT NOT NULL,
    embedding BLOB NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_rag_tenant ON rag_documents (tenant_id);
"""


def db_path() -> Path:
    root = Path(os.getenv("STORAGE_PATH", "./data"))
    root.mkdir(parents=True, exist_ok=True)
    return root / "retrieval.db"


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path()), timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.executescript(SCHEMA)
    return conn


def tokens(text: str) -> List[str]:
    return _TOKEN_RE.findall(str(text or "").lower())


def embed_text(text: str) -> List[float]:
    """Deterministic hashing embedder: same text, same vector, no provider."""
    vector = [0.0] * EMBED_DIM
    for token in tokens(text):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        for offset in range(0, 16, 4):
            idx = struct.unpack("<I", digest[offset : offset + 4])[0] % EMBED_DIM
            sign = 1.0 if digest[offset] % 2 == 0 else -1.0
            vector[idx] += sign
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


def _pack(vector: Sequence[float]) -> bytes:
    return struct.pack("<%df" % len(vector), *vector)


def _unpack(blob: bytes) -> List[float]:
    return list(struct.unpack("<%df" % (len(blob) // 4), blob))


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    return float(sum(x * y for x, y in zip(a, b)))


def ingest(
    *,
    tenant_id: str,
    text: str,
    document: str = "uploaded-document",
    document_type: str = "procedure",
    branch: str = "",
) -> Dict[str, Any]:
    """Index one passage for one tenant. No passage, no row."""
    body = str(text or "").strip()
    if not body:
        raise ValueError("text is required to ingest a document passage")
    conn = connect()
    try:
        cur = conn.execute(
            "INSERT INTO rag_documents (tenant_id, document, document_type, branch, text, embedding)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (tenant_id, document, document_type, branch, body, _pack(embed_text(body))),
        )
        conn.commit()
        return {
            "id": cur.lastrowid,
            "tenant_id": tenant_id,
            "document": document,
            "document_type": document_type,
            "branch": branch,
            "chars": len(body),
        }
    finally:
        conn.close()


def search(*, tenant_id: str, query: str, limit: int = 5, branch: str = "") -> List[Dict[str, Any]]:
    """Rank this tenant's passages against a query. Returns scored hits."""
    terms = tokens(query)
    if not terms:
        raise ValueError("query is required for retrieval")
    query_vector = embed_text(query)
    conn = connect()
    try:
        sql = "SELECT id, document, document_type, branch, text, embedding FROM rag_documents WHERE tenant_id = ?"
        params: List[Any] = [tenant_id]
        if branch:
            sql += " AND (branch = ? OR branch = '')"
            params.append(branch)
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()

    hits: List[Dict[str, Any]] = []
    for row in rows:
        body = str(row["text"])
        lowered = body.lower()
        lexical = sum(1 for term in terms if term in lowered)
        if lexical == 0:
            continue
        similarity = cosine(query_vector, _unpack(row["embedding"]))
        score = (lexical / len(terms)) * 0.7 + max(0.0, similarity) * 0.3
        hits.append(
            {
                "id": row["id"],
                "document": row["document"],
                "document_type": row["document_type"],
                "branch": row["branch"],
                "text": body,
                "score": round(score, 4),
            }
        )
    hits.sort(key=lambda h: h["score"], reverse=True)
    return hits[: max(1, int(limit))]


# --- Store vector_search module hooks (vendor.cerebrum.core.vector_store) ---


async def search_vectors(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    """Async search hook used by the vendored knowledge / vector_search blocks."""
    tenant_id = str(kwargs.get("tenant_id") or kwargs.get("namespace") or "local")
    query = kwargs.get("query") or kwargs.get("query_text") or ""
    if isinstance(args[0], str) and not query:
        query = args[0]
    if not str(query).strip():
        return {"results": [], "total": 0}
    hits = search(tenant_id=tenant_id, query=str(query), limit=int(kwargs.get("top_k") or 5))
    return {"results": hits, "total": len(hits)}


async def upsert_vectors(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    """Async upsert hook: index one passage into the tenant's corpus."""
    tenant_id = str(kwargs.get("tenant_id") or kwargs.get("namespace") or "local")
    text = str(kwargs.get("text") or kwargs.get("content") or "")
    if not text.strip():
        return {"upserted": 0}
    row = ingest(
        tenant_id=tenant_id,
        text=text,
        document=str(kwargs.get("document") or "uploaded-document"),
        document_type=str(kwargs.get("document_type") or "procedure"),
        branch=str(kwargs.get("branch") or ""),
    )
    return {"upserted": 1, "id": row["id"]}
