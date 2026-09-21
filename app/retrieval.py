"""Project-sheet retrieval: the platform's memory of what PSI actually said.

PSI's project sheets (price lists, payment plans, handover dates) are
ingested here: chunked, stored per tenant, and retrieved per project tag.
The retriever is lexical (BM25 over tokens) on purpose — it runs with no
network, no embedding service and no model weights, so a brokerage's price
list is quoted from its own document on the day it was uploaded, and the
retrieval path is deterministic enough to test.

Cite-or-refuse lives on top of it: :func:`grounded_answer` returns a
verbatim sentence from a retrieved chunk with its citation, or withholds.
It never paraphrases a price, a payment plan or a handover date into
something the document does not say, because that is where the liability is.

Every answer carries the authority envelope (``precedence.v1``): a certified
sheet outranks an ordinary document, and the label names the chunk.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import uuid
from collections import Counter
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from app import config
from app.authority import Claim, envelope
from app.store import connect
from app.store import placeholder as _placeholder

STOPWORDS = frozenset(
    """a an and are as at be by for from has have how i in is it its of on or that the
this to was were what when where which who will with you your do does did can could
should would about after before over under""".split()
)

TOKEN_RE = re.compile(r"[a-z0-9]+(?:[.][0-9]+)?")
SENTENCE_RE = re.compile(r"[^.!?\n]+[.!?]?")

MONEY_RE = re.compile(
    r"(?:[A-Z]{3}\s?)?\d[\d,]*(?:\.\d+)?\s?(?:m|k|million|thousand)?\b",
    re.IGNORECASE,
)
HANDOVER_RE = re.compile(
    r"\b(?:q[1-4]\s?\d{4}|\d{4}|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s?\d{4})\b",
    re.IGNORECASE,
)
PAYMENT_RE = re.compile(
    r"\b\d{1,3}\s?%|\b\d{1,3}\s?(?:months?|instal?ments?|years?)\b", re.IGNORECASE
)

#: Words that identify each claim type inside a retrieved chunk. The price
#: lane names no currency: the brief states no country, so the only currency
#: tokens this platform looks for are the ones the operator supplies --
#: ``CURRENCY`` once it is set, plus ``PRICE_CURRENCY_TOKENS`` for whatever
#: their project sheets happen to print.
CLAIM_KEYWORDS = {
    "price": ("price", "prices", "starting", "from", "cost"),
    "payment_plan": ("payment", "plan", "instalment", "installment", "down", "months", "%"),
    "handover_date": ("handover", "delivery", "completion", "q1", "q2", "q3", "q4"),
    "amenities": ("amenit", "pool", "gym", "parking", "clubhouse", "beach"),
    "location": ("location", "minutes", "district", "near", "road", "community"),
    "availability": ("available", "availability", "inventory", "sold", "remaining"),
}

CLAIM_PATTERNS = {
    "price": MONEY_RE,
    "handover_date": HANDOVER_RE,
    "payment_plan": PAYMENT_RE,
}


class _Conn:
    """Placeholder adapter: one SQL text runs on sqlite and on Postgres.

    The queries below are written with ``?`` because that is what the
    development backend takes; this translates them for the operator's
    Postgres, so the corpus behaves the same on both.
    """

    def __init__(self, conn: Any) -> None:
        self._conn = conn

    def execute(self, sql: str, params: Sequence[Any] = ()) -> Any:
        return self._conn.execute(sql.replace("?", _placeholder()), list(params))

    def commit(self) -> None:
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()


def tokenize(text: str) -> List[str]:
    raw = [t for t in TOKEN_RE.findall(str(text or "").lower())]
    return [t for t in raw if t not in STOPWORDS and len(t) > 1]


def digest(text: str) -> str:
    return hashlib.sha256(str(text or "").encode("utf-8")).hexdigest()


def chunk_text(text: str, *, size: Optional[int] = None, overlap: Optional[int] = None) -> List[str]:
    """Paragraph-aware chunking, so a quoted sentence stays whole."""
    limit = int(config.CHUNK_CHARACTERS if size is None else size)
    keep = int(config.CHUNK_OVERLAP if overlap is None else overlap)
    body = str(text or "").strip()
    if not body:
        return []
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    chunks: List[str] = []
    current = ""
    for para in paragraphs:
        if len(para) > limit:
            if current:
                chunks.append(current)
                current = ""
            step = max(1, limit - keep)
            for start in range(0, len(para), step):
                piece = para[start : start + limit].strip()
                if piece:
                    chunks.append(piece)
            continue
        if len(current) + len(para) + 2 <= limit:
            current = f"{current}\n\n{para}".strip()
        else:
            if current:
                chunks.append(current)
            tail = current[-keep:] if keep and current else ""
            current = f"{tail}\n\n{para}".strip() if tail else para
    if current:
        chunks.append(current)
    return chunks


def _rows(sql: str, params: Sequence[Any]) -> List[Dict[str, Any]]:
    conn = _Conn(connect())
    try:
        cursor = conn.execute(sql, list(params))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def _write(sql: str, params: Sequence[Any]) -> None:
    conn = _Conn(connect())
    try:
        conn.execute(sql, list(params))
        conn.commit()
    finally:
        conn.close()


def ingest(
    tenant_id: str,
    *,
    text: str,
    title: str = "",
    project_tag: str = "",
    source: str = "",
    certified: bool = False,
    document_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Ingest one project sheet for one tenant. Idempotent per document id."""
    if not tenant_id:
        raise ValueError("tenant_id is required: a corpus is never shared")
    body = str(text or "").strip()
    if not body:
        raise ValueError("a document with no text cannot be retrieved from")
    doc_id = str(document_id or uuid.uuid4().hex[:16])
    stamp = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    doc_digest = digest(body)
    conn = _Conn(connect())
    try:
        conn.execute("DELETE FROM rag_chunks WHERE tenant_id = ? AND document_id = ?", (tenant_id, doc_id))
        conn.execute(
            "DELETE FROM rag_documents WHERE tenant_id = ? AND document_id = ?",
            (tenant_id, doc_id),
        )
        conn.execute(
            "INSERT INTO rag_documents (tenant_id, document_id, title, project_tag, source, "
            "certified, content, digest, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                tenant_id,
                doc_id,
                title or doc_id,
                project_tag,
                source,
                1 if certified else 0,
                body,
                doc_digest,
                stamp,
                stamp,
            ),
        )
        pieces = chunk_text(body)
        for ordinal, piece in enumerate(pieces, start=1):
            conn.execute(
                "INSERT INTO rag_chunks (tenant_id, document_id, project_tag, ordinal, text, "
                "certified, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    tenant_id,
                    doc_id,
                    project_tag,
                    ordinal,
                    piece,
                    1 if certified else 0,
                    stamp,
                    stamp,
                ),
            )
        conn.commit()
    finally:
        conn.close()
    return {
        "ok": True,
        "tenant_id": tenant_id,
        "document_id": doc_id,
        "title": title or doc_id,
        "project_tag": project_tag,
        "source": source,
        "certified": bool(certified),
        "chunks": len(pieces),
        "digest": doc_digest,
        "authority": envelope(
            [
                Claim(
                    name="document",
                    value=doc_id,
                    layer="certified" if certified else "documents",
                    source=source or doc_id,
                    detail="ingested project sheet",
                )
            ]
        ),
    }


