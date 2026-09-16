"""precedence.v1 -- which source wins, as versioned data.

Written by the factory WRITER role (codewhale exec)

Layer order, highest first:

    1 certified        regulator-approved guidance (certified=True)
    2 documents        the hotel's own ingested documents
    3 formulas         the versioned formula registry (app.formulas)
    4 procedures       operating procedures and notes

The model is TOLD the winner: ``resolve()`` returns the winner plus a
divergence record for every lower layer that disagrees, and every claim carries
the label of the layer it came from. The model never chooses a source and never
silently merges two of them.

Scope
-----
READS  its own versioned data (this module), the caller's candidate set.
WRITES nothing.
NEVER  network, ``vendor/**``, another capability's table.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

PRECEDENCE_VERSION = "precedence.v1"

#: Highest layer first. The order IS the policy; it is data, not prose.
LAYERS: Tuple[Tuple[int, str], ...] = (
    (1, "certified"),
    (2, "documents"),
    (3, "formulas"),
    (4, "procedures"),
)

LAYER_NAMES: Dict[int, str] = {rank: name for rank, name in LAYERS}
LAYER_RANK: Dict[str, int] = {name: rank for rank, name in LAYERS}


@dataclass(frozen=True)
class Claim:
    """One statement from one layer, with the label that must travel with it."""

    layer: int
    source: str
    text: str
    detail: Dict[str, Any] = field(default_factory=dict)

    @property
    def label(self) -> Dict[str, Any]:
        return {
            "precedence": PRECEDENCE_VERSION,
            "layer": self.layer,
            "layer_name": LAYER_NAMES.get(self.layer, "unknown"),
            "source": self.source,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {"text": self.text, "detail": dict(self.detail), **self.label}


class AuthorityError(ValueError):
    """A claim was labelled with a layer this platform does not define."""


def validate_claim(claim: Claim) -> Claim:
    if claim.layer not in LAYER_NAMES:
        raise AuthorityError(f"unknown precedence layer: {claim.layer}")
    if not str(claim.text).strip():
        raise AuthorityError("a claim needs text")
    return claim


def resolve(claims: Iterable[Claim]) -> Dict[str, Any]:
    """The winner, the labelled claims, and every divergence.

    ``winner`` is the highest-layer claim. Ties inside a layer are broken by
    source name so the answer is deterministic, and each losing claim that
    disagrees (different text) becomes a divergence record.
    """
    valid: List[Claim] = [validate_claim(c) for c in claims]
    labelled = [c.to_dict() for c in valid]
    if not valid:
        return {
            "precedence": PRECEDENCE_VERSION,
            "winner": None,
            "claims": [],
            "divergences": [],
            "labels": [],
        }
    ordered = sorted(valid, key=lambda c: (c.layer, c.source))
    winner = ordered[0]
    divergences = [
        {
            "layer": claim.layer,
            "layer_name": LAYER_NAMES.get(claim.layer, "unknown"),
            "source": claim.source,
            "against": winner.source,
            "agrees": claim.text.strip() == winner.text.strip(),
            "text": claim.text,
        }
        for claim in ordered[1:]
    ]
    return {
        "precedence": PRECEDENCE_VERSION,
        "winner": winner.to_dict(),
        "claims": labelled,
        "divergences": divergences,
        "labels": [claim.label for claim in ordered],
    }


def layer_of(source_kind: str, *, certified: bool = False) -> int:
    """Rank a source kind, honouring the certified flag on document rows."""
    kind = str(source_kind or "").strip().lower()
    if certified or kind == "certified":
        return 1
    if kind in ("document", "documents", "corpus"):
        return 2
    if kind in ("formula", "formulas", "calculation"):
        return 3
    if kind in ("procedure", "procedures", "note", "notes"):
        return 4
    raise AuthorityError(f"cannot rank source kind: {source_kind!r}")


def declaration() -> Dict[str, Any]:
    """The precedence table as data, for docs and for the answer endpoint."""
    return {
        "precedence": PRECEDENCE_VERSION,
        "layers": [{"rank": rank, "name": name} for rank, name in LAYERS],
    }
