"""Tenant-scoped local retrieval for RetailOS.

Written by the factory WRITER role (codewhale exec).

Offline, dependency-free lexical retrieval (BM25-shaped scoring over a
JSONL corpus). Every corpus read and write is scoped to the tenant resolved
from the authenticated principal — a client-supplied tenant name is never
honoured (see app/tenancy.py).

Used by:
  * ``app/rag_routes.py`` — POST /v1/rag/ingest, POST /v1/rag/query
  * ``app/offline_blocks.py`` — the sealed knowledge runtime's replacement
  * ``app/authority.py`` — document layer lookup for precedence answers
"""

from __future__ import annotations

import json
import math
import os
import re
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset(
    """a an and are as at be by for from has have in is it its of on or that the
    to was were will with this these those""".split()
)

_LOCK = threading.Lock()
_INDEXES: Dict[str, "CorpusIndex"] = {}


def corpus_root() -> Path:
    root = Path(os.getenv("STORAGE_PATH") or "./data") / "corpus"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _tokens(text: str) -> List[str]:
    return [tok for tok in _TOKEN_RE.findall(str(text or "").lower()) if tok not in _STOPWORDS]


@dataclass
class Document:
    """One ingested corpus document."""

    doc_id: str
    tenant: str
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(
            {
                "doc_id": self.doc_id,
                "tenant": self.tenant,
                "text": self.text,
                "metadata": self.metadata,
            },
            sort_keys=True,
        )


class CorpusIndex:
    """Lexical index over one tenant's corpus. Persisted as JSONL."""

    def __init__(self, tenant: str) -> None:
        self.tenant = tenant
        self.documents: List[Document] = []
        self._postings: Dict[str, Dict[int, int]] = {}
        self._lengths: List[int] = []
        self.load()

    # -- persistence --------------------------------------------------------
    @property
    def path(self) -> Path:
        safe = re.sub(r"[^A-Za-z0-9_.-]", "_", self.tenant or "local")
        return corpus_root() / (safe + ".jsonl")

    def load(self) -> None:
        if not self.path.is_file():
            return
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except ValueError:
                continue
            doc = Document(
                doc_id=str(raw.get("doc_id") or ""),
                tenant=str(raw.get("tenant") or self.tenant),
                text=str(raw.get("text") or ""),
                metadata=dict(raw.get("metadata") or {}),
            )
            if doc.doc_id:
                self._add(doc, persist=False)

    def _add(self, document: Document, *, persist: bool = True) -> None:
        index = len(self.documents)
        tokens = _tokens(document.text)
        self.documents.append(document)
        self._lengths.append(len(tokens))
        for token in tokens:
            self._postings.setdefault(token, {})
            self._postings[token][index] = self._postings[token].get(index, 0) + 1
        if persist:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(document.to_json() + "\n")

    def ingest(
        self,
        text: str,
        *,
        doc_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Document:
        existing = {doc.doc_id for doc in self.documents}
        ident = str(doc_id or "").strip()
        if not ident:
            ident = "doc_%04d" % (len(self.documents) + 1)
        while ident in existing:
            ident = ident + "_x"
        document = Document(
            doc_id=ident,
            tenant=self.tenant,
            text=str(text or ""),
            metadata=dict(metadata or {}),
        )
        self._add(document)
        return document

    # -- search -------------------------------------------------------------
    def search(self, query: str, *, top_k: int = 5) -> List[Dict[str, Any]]:
        terms = _tokens(query)
        if not terms or not self.documents:
            return []
        total = len(self.documents)
        avg_len = (sum(self._lengths) / total) if total else 1.0
        scores: Dict[int, float] = {}
        for term in terms:
            postings = self._postings.get(term)
            if not postings:
                continue
            df = len(postings)
            idf = math.log(1.0 + (total - df + 0.5) / (df + 0.5))
            for index, freq in postings.items():
                length = self._lengths[index] or 1
                denom = freq + 1.2 * (0.25 + 0.75 * length / (avg_len or 1.0))
                scores[index] = scores.get(index, 0.0) + idf * (freq * 2.2) / denom
        ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))[: max(1, top_k)]
        return [
            {
                "doc_id": self.documents[index].doc_id,
                "text": self.documents[index].text,
                "score": round(score, 6),
                "metadata": self.documents[index].metadata,
            }
            for index, score in ranked
        ]

    def stats(self) -> Dict[str, Any]:
        return {
            "tenant": self.tenant,
            "documents": len(self.documents),
            "terms": len(self._postings),
            "path": str(self.path),
        }