def _corpus(tenant_id: str, project_tag: Optional[str]) -> List[Dict[str, Any]]:
    if project_tag:
        return _rows(
            "SELECT * FROM rag_chunks WHERE tenant_id = ? AND project_tag = ?",
            (tenant_id, project_tag),
        )
    return _rows("SELECT * FROM rag_chunks WHERE tenant_id = ?", (tenant_id,))


def _bm25(
    question: str,
    chunks: Sequence[Mapping[str, Any]],
    *,
    top_k: int,
    k1: float = 1.2,
    b: float = 0.75,
) -> List[Dict[str, Any]]:
    terms = tokenize(question)
    if not terms or not chunks:
        return []
    documents = [tokenize(str(chunk.get("text") or "")) for chunk in chunks]
    lengths = [len(doc) or 1 for doc in documents]
    average = sum(lengths) / len(lengths)
    document_frequency = Counter()
    for doc in documents:
        for term in set(doc):
            document_frequency[term] += 1
    total = len(documents)
    scored: List[Dict[str, Any]] = []
    for index, doc in enumerate(documents):
        counts = Counter(doc)
        score = 0.0
        for term in terms:
            if term not in counts:
                continue
            idf = math.log(1 + (total - document_frequency[term] + 0.5) / (document_frequency[term] + 0.5))
            tf = counts[term]
            denominator = tf + k1 * (1 - b + b * (lengths[index] / average))
            score += idf * (tf * (k1 + 1)) / denominator
        if score <= 0:
            continue
        chunk = dict(chunks[index])
        chunk["score"] = round(score, 6)
        chunk["citation"] = f"{chunk.get('document_id')}#chunk-{chunk.get('ordinal')}"
        chunk["layer"] = "certified" if int(chunk.get("certified") or 0) else "documents"
        chunk["label"] = f"{chunk['layer']}:{chunk['citation']}"
        scored.append(chunk)
    scored.sort(key=lambda item: (-float(item["score"]), str(item["citation"])))
    return scored[: max(1, int(top_k))]


def price_currency_tokens() -> set:
    """The currency tokens the operator supplied, never one this code chose."""
    tokens = {str(token).lower() for token in config.PRICE_CURRENCY_TOKENS}
    configured = (config.env("CURRENCY") or "").strip().lower()
    if configured:
        tokens.add(configured)
    return tokens


