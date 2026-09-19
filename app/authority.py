"""Authority ladder (precedence.v1) for Bakery Chain Operations answers.

Written by the factory WRITER role (codewhale exec)

Four layers, in precedence order, as versioned data — never as prose the model
may reorder:

    1. ``certified``   — signed certificates and released test results
    2. ``documents``   — approved specifications and standards
    3. ``formulas``    — the recipe/formula of record
    4. ``procedures``  — work instructions and SOPs

The model is told which layer won; it never chooses. Every answer carries the
winner plus per-claim labels and the divergence records that were rejected.

Scope
-----
READS  the caller's corpus description (precedence labels).
WRITES nothing.
NEVER  network, ``vendor/**``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

PRECEDENCE_VERSION = "precedence.v1"

#: Highest first. The index is the layer's authority rank.
LAYERS: Tuple[str, ...] = ("certified", "documents", "formulas", "procedures")

_ALIASES = {
    "certificate": "certified",
    "cert": "certified",
    "signed": "certified",
    "document": "documents",
    "spec": "documents",
    "specification": "documents",
    "standard": "documents",
    "formula": "formulas",
    "recipe": "formulas",
    "procedure": "procedures",
    "sop": "procedures",
    "manual": "procedures",
}


def normalise_layer(layer: Optional[str]) -> Optional[str]:
    if layer is None:
        return None
    key = str(layer).strip().lower()
    if key in LAYERS:
        return key
    return _ALIASES.get(key)


def rank(layer: Optional[str]) -> int:
    """0 is strongest. An unknown layer is weakest, never silently first."""
    normalised = normalise_layer(layer)
    if normalised is None:
        return len(LAYERS)
    return LAYERS.index(normalised)


def resolve(claims: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Pick the winning claim and record every divergence.

    ``claims`` is a list of ``{"layer": str, "value": Any, "source": str}``.
    The winner is the highest layer; ties keep the first (stable) and are
    reported as ``tie`` rather than hidden.
    """
    prepared: List[Dict[str, Any]] = []
    for index, claim in enumerate(claims or ()):
        if not isinstance(claim, dict):
            continue
        layer = normalise_layer(claim.get("layer"))
        prepared.append(
            {
                "index": index,
                "layer": layer,
                "rank": rank(layer),
                "value": claim.get("value"),
                "source": claim.get("source") or claim.get("doc_id"),
                "label": claim.get("label") or layer,
            }
        )
    if not prepared:
        return {"version": PRECEDENCE_VERSION, "winner": None,
                "divergences": [], "labels": []}
    prepared.sort(key=lambda item: (item["rank"], item["index"]))
    winner = prepared[0]
    divergences = [
        {
            "layer": item["layer"],
            "label": item["label"],
            "value": item["value"],
            "source": item["source"],
            "rejected_because": f"lower precedence than {winner['layer']}",
        }
        for item in prepared[1:]
        if item["value"] != winner["value"]
    ]
    labels = [
        {"claim": item["label"], "layer": item["layer"], "source": item["source"],
         "authority": "winner" if item is winner else "rejected"}
        for item in prepared
    ]
    return {
        "version": PRECEDENCE_VERSION,
        "winner": {"layer": winner["layer"], "value": winner["value"],
                   "source": winner["source"]},
        "tie": any(item["rank"] == winner["rank"] for item in prepared[1:]),
        "divergences": divergences,
        "labels": labels,
    }
