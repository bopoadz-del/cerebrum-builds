"""Offline answer synthesis for the bakery platform.

Written by the factory WRITER role (codewhale exec)

No provider call, no key, no network: the crew asked for answers from the
bakery's own uploaded documents, and this module answers from them. It
scores the retrieved passages, quotes the strongest one, and labels the
answer with its source so a claim can be traced back to the document it
came from. When nothing is retrieved it says so instead of inventing text.
"""

from __future__ import annotations

from typing import Any, Dict, List, Sequence

NO_ANSWER = "No uploaded bakery document covers that question yet."


def _sentences(text: str) -> List[str]:
    return [part.strip() for part in str(text or "").replace("\n", " ").split(".") if part.strip()]


def synthesize(question: str, passages: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Compose an answer from retrieved passages, with per-claim sources."""
    question = str(question or "").strip()
    ranked = sorted(
        (p for p in passages if isinstance(p, dict) and str(p.get("text") or "").strip()),
        key=lambda p: float(p.get("score") or 0.0),
        reverse=True,
    )
    if not ranked:
        return {"answer": NO_ANSWER, "citations": [], "confidence": 0.0, "provider": "offline_extractive"}

    terms = {t for t in question.lower().split() if len(t) > 2}
    best = ranked[0]
    chosen = ""
    for sentence in _sentences(str(best.get("text"))):
        if not terms or any(t in sentence.lower() for t in terms):
            chosen = sentence
            break
    if not chosen:
        chosen = _sentences(str(best.get("text")))[:1][0] if _sentences(str(best.get("text"))) else str(best.get("text"))

    citations = [
        {
            "document": str(p.get("document") or p.get("source") or "uploaded-document"),
            "document_type": str(p.get("document_type") or "procedure"),
            "score": round(float(p.get("score") or 0.0), 4),
        }
        for p in ranked[:3]
    ]
    confidence = min(1.0, float(best.get("score") or 0.0))
    return {
        "answer": chosen.strip(),
        "citations": citations,
        "confidence": round(confidence, 4),
        "provider": "offline_extractive",
        "question": question,
    }
