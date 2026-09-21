"""Answer synthesis with evidence, offline.

Written by the factory WRITER role (codewhale exec)

The platform is offline by contract (no network, no Store callbacks), so this
module is a deterministic, extractive reasoner: it answers from the sentences
that actually matched in the tenant's own corpus, and labels the answer with
the authority layer of the best source (precedence.v1).

What it will not do is the thing the brief forbids: answer when nothing was
retrieved. With no evidence the answer is a refusal that names the reason --
``evidence_or_refuse`` -- because a plausible sentence from nowhere is worse
than "I have no document for that".
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence

from app import authority
from app.retrieval import search, tokenize

MAX_SOURCES = 4


def _sentences(text: str) -> List[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", str(text or "")) if part.strip()]


def _best_sentence(chunk: str, terms: Sequence[str]) -> str:
    scored = []
    for sentence in _sentences(chunk):
        overlap = len(set(tokenize(sentence)) & set(terms))
        scored.append((overlap, len(sentence), sentence))
    scored.sort(key=lambda item: (-item[0], -item[1]))
    return scored[0][2] if scored else str(chunk or "")


def answer(
    question: Any,
    *,
    tenant_id: str,
    top_k: int = 4,
) -> Dict[str, Any]:
    """Answer a staff question from the tenant's own documents."""
    question_text = str(question or "").strip()
    if not question_text:
        return {
            "ok": False,
            "refused": True,
            "reason": "no_question",
            "error": "a question is required",
            "authority": authority.HIGHEST,
            "precedence": "precedence.v1",
        }
    found = search(question_text, tenant_id, top_k=top_k)
    hits = list(found.get("hits") or [])
    if not hits:
        return {
            "ok": True,
            "refused": True,
            "reason": "no_source_in_corpus",
            "answer": None,
            "question": question_text,
            "hits": [],
            "citations": [],
            "authority": "procedures",
            "rank": authority.rank_of("procedures"),
            "precedence": "precedence.v1",
            "note": (
                "no uploaded document in this property's corpus matches the "
                "question; refusing rather than answering from no source"
            ),
        }
    terms = tokenize(question_text)
    claims: List[Dict[str, Any]] = []
    citations: List[Dict[str, Any]] = []
    for hit in hits[:MAX_SOURCES]:
        sentence = _best_sentence(str(hit.get("text") or ""), terms)
        claims.append(
            {
                "layer": hit.get("authority"),
                "document": hit.get("title"),
                "claim": sentence,
                "score": hit.get("score"),
            }
        )
        citations.append(
            {
                "document_id": hit.get("document_id"),
                "title": hit.get("title"),
                "kind": hit.get("kind"),
                "authority": hit.get("authority"),
                "chunk_id": hit.get("chunk_id"),
                "text": hit.get("text"),
            }
        )
    label = authority.winner([str(hit.get("authority")) for hit in hits])
    winner_claim = next(
        (claim["claim"] for claim in claims if claim["layer"] == label), claims[0]["claim"]
    )
    body = " ".join(claim["claim"] for claim in claims[:2]).strip()
    envelope = authority.label_answer(label, claims)
    return {
        "ok": True,
        "refused": False,
        "question": question_text,
        "answer": body or winner_claim,
        "lead_claim": winner_claim,
        "citations": citations,
        "hits": hits[:MAX_SOURCES],
        "precedence": envelope["precedence"],
        "authority": envelope["authority"],
        "rank": envelope["rank"],
        "claims": envelope["claims"],
    }
