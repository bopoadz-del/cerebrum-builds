"""Authority: which layer a claim came from, and who wins when they differ.

The model is told the winner; it never chooses. Four layers, strongest
first, versioned as data under ``precedence.v1``:

    1. certified   — a fact the brokerage has pinned as authoritative
                     (a signed-off project sheet revision)
    2. documents   — retrieved from an ingested project sheet, quoted
    3. formulas    — computed by app/formulas.py from stated inputs
    4. procedures  — the platform's own script/flow wording

Every answer CallOps gives carries this envelope: the winning layer, one
label per claim, and a divergence record for each claim where two layers
disagree — the price a document states versus the price a formula derives,
for example. A claim nothing supports is withheld, and the envelope says
so, because an invented handover date is the liability this platform exists
to avoid.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

PRECEDENCE_ID = "precedence.v1"

#: Strongest first. The index is the rank; lower wins.
LAYERS: tuple[str, ...] = ("certified", "documents", "formulas", "procedures")

LAYER_DESCRIPTIONS: Dict[str, str] = {
    "certified": "a fact the brokerage pinned as authoritative",
    "documents": "retrieved from an ingested project sheet, quoted verbatim",
    "formulas": "computed by app/formulas.py from stated inputs",
    "procedures": "the platform's own script or flow wording",
}


def rank(layer: str) -> int:
    try:
        return LAYERS.index(str(layer))
    except ValueError:
        return len(LAYERS)


@dataclass(frozen=True)
class Claim:
    """One assertion in an answer, with the layer that carries it."""

    name: str
    value: Any
    layer: str
    source: str = ""
    detail: str = ""

    def label(self) -> Dict[str, Any]:
        return {
            "claim": self.name,
            "layer": self.layer,
            "label": f"{self.layer}:{self.source}" if self.source else self.layer,
            "source": self.source,
            "precedence": PRECEDENCE_ID,
            "detail": self.detail,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {**self.label(), "value": self.value}


def precedence_document() -> Dict[str, Any]:
    """``precedence.v1`` as data — the versioned contract the model is told."""
    return {
        "id": PRECEDENCE_ID,
        "layers": [
            {
                "layer": layer,
                "rank": index + 1,
                "means": LAYER_DESCRIPTIONS[layer],
            }
            for index, layer in enumerate(LAYERS)
        ],
        "rule": "the strongest layer that supports a claim carries it; a claim "
        "no layer supports is withheld, never improvised",
        "divergence": "when two layers disagree, both are recorded and the "
        "stronger one is reported",
    }


def resolve(claims: Iterable[Claim]) -> Dict[str, Any]:
    """Winner, per-claim labels and divergence records for one answer."""
    items = [c for c in claims if c is not None]
    if not items:
        return {
            "precedence": PRECEDENCE_ID,
            "layer": None,
            "label": "withheld:no-supporting-layer",
            "claim_labels": [],
            "divergence": [],
            "withheld": True,
        }
    ordered = sorted(items, key=lambda c: (rank(c.layer), c.name))
    winner = ordered[0]
    by_claim: Dict[str, List[Claim]] = {}
    for item in ordered:
        by_claim.setdefault(item.name, []).append(item)
    divergence: List[Dict[str, Any]] = []
    for name, group in sorted(by_claim.items()):
        values = {str(item.value) for item in group}
        if len(values) > 1:
            divergence.append(
                {
                    "claim": name,
                    "layers": [
                        {"layer": item.layer, "value": item.value, "source": item.source}
                        for item in group
                    ],
                    "reported": group[0].layer,
                    "precedence": PRECEDENCE_ID,
                }
            )
    return {
        "precedence": PRECEDENCE_ID,
        "layer": winner.layer,
        "label": winner.label()["label"],
        "claim_labels": [item.label() for item in ordered],
        "divergence": divergence,
        "withheld": False,
    }


def envelope(
    claims: Iterable[Claim],
    *,
    withheld_claim: Optional[str] = None,
    refused: Optional[str] = None,
) -> Dict[str, Any]:
    """The authority block every answer carries."""
    resolved = resolve(claims)
    if withheld_claim and not any(
        item["claim"] == withheld_claim for item in resolved["claim_labels"]
    ):
        resolved = dict(resolved)
        resolved.setdefault("withheld_claims", [])
        resolved["withheld_claims"] = sorted(
            set(list(resolved.get("withheld_claims") or []) + [withheld_claim])
        )
        if not resolved.get("layer"):
            resolved["label"] = f"withheld:{withheld_claim}"
            resolved["withheld"] = True
    if refused:
        resolved = dict(resolved)
        resolved["refused"] = refused
    return resolved


def certification_record(claim: str, value: Any, source: str) -> Dict[str, Any]:
    """The shape of a certified fact, as the operator pins it."""
    return {
        "claim": claim,
        "value": value,
        "layer": "certified",
        "source": source,
        "precedence": PRECEDENCE_ID,
    }
