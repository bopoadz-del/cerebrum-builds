"""precedence.v1 -- layer authority as versioned data.

Written by the factory WRITER role (codewhale exec)

Layers, highest first:

    1 certified   -- a signed/certified source class
    2 documents   -- the tenant's ingested corpus
    3 formulas    -- the versioned formula registry
    4 procedures  -- operating procedures

The model is TOLD the winner; it never chooses one. Every answer built on
this module carries per-claim labels and the divergence records between
claims that disagree, so a reader can see which layer won and why.

Scope
-----
READS  the claims handed in (pure function).
WRITES nothing.
NEVER  network; the caller's choice of winner.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

VERSION = "precedence.v1"

LAYERS: List[Dict[str, Any]] = [
    {"rank": 1, "kind": "certified", "label": "Certified source",
     "rule": "a certified source outranks every uncertified layer"},
    {"rank": 2, "kind": "document", "label": "Tenant document",
     "rule": "an ingested document outranks a formula or a procedure"},
    {"rank": 3, "kind": "formula", "label": "Formula registry",
     "rule": "a versioned formula outranks a procedure"},
    {"rank": 4, "kind": "procedure", "label": "Procedure",
     "rule": "a procedure is the lowest layer"},
]

_RANK = {layer["kind"]: layer["rank"] for layer in LAYERS}
_KIND_BY_ALIAS = {
    "certified": "certified",
    "certificate": "certified",
    "document": "document",
    "doc": "document",
    "corpus": "document",
    "formula": "formula",
    "procedure": "procedure",
    "sop": "procedure",
}


class UnknownLayer(ValueError):
    """A claim declared a layer precedence.v1 does not define."""


def kind_of(claim: Dict[str, Any]) -> str:
    raw = str((claim or {}).get("layer") or "").strip().lower()
    kind = _KIND_BY_ALIAS.get(raw)
    if kind is None:
        raise UnknownLayer(f"unknown layer: {raw!r}")
    return kind


def label_of(claim: Dict[str, Any]) -> Dict[str, Any]:
    kind = kind_of(claim)
    return {
        "layer": kind,
        "rank": _RANK[kind],
        "label": next(l["label"] for l in LAYERS if l["kind"] == kind),
        "source": str((claim or {}).get("source") or ""),
    }


def winner(claims: Iterable[Dict[str, Any]]) -> Dict[str, Any] | None:
    """The precedence-winning claim. Ties break on confidence, then order."""
    ranked = []
    for index, claim in enumerate(claims or []):
        if not isinstance(claim, dict):
            continue
        ranked.append(
            (
                _RANK[kind_of(claim)],
                -float(claim.get("confidence") or 0.0),
                index,
                claim,
            )
        )
    if not ranked:
        return None
    ranked.sort(key=lambda item: (item[0], item[1], item[2]))
    return ranked[0][3]


def divergence(claims: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Claims that disagree with the winner, recorded rather than dropped."""
    claims = [c for c in (claims or []) if isinstance(c, dict)]
    top = winner(claims)
    if top is None:
        return []
    top_text = str(top.get("text") or "").strip().lower()
    top_kind = kind_of(top)
    records = []
    for claim in claims:
        if claim is top:
            continue
        text = str(claim.get("text") or "").strip().lower()
        if text == top_text:
            continue
        records.append(
            {
                "layer": kind_of(claim),
                "rank": _RANK[kind_of(claim)],
                "source": str(claim.get("source") or ""),
                "text": str(claim.get("text") or ""),
                "loses_to": top_kind,
                "reason": f"layer {_RANK[kind_of(claim)]} is outranked by {top_kind}",
            }
        )
    return records


def declaration() -> Dict[str, Any]:
    """precedence.v1 as data, for GET /v1/precedence."""
    return {
        "ok": True,
        "version": VERSION,
        "layers": LAYERS,
        "winner_is": "decided by this module, reported to the model -- never chosen by it",
        "labels": sorted(_RANK),
    }