def relevant_sentence(chunk: str, question: str, claim_type: Optional[str] = None) -> str:
    """The sentence in the chunk that actually carries the claim, verbatim."""
    sentences = [s.strip() for s in SENTENCE_RE.findall(str(chunk or "")) if s.strip()]
    if not sentences:
        return str(chunk or "").strip()
    terms = set(tokenize(question)) | set(CLAIM_KEYWORDS.get(str(claim_type or ""), ()))
    if str(claim_type or "") == "price":
        terms |= price_currency_tokens()
    best = sentences[0]
    best_score = -1
    for sentence in sentences:
        words = set(tokenize(sentence))
        score = len(words & terms)
        pattern = CLAIM_PATTERNS.get(str(claim_type or ""))
        if pattern and pattern.search(sentence):
            score += 2
        if score > best_score:
            best, best_score = sentence, score
    return best


def query(
    tenant_id: str,
    question: str,
    *,
    project_tag: Optional[str] = None,
    top_k: Optional[int] = None,
    claim_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve the passages that support an answer, tenant-scoped."""
    limit = int(config.RETRIEVAL_TOP_K if top_k is None else top_k)
    chunks = _corpus(tenant_id, project_tag)
    hits = _bm25(question, chunks, top_k=limit)
    threshold = float(config.RETRIEVAL_MIN_SCORE)
    hits = [hit for hit in hits if float(hit["score"]) >= threshold]
    claims = [
        Claim(
            name=str(claim_type or "retrieval"),
            value=hit["citation"],
            layer=str(hit["layer"]),
            source=str(hit["citation"]),
            detail=str(relevant_sentence(str(hit["text"]), question, claim_type))[:400],
        )
        for hit in hits
    ]
    authority = envelope(claims) if claims else envelope([], withheld_claim=str(claim_type or "retrieval"))
    return {
        "tenant_id": tenant_id,
        "question": question,
        "project_tag": project_tag,
        "claim_type": claim_type,
        "hits": hits,
        "citations": [hit["citation"] for hit in hits],
        "authority": authority,
        "retrieved_count": len(hits),
    }


def grounded_answer(
    tenant_id: str,
    *,
    project_tag: str,
    question: str,
    claim_type: Optional[str] = None,
    language: str = "en",
) -> Dict[str, Any]:
    """The answered turn: cited and verbatim, or withheld. Never improvised."""
    found = query(
        tenant_id,
        question,
        project_tag=project_tag or None,
        claim_type=claim_type,
    )
    hits = found["hits"]
    if not hits:
        return {
            "answer": None,
            "pitch": None,
            "withheld": True,
            "withheld_claims": [str(claim_type or "retrieval")],
            "reason": "no retrieved passage supports this claim about the project",
            "citations": [],
            "retrieved_count": 0,
            "project_tag": project_tag,
            "language": language,
            "authority": found["authority"],
        }
    best = hits[0]
    sentence = relevant_sentence(str(best["text"]), question, claim_type)
    answer = f"{sentence} [{best['citation']}]"
    return {
        "answer": answer,
        "pitch": answer,
        "withheld": False,
        "withheld_claims": [],
        "reason": "quoted verbatim from an ingested project sheet",
        "citations": [best["citation"]],
        "retrieved_count": len(hits),
        "project_tag": project_tag,
        "language": language,
        "quote": sentence,
        "source_documents": best.get("document_id"),
        "authority": found["authority"],
    }


def corpus_stats(tenant_id: str) -> Dict[str, Any]:
    documents = _rows(
        "SELECT document_id, title, project_tag, source, certified, digest FROM rag_documents "
        "WHERE tenant_id = ? ORDER BY document_id",
        (tenant_id,),
    )
    chunks = _rows(
        "SELECT COUNT(*) AS n FROM rag_chunks WHERE tenant_id = ?", (tenant_id,)
    )
    return {
        "tenant_id": tenant_id,
        "documents": documents,
        "document_count": len(documents),
        "chunk_count": int(chunks[0]["n"]) if chunks else 0,
        "projects": sorted({str(d.get("project_tag") or "") for d in documents if d.get("project_tag")}),
    }


def forget(tenant_id: str, document_id: str) -> bool:
    conn = _Conn(connect())
    try:
        conn.execute(
            "DELETE FROM rag_chunks WHERE tenant_id = ? AND document_id = ?",
            (tenant_id, document_id),
        )
        cursor = conn.execute(
            "DELETE FROM rag_documents WHERE tenant_id = ? AND document_id = ?",
            (tenant_id, document_id),
        )
        conn.commit()
        return bool(cursor.rowcount)
    finally:
        conn.close()