def index_for(tenant: str) -> CorpusIndex:
    """The tenant's index. The tenant is resolved, never client-supplied."""
    key = str(tenant or "local")
    with _LOCK:
        index = _INDEXES.get(key)
        if index is None:
            index = CorpusIndex(key)
            _INDEXES[key] = index
        return index


def ingest_document(
    tenant: str,
    text: str,
    *,
    doc_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    index = index_for(tenant)
    with _LOCK:
        document = index.ingest(text, doc_id=doc_id, metadata=metadata)
    return {
        "doc_id": document.doc_id,
        "tenant": document.tenant,
        "terms": len(_tokens(document.text)),
        "corpus_total": len(index.documents),
    }


def search(
    tenant: str,
    query: str,
    *,
    top_k: int = 5,
    collections: Optional[Sequence[str]] = None,
) -> List[Dict[str, Any]]:
    index = index_for(tenant)
    hits = index.search(query, top_k=max(top_k, 1) * (3 if collections else 1))
    wanted = {str(c) for c in (collections or ()) if str(c)}
    if wanted:
        filtered = [
            hit
            for hit in hits
            if str((hit.get("metadata") or {}).get("collection") or "") in wanted
        ]
        hits = filtered or hits
    return hits[: max(top_k, 1)]


def answer(tenant: str, query: str, *, top_k: int = 5) -> Dict[str, Any]:
    """An extractive answer with its citations — never an invented claim."""
    hits = search(tenant, query, top_k=top_k)
    if not hits:
        return {
            "answer": "",
            "results": [],
            "grounded": False,
            "note": "no corpus match for this query",
        }
    best = hits[0]
    return {
        "answer": best["text"],
        "results": hits,
        "grounded": True,
        "score": best["score"],
        "citations": [
            {"doc_id": hit["doc_id"], "score": hit["score"]} for hit in hits
        ],
    }


def seed_firm_guidance(tenant: str = "local") -> int:
    """Load the firm's own guidance corpus once per process.

    These are the practice's standing instructions the knowledge block
    answers from when the sealed Store runtime is unavailable. Idempotent.
    """
    index = index_for(tenant)
    with _LOCK:
        if index.documents:
            return 0
        seeded = 0
        for title, body in FIRM_GUIDANCE:
            index.ingest(
                body,
                doc_id="guidance_" + title,
                metadata={"collection": "firm_guidance", "title": title},
            )
            seeded += 1
    return seeded


#: The retailer's own documented practice — the SOP corpus the knowledge
#: block answers from. Written by the operating team, versioned in this
#: platform.
FIRM_GUIDANCE: Tuple[Tuple[str, str], ...] = (
    (
        "stock_replenishment",
        "Stock replenishment: every SKU carries an on-hand count, a reorder "
        "point and a lead time. A count at or below the reorder point is "
        "replenished before the next trading week, and the purchase order "
        "records the supplier, the quantity and the expected date.",
    ),
    (
        "sales_and_returns",
        "Sales and returns: an order records its number, channel, total and "
        "payment status. In-store, online and marketplace orders are held in "
        "one ledger; a return is recorded against the original order number "
        "and the stock level moves back to the shelf on receipt.",
    ),
    (
        "customer_data",
        "Customer data: profiles hold a name, contact details, segment and "
        "purchase history. Marketing only uses the segment and loyalty tier; "
        "contact details are never exported outside the platform.",
    ),
    (
        "supplier_purchasing",
        "Purchasing: a purchase order names the supplier, the SKU, the "
        "quantity and the payment terms. Lead times are reviewed monthly and "
        "a supplier whose lead time doubles is escalated to the buyer.",
    ),
    (
        "omnichannel_sync",
        "Channel synchronisation: stock counts and order status are pushed to "
        "every connected channel, and each sync records its direction, "
        "marketplace and external order id so a mismatch can be traced to one "
        "event.",
    ),
    (
        "audit_and_compliance",
        "Record access, modification and financial events are logged "
        "immutably with actor, timestamp and resource. Evidence bundles are "
        "hashed with sha256 and verified against the recorded digest, and the "
        "control set is reviewed quarterly.",
    ),
)
