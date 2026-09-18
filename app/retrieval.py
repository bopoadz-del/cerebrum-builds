"""Tenant-scoped corpus retrieval, offline and deterministic.

Written by the factory WRITER role (codewhale exec)

Every corpus read and write goes through the tenant resolved from the
authenticated principal -- there is no client-supplied tenant on any path.
Ranking is lexical (token overlap with a certified-source boost), computed in
process: no embedding service, no network, no vector database. The vendored
``knowledge`` slice that would have provided RAG could not be bound in this
checkout (see docs/blockers.json); this module is the platform's own honest
retrieval path for the corpus routes.

Scope
-----
READS  ``corpus_documents`` rows for the bound tenant.
WRITES exactly ONE ``corpus_documents`` row per ingest.
NEVER  network; another tenant's rows; a tenant named by the caller.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.store import connect

TABLE = "corpus_documents"
SOURCE_KINDS = ("document", "certified", "procedure")
_TOKEN_RE = re.compile(r"[a-z0-9]+")


class CorpusRefused(ValueError):
    """The ingest request violated the corpus contract."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def tokens(text: str) -> List[str]:
    return _TOKEN_RE.findall(str(text or "").lower())


def ingest(
    *,
    tenant: str,
    title: str,
    body: str,
    source_kind: str = "document",
    certified: bool = False,
    version: str = "1.0.0",
) -> Dict[str, Any]:
    """Store one document for one tenant. Returns the stored row."""
    tenant = str(tenant or "").strip()
    title = str(title or "").strip()
    body = str(body or "")
    kind = str(source_kind or "document").strip().lower()
    if not tenant:
        raise CorpusRefused("a tenant is required")
    if not title:
        raise CorpusRefused("title is required")
    if not body.strip():
        raise CorpusRefused("body is required")
    if kind not in SOURCE_KINDS:
        raise CorpusRefused("source_kind must be one of: " + ", ".join(SOURCE_KINDS))
    layer = "certified" if (certified or kind == "certified") else "document"
    conn = connect()
    try:
        cur = conn.execute(
            "INSERT INTO corpus_documents "
            "(tenant_id, title, body, source_kind, layer, certified, version, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (tenant, title, body, kind, layer, 1 if certified else 0, str(version), _now()),
        )
        conn.commit()
        return {
            "id": cur.lastrowid,
            "tenant_id": tenant,
            "title": title,
            "source_kind": kind,
            "layer": layer,
            "certified": bool(certified),
            "version": str(version),
            "created_at": _now(),
        }
    finally:
        conn.close()


def list_documents(tenant: str) -> Dict[str, Any]:
    """This tenant's documents only. Another tenant's rows are invisible."""
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT * FROM corpus_documents WHERE tenant_id = ? ORDER BY id",
            (str(tenant),),
        ).fetchall()
        return {"items": [dict(r) for r in rows], "total": len(rows)}
    finally:
        conn.close()


def _score(query_tokens: List[str], row: Dict[str, Any]) -> float:
    haystack = set(tokens(row.get("title"))) | set(tokens(row.get("body")))
    if not query_tokens:
        return 0.0
    overlap = sum(1 for token in set(query_tokens) if token in haystack)
    score = overlap / float(len(set(query_tokens)))
    if str(row.get("layer")) == "certified":
        score += 0.25
    return round(score, 4)


def search(tenant: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Rank this tenant's corpus against a query. Lexical, in-process."""
    query_tokens = tokens(query)
    rows = list_documents(tenant)["items"]
    scored = []
    for row in rows:
        score = _score(query_tokens, row)
        if score <= 0:
            continue
        scored.append((score, row))
    scored.sort(key=lambda item: (-item[0], item[1]["id"]))
    out = []
    for score, row in scored[: max(1, int(limit))]:
        out.append(
            {
                "id": row["id"],
                "title": row["title"],
                "excerpt": str(row.get("body") or "")[:400],
                "layer": row.get("layer"),
                "source_kind": row.get("source_kind"),
                "certified": bool(row.get("certified")),
                "version": row.get("version"),
                "score": score,
            }
        )
    return out


def get(tenant: str, document_id: int) -> Optional[Dict[str, Any]]:
    conn = connect()
    try:
        row = conn.execute(
            "SELECT * FROM corpus_documents WHERE tenant_id = ? AND id = ?",
            (str(tenant), int(document_id)),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()
