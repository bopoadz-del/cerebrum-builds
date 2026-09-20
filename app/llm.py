"""Offline answer synthesis and management briefs for the schools estate.

Written by the factory WRITER role (codewhale exec)

No provider call, no key, no network: management asked for answers from the
platform's own records and for a brief on how a school is performing, and
this module produces both deterministically. It scores the retrieved
passages, quotes the strongest one, and labels the answer with its source so
a claim can be traced back to the record it came from. When nothing is
retrieved it says so instead of inventing text.

Scope: READS the question and the retrieved passages (or one rollup line),
WRITES an answer envelope. It never touches the store or the network.
"""

from __future__ import annotations

from typing import Any, Dict, List, Sequence

NO_ANSWER = "No facility record the platform holds covers that question yet."


def _sentences(text: str) -> List[str]:
    return [
        part.strip()
        for part in str(text or "").replace("\n", " ").split(".")
        if part.strip()
    ]


def synthesize(question: str, passages: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Compose an answer from retrieved passages, with per-claim sources."""
    question = str(question or "").strip()
    ranked = sorted(
        (
            p
            for p in passages
            if isinstance(p, dict) and str(p.get("text") or "").strip()
        ),
        key=lambda p: float(p.get("score") or 0.0),
        reverse=True,
    )
    if not ranked:
        return {
            "answer": NO_ANSWER,
            "citations": [],
            "confidence": 0.0,
            "provider": "offline_extractive",
        }

    terms = {t for t in question.lower().split() if len(t) > 2}
    best = ranked[0]
    sentences = _sentences(str(best.get("text")))
    chosen = ""
    for sentence in sentences:
        if not terms or any(t in sentence.lower() for t in terms):
            chosen = sentence
            break
    if not chosen:
        chosen = sentences[0] if sentences else str(best.get("text"))

    citations = [
        {
            "document": str(p.get("document") or p.get("source") or "facility-record"),
            "document_type": str(p.get("document_type") or "log"),
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


#: Rules the management brief is rendered through. Each entry is
#: (condition, headline, action). The template is data, not prose: the same
#: line always produces the same brief for the same figures.
RECOMMENDATION_RULES = (
    (
        "breach_high",
        "Service targets are being missed on a material share of closures",
        "re-plan the shift rota for the busiest trade this week",
    ),
    (
        "breach_watch",
        "Service targets are close to slipping",
        "confirm the open critical complaints have an owner",
    ),
    (
        "backlog_high",
        "The open backlog is above the team's capacity",
        "move field staff to the school with the largest backlog",
    ),
    (
        "clean",
        "The school is tracking to plan",
        "keep the current rota and review again next period",
    ),
)


def recommendation(*, audience: str, line: Dict[str, Any], notes: str = "") -> Dict[str, Any]:
    """Render the management brief from one dashboard rollup line.

    Deterministic and offline: no provider is called, and the brief names
    the figures it was derived from so the reader can audit it.
    """
    line = dict(line or {})
    compliance = line.get("sla_compliance_pct")
    open_count = line.get("complaints_open")
    workload = line.get("workload_score")
    fired: List[str] = []
    try:
        value = float(compliance) if compliance is not None else None
    except (TypeError, ValueError):
        value = None
    try:
        load = float(workload) if workload is not None else None
    except (TypeError, ValueError):
        load = None
    if value is not None and value < 80:
        fired.append("breach_high")
    elif value is not None and value < 95:
        fired.append("breach_watch")
    if load is not None and load > 80:
        fired.append("backlog_high")
    if not fired:
        fired.append("clean")
    items = [
        {"id": code, "headline": headline, "action": action}
        for code, headline, action in RECOMMENDATION_RULES
        if code in fired
    ]
    return {
        "audience": str(audience or "management"),
        "school": str(line.get("school") or ""),
        "period": str(line.get("period") or ""),
        "headline": items[0]["headline"] if items else "The school is tracking to plan",
        "action_items": items,
        "evidence": {
            "sla_compliance_pct": compliance,
            "complaints_open": open_count,
            "workload_score": workload,
        },
        "notes": str(notes or "")[:500],
        "provider": "offline_template",
    }
