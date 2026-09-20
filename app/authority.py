"""Answer authority: precedence.v1, as versioned data.

Written by the factory WRITER role (codewhale exec)

Layer order, highest first:

    1 certified      -- a certified store artefact
    2 documents       -- the tenant's own uploaded facility documents
    3 formulas        -- figures computed by app/formulas.py
    4 procedures      -- procedural text and general guidance

The model is told which layer won; it never chooses. Every answer carries
the winning layer, the layers it diverged from, and a per-claim label, so
"the price list says 2.50" and "the procedure suggests 2.50" are not the
same sentence.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Sequence

PRECEDENCE_VERSION = "precedence.v1"

LAYERS: Sequence[Dict[str, Any]] = (
    {"rank": 1, "layer": "certified", "source": "certified_store_artefact",
     "why": "a certified artefact is the strongest claim this platform can make"},
    {"rank": 2, "layer": "documents", "source": "uploaded_document",
     "why": "the tenant's own uploaded facility documents govern over derived text"},
    {"rank": 3, "layer": "formulas", "source": "computed_formula",
     "why": "a computed figure is authoritative over prose, but not over a document"},
    {"rank": 4, "layer": "procedures", "source": "procedure_text",
     "why": "procedural guidance is the fallback layer"},
)

_RANK = {item["layer"]: int(item["rank"]) for item in LAYERS}


def ladder() -> Dict[str, Any]:
    return {"version": PRECEDENCE_VERSION, "layers": [dict(item) for item in LAYERS]}


def label(layer: str) -> Dict[str, Any]:
    """Per-claim label for the layer a claim came from."""
    name = str(layer or "procedures")
    rank = _RANK.get(name, 4)
    return {"layer": name, "rank": rank, "authority": f"{rank}/4", "version": PRECEDENCE_VERSION}


def winner(claims: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """The winning claim, the losers, and the divergence record."""
    ranked: List[Dict[str, Any]] = []
    for claim in claims or ():
        if not isinstance(claim, dict):
            continue
        item = dict(claim)
        item["layer"] = str(item.get("layer") or "procedures")
        item["rank"] = _RANK.get(item["layer"], 4)
        ranked.append(item)
    if not ranked:
        return {
            "version": PRECEDENCE_VERSION,
            "winner": None,
            "label": label("procedures"),
            "divergence": [],
        }
    ranked.sort(key=lambda item: (item["rank"], -float(item.get("score") or 0.0)))
    top = ranked[0]
    return {
        "version": PRECEDENCE_VERSION,
        "winner": top,
        "label": label(top["layer"]),
        "divergence": [
            {
                "layer": item["layer"],
                "value": item.get("value"),
                "lost_to": top["layer"],
                "because": f"layer {item['layer']} ranks below {top['layer']} in {PRECEDENCE_VERSION}",
            }
            for item in ranked[1:]
        ],
    }
