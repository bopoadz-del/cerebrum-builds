"""Authority precedence (precedence.v1) for the DentalDesk Clinic Manager.

Clinical and financial answers are produced from four ranked layers, held as
versioned data. The model never chooses the winner: :func:`resolve` sorts the
claims by layer rank and returns the winner plus every divergence it found, so
an answer can always be audited back to the layer that produced it.

    1. certified   — signed clinical/financial records (highest authority)
    2. documents   — uploaded documents (visit notes, invoices, consent forms)
    3. formulas    — arithmetic the platform computed
    4. procedures  — standing practice procedure / defaults (lowest authority)

Pure stdlib, no network, no model call.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

PRECEDENCE_VERSION = "precedence.v1"

#: Rank 1 = highest authority. Declared as data so a later revision can move a
#: layer without touching a call site.
LAYER_RANKS: Dict[str, int] = {
    "certified": 1,
    "documents": 2,
    "formulas": 3,
    "procedures": 4,
}

#: Human-facing labels stamped onto every claim in an answer.
LAYER_LABELS: Dict[str, str] = {
    "certified": "certified record (highest authority)",
    "documents": "uploaded document",
    "formulas": "platform formula",
    "procedures": "practice procedure (lowest authority)",
}


class AuthorityError(ValueError):
    """A claim names a layer this version of precedence.v1 does not rank."""


@dataclass(frozen=True)
class Claim:
    """One layer's answer for a subject."""

    subject: str
    layer: str
    value: Any
    source_ref: str = ""
    recorded_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subject": self.subject,
            "layer": self.layer,
            "label": LAYER_LABELS.get(self.layer, self.layer),
            "value": self.value,
            "source_ref": self.source_ref,
            "recorded_at": self.recorded_at,
        }


@dataclass
class Resolution:
    """The winner plus every divergence, with per-claim labels."""

    subject: str
    winner: Dict[str, Any] = field(default_factory=dict)
    divergences: List[Dict[str, Any]] = field(default_factory=list)
    precedence: str = PRECEDENCE_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "precedence": self.precedence,
            "subject": self.subject,
            "winner": self.winner,
            "divergences": self.divergences,
        }


def rank_of(layer: str) -> int:
    key = str(layer or "").strip().lower()
    if key not in LAYER_RANKS:
        raise AuthorityError(
            f"unknown authority layer {layer!r}; precedence.v1 ranks "
            + ", ".join(sorted(LAYER_RANKS))
        )
    return LAYER_RANKS[key]


def resolve(subject: str, claims: Iterable[Any]) -> Resolution:
    """Rank the claims for one subject. Deterministic, no model call."""
    rows: List[Dict[str, Any]] = []
    for raw in claims or ():
        claim = raw if isinstance(raw, Claim) else Claim(**dict(raw))
        rank_of(claim.layer)
        entry = claim.to_dict()
        entry["rank"] = LAYER_RANKS[claim.layer]
        rows.append(entry)
    if not rows:
        return Resolution(subject=subject)
    rows.sort(key=lambda item: (item["rank"], str(item.get("source_ref") or "")))
    winner = rows[0]
    divergences = [
        {
            "layer": item["layer"],
            "label": item["label"],
            "value": item["value"],
            "source_ref": item["source_ref"],
            "lost_to": winner["layer"],
        }
        for item in rows[1:]
        if item["value"] != winner["value"]
    ]
    return Resolution(subject=subject, winner=winner, divergences=divergences)


def load_ledger(path: str | Path) -> Sequence[Dict[str, Any]]:
    """Read a precedence ledger (a JSON list of claims) from disk."""
    target = Path(path)
    if not target.is_file():
        return []
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return data if isinstance(data, list) else []
