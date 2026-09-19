"""Offline answer synthesis and recommendation briefs for FinOps Central.

Written by the factory WRITER role (codewhale exec)

No provider call, no key, no network: the finance team asked for answers
from the platform's own uploaded documents and for a recommendation brief
for the CFO, and this module produces both deterministically. It scores the
retrieved passages, quotes the strongest one, and labels the answer with its
source so a claim can be traced back to the document it came from. When
nothing is retrieved it says so instead of inventing text.

Scope: READS the question and the retrieved passages (or one rollup line),
WRITES an answer envelope. It never touches the store or the network.
"""

from __future__ import annotations

from typing import Any, Dict, List, Sequence

NO_ANSWER = "No uploaded finance document covers that question yet."


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
            "document_type": str(p.get("document_type") or "policy"),
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


#: Recommendation template the CFO brief is rendered through. Each entry is
#: (condition, headline, action). The template is data, not prose: the same
#: line always produces the same brief for the same figures.
RECOMMENDATION_RULES = (
    ("over_forecast", "Department is over its forecast", "freeze discretionary commitments until the next review"),
    ("near_forecast", "Department is within 10% of forecast", "re-plan the remaining commitments this period"),
    ("under_forecast", "Department is tracking below forecast", "confirm the underspend is committed, not deferred spend"),
    ("low_confidence", "Forecast confidence is below 60%", "evidence the forecast with approved commitments"),
)


def recommendation(*, audience: str, line: Dict[str, Any], notes: str = "") -> Dict[str, Any]:
    """Render the reporting brief for the CFO/controller from a rollup line.

    Deterministic and offline: no provider is called, and the brief names
    the figures it was derived from so the reader can audit it.
    """
    line = dict(line or {})
    spend = line.get("portfolio_total")
    confidence = line.get("forecast_confidence")
    risk = str(line.get("risk_level") or "low")
    fired: List[str] = []
    if risk == "high":
        fired.append("over_forecast")
    elif risk == "medium":
        fired.append("near_forecast")
    else:
        fired.append("under_forecast")
    try:
        if confidence is not None and float(confidence) < 0.6:
            fired.append("low_confidence")
    except (TypeError, ValueError):
        pass
    items = [
        {"id": code, "headline": headline, "action": action}
        for code, headline, action in RECOMMENDATION_RULES
        if code in fired
    ]
    return {
        "audience": str(audience or "cfo"),
        "department": str(line.get("department") or ""),
        "period": str(line.get("period") or ""),
        "headline": items[0]["headline"] if items else "Department is tracking to plan",
        "action_items": items,
        "evidence": {
            "portfolio_total": spend,
            "forecast_confidence": confidence,
            "risk_level": risk,
        },
        "notes": str(notes or "")[:500],
        "provider": "offline_template",
    }
