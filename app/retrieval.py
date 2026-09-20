"""Document retrieval for the FleetOps Back-Office Platform.

Written by the factory WRITER role (codewhale exec)

Scope
  READS   the caller's query, the corpus under STORAGE_PATH/rag, and the
          platform's own token/hash vocabulary.
  WRITES  corpus chunks during ingest; the caller's response during query.
  NEVER   network, an external vector database, or an LLM call.

Why the platform owns this instead of binding the Store ``vector_search``
block: that block is reachable through ``app.dispatch.execute`` for its
``search`` action only -- its ``add`` action needs ``params.operation``, and
the dispatch contract refuses params the block's ``block.json`` does not
declare. A search-only bind cannot be given a corpus, so the retrieval surface
is implemented here over a durable local corpus. The Store block remains bound
at the ``reporting_analytics`` capability as the plan assigns it.

Ranking is deterministic: character-trigram cosine similarity over the
chunk/query pair, blended with exact-token overlap. A query that shares
nothing with the corpus scores zero and returns no hits -- the negative
control that tells retrieval apart from a request echo.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

CHUNK_CHARS = 800
CHUNK_OVERLAP = 120
MIN_SCORE = 0.05
TOKEN_RE = re.compile(r"[a-z0-9]+")


class RetrievalError(ValueError):
    """An ingest/query the surface must refuse rather than guess at."""


def corpus_root() -> Path:
    """The RAG corpus lives INSIDE the one storage root.

    Resolved through app.db.storage_root() -- the single place that decides
    where this deployment keeps its files -- so an unset STORAGE_PATH puts
    the corpus under the default root (./data/rag) rather than in a bare
    ./rag beside the database: two roots is how a backup misses a corpus.
    """
    from app import db as _db

    return _db.storage_root() / "rag"


def corpus_path(collection: str = "default") -> Path:
    safe = re.sub(r"[^a-z0-9_-]+", "-", str(collection or "default").lower()).strip("-")
    return corpus_root() / ("%s.jsonl" % (safe or "default"))


def _chunks(text: str) -> List[str]:
    body = str(text or "").strip()
    if not body:
        return []
    if len(body) <= CHUNK_CHARS:
        return [body]
    out: List[str] = []
    start = 0
    while start < len(body):
        out.append(body[start:start + CHUNK_CHARS])
        if start + CHUNK_CHARS >= len(body):
            break
        start += CHUNK_CHARS - CHUNK_OVERLAP
    return out


def _tokens(text: str) -> List[str]:
    return TOKEN_RE.findall(str(text or "").lower())


def _trigrams(text: str) -> Dict[str, int]:
    body = " " + str(text or "").lower() + " "
    out: Dict[str, int] = {}
    for i in range(len(body) - 2):
        gram = body[i:i + 3]
        out[gram] = out.get(gram, 0) + 1
    return out


def _cosine(left: Dict[str, int], right: Dict[str, int]) -> float:
    if not left or not right:
        return 0.0
    shared = set(left) & set(right)
    if not shared:
        return 0.0
    dot = sum(left[g] * right[g] for g in shared)
    norm_l = math.sqrt(sum(v * v for v in left.values()))
    norm_r = math.sqrt(sum(v * v for v in right.values()))
    if not norm_l or not norm_r:
        return 0.0
    return dot / (norm_l * norm_r)


def ingest(
    *,
    text: str = "",
    collection: str = "default",
    reference: str = "",
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Chunk one document into the durable corpus and return its chunk ids."""
    body = str(text or "").strip()
    if not body:
        raise RetrievalError("text is required")
    pieces = _chunks(body)
    if not pieces:
        raise RetrievalError("text produced no chunks")
    path = corpus_path(collection)
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    added: List[str] = []
    with path.open("a", encoding="utf-8") as handle:
        for index, piece in enumerate(pieces):
            digest = hashlib.sha256(
                ("%s|%d|%s" % (reference, index, piece)).encode("utf-8")
            ).hexdigest()[:16]
            record = {
                "id": digest,
                "collection": collection,
                "reference": reference,
                "index": index,
                "text": piece,
                "metadata": dict(metadata or {}),
                "ingested_at": stamp,
            }
            handle.write(json.dumps(record, sort_keys=True) + "\n")
            added.append(digest)
    return {
        "ok": True,
        "collection": collection,
        "reference": reference,
        "chunks": len(added),
        "ids": added,
    }


def read_corpus(collection: str = "default") -> List[Dict[str, Any]]:
    path = corpus_path(collection)
    if not path.is_file():
        return []
    rows: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict) and row.get("text"):
            rows.append(row)
    return rows


def query(
    *,
    q: str = "",
    collection: str = "default",
    top_k: int = 5,
) -> Dict[str, Any]:
    """Rank corpus chunks against the query. Empty hits when nothing shares."""
    needle = str(q or "").strip()
    if not needle:
        raise RetrievalError("q is required")
    rows = read_corpus(collection)
    query_grams = _trigrams(needle)
    query_tokens = set(_tokens(needle))
    scored: List[Dict[str, Any]] = []
    for row in rows:
        text = str(row.get("text") or "")
        score = _cosine(query_grams, _trigrams(text))
        overlap = len(query_tokens & set(_tokens(text)))
        if query_tokens:
            score = 0.75 * score + 0.25 * (overlap / len(query_tokens))
        if score >= MIN_SCORE:
            scored.append(
                {
                    "id": row.get("id"),
                    "text": text[:400],
                    "score": round(float(score), 4),
                    "reference": row.get("reference") or "",
                    "metadata": row.get("metadata") or {},
                }
            )
    scored.sort(key=lambda item: item["score"], reverse=True)
    hits = scored[: max(int(top_k), 1)]
    return {
        "ok": True,
        "collection": collection,
        "query": needle,
        "hits": hits,
        "results": hits,
        "total": len(hits),
        "corpus_size": len(rows),
    }
