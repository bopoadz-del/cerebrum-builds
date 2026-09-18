"""Offline answer adapter: deterministic, labelled, no model call.

Written by the factory WRITER role (codewhale exec)

There is no network in this platform, so the "model" is an adapter over the
tenant's own corpus plus the versioned formula registry and the operating
procedures. It never chooses a winner: app.authority decides which layer wins
and this module only reports it, together with the per-claim labels and the
divergence records for the claims that disagree.

Scope
-----
READS  the bound tenant's corpus (app.retrieval), the formula registry
       (app.formulas), the procedure list below.
WRITES nothing.
NEVER  network; a provider key; a claim without a layer label.
"""

from __future__ import annotations

from typing import Any, Dict, List

import app.authority as authority
import app.formulas as formulas
import app.retrieval as retrieval

ENGINE = "offline-deterministic"
PROCEDURES: List[Dict[str, str]] = [
    {
        "key": "check_in_desk_procedure",
        "text": (
            "Front desk: greet the guest, confirm the room number and the "
            "number of nights, record the check-in, hand over the key."
        ),
    },
    {
        "key": "no_show_procedure",
        "text": (
            "If a guest has not arrived by the end of the day, mark the "
            "arrival as a no-show in the daily summary."
        ),
    },
    {
        "key": "overbooking_procedure",
        "text": (
            "If a room is not free for the requested dates, offer the next "
            "free room of the same grade before releasing the booking."
        ),
    },
]


def _document_claims(tenant: str, question: str, limit: int) -> List[Dict[str, Any]]:
    claims = []
    for hit in retrieval.search(tenant, question, limit=limit):
        claims.append(
            {
                "layer": "certified" if hit.get("certified") else "document",
                "source": hit.get("title") or f"corpus:{hit.get('id')}",
                "text": hit.get("excerpt") or "",
                "confidence": hit.get("score"),
            }
        )
    return claims


def _formula_claims(question: str) -> List[Dict[str, Any]]:
    words = set(retrieval.tokens(question))
    claims = []
    for item in formulas.REGISTRY:
        key_words = {part for part in item["key"].split("_")}
        if key_words & words:
            claims.append(
                {
                    "layer": "formula",
                    "source": item["key"],
                    "text": f"{item['description']} ({item['version']})",
                    "confidence": 0.5,
                }
            )
    return claims


def _procedure_claims(question: str) -> List[Dict[str, Any]]:
    words = set(retrieval.tokens(question))
    claims = []
    for item in PROCEDURES:
        key_words = {part for part in item["key"].split("_")}
        if key_words & words:
            claims.append(
                {
                    "layer": "procedure",
                    "source": item["key"],
                    "text": item["text"],
                    "confidence": 0.25,
                }
            )
    return claims


def answer(question: str, *, tenant: str, limit: int = 5) -> Dict[str, Any]:
    """Answer from the bound tenant's corpus, labelled and auditable."""
    question = str(question or "").strip()
    if not question:
        raise ValueError("question is required")
    claims = (
        _document_claims(str(tenant), question, limit)
        + _formula_claims(question)
        + _procedure_claims(question)
    )
    top = authority.winner(claims)
    labels = [authority.label_of(claim) for claim in claims]
    divergences = authority.divergence(claims)
    if top is None:
        return {
            "answer": "No source in this tenant's corpus covers that question.",
            "engine": ENGINE,
            "winner": None,
            "claims": [],
            "labels": [],
            "divergence": [],
            "sources": [],
            "network": "none",
        }
    return {
        "answer": str(top.get("text") or ""),
        "engine": ENGINE,
        "winner": authority.label_of(top),
        "claims": [
            {"layer": c.get("layer"), "source": c.get("source"), "text": c.get("text")}
            for c in claims
        ],
        "labels": labels,
        "divergence": divergences,
        "sources": [c.get("source") for c in claims],
        "network": "none",
    }


def status() -> Dict[str, Any]:
    """What this adapter really is. Never claims a provider."""
    return {
        "ok": True,
        "engine": ENGINE,
        "provider": "none",
        "network": "none",
        "precedence": authority.VERSION,
        "formulas": formulas.VERSION,
        "procedures": [item["key"] for item in PROCEDURES],
        "note": (
            "answers come from the bound tenant's corpus plus the versioned "
            "formula registry; the winner is decided by precedence.v1, not by "
            "a model"
        ),
    }
