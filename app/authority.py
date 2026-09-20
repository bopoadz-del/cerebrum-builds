"""Authority layers for the FleetOps Back-Office Platform (precedence.v1).

Written by the factory WRITER role (codewhale exec)

Scope
  READS   the caller's question context, the versioned precedence document.
  WRITES  the caller's response (per-claim labels and divergence records).
  NEVER   choosing a winner by model opinion -- precedence is data, and the
          winner is computed here.

Layers, strongest first:

  1. certified   -- signed company policy (rate cards, deposit policy)
  2. documents   -- branch manuals and uploaded documents
  3. formulas    -- the pricing/maintenance formulas the platform executes
  4. procedures  -- day-to-day operating procedures

Every answer carries, per claim, the layer that produced it and every
divergence recorded between layers that disagree.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence

PRECEDENCE_VERSION = "precedence.v1"

#: Strongest first. The model is told the winner; it never chooses.
LAYER_ORDER: Sequence[str] = ("certified", "documents", "formulas", "procedures")

LAYER_LABELS: Dict[str, str] = {
    "certified": "certified policy",
    "documents": "documents",
    "formulas": "formulas",
    "procedures": "procedures",
}


class AuthorityError(ValueError):
    """A claim set that cannot be adjudicated as given."""


@dataclass
class Claim:
    """One assertion a layer makes about a field."""

    layer: str
    field: str
    value: Any
    source: str = ""
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "layer": self.layer,
            "field": self.field,
            "value": self.value,
            "source": self.source,
            "note": self.note,
        }


@dataclass
class Divergence:
    """Two layers disagreeing about one field; the winner is recorded."""

    field: str
    winner: str
    loser: str
    winner_value: Any
    loser_value: Any

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "winner": self.winner,
            "loser": self.loser,
            "winner_value": self.winner_value,
            "loser_value": self.loser_value,
        }


@dataclass
class Adjudication:
    """The precedence decision for a claim set."""

    version: str = PRECEDENCE_VERSION
    claims: List[Dict[str, Any]] = field(default_factory=list)
    divergences: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "claims": list(self.claims),
            "divergences": list(self.divergences),
        }


def layer_rank(layer: str) -> int:
    try:
        return LAYER_ORDER.index(str(layer))
    except ValueError:
        raise AuthorityError("unknown authority layer: %r" % (layer,)) from None


def adjudicate(claims: Iterable[Claim | Dict[str, Any]]) -> Adjudication:
    """Resolve competing claims field by field, by layer precedence.

    Every input claim is echoed with its layer label. Where two layers make
    claims about the same field, the stronger layer wins and the disagreement
    is recorded as a divergence -- never silently dropped.
    """
    normalised: List[Claim] = []
    for item in claims or ():
        if isinstance(item, Claim):
            normalised.append(item)
            continue
        if not isinstance(item, dict):
            raise AuthorityError("claims must be Claim objects or dicts")
        field_name = str(item.get("field") or "").strip()
        if not field_name:
            raise AuthorityError("a claim must name the field it is about")
        normalised.append(
            Claim(
                layer=str(item.get("layer") or ""),
                field=field_name,
                value=item.get("value"),
                source=str(item.get("source") or ""),
                note=str(item.get("note") or ""),
            )
        )
    for claim in normalised:
        layer_rank(claim.layer)  # unknown layer is refused, not ranked last

    decision = Adjudication()
    by_field: Dict[str, List[Claim]] = {}
    for claim in normalised:
        by_field.setdefault(claim.field, []).append(claim)

    for field_name in sorted(by_field):
        contenders = sorted(by_field[field_name], key=lambda c: layer_rank(c.layer))
        winner = contenders[0]
        decision.claims.append(
            {
                "field": field_name,
                "value": winner.value,
                "label": LAYER_LABELS.get(winner.layer, winner.layer),
                "layer": winner.layer,
                "source": winner.source,
                "decided_by": PRECEDENCE_VERSION,
            }
        )
        for loser in contenders[1:]:
            if loser.value == winner.value:
                continue
            decision.divergences.append(
                Divergence(
                    field=field_name,
                    winner=winner.layer,
                    loser=loser.layer,
                    winner_value=winner.value,
                    loser_value=loser.value,
                ).to_dict()
            )
    return decision


def winner_for(claims: Iterable[Claim | Dict[str, Any]], field_name: str) -> Optional[Claim]:
    """The strongest claim about one field, or None when nothing claims it."""
    best: Optional[Claim] = None
    for item in claims or ():
        claim = item if isinstance(item, Claim) else Claim(
            layer=str((item or {}).get("layer") or ""),
            field=str((item or {}).get("field") or ""),
            value=(item or {}).get("value"),
        )
        if claim.field != field_name:
            continue
        if best is None or layer_rank(claim.layer) < layer_rank(best.layer):
            best = claim
    return best


def claim_label(layer: str) -> Dict[str, Any]:
    """The label an answer carries so an operator sees where it came from.

    Unknown layers are refused (:class:`AuthorityError`) rather than
    labelled with a guess.
    """
    rank = layer_rank(layer)
    return {
        "layer": layer,
        "rank": rank,
        "label": LAYER_LABELS.get(layer, layer),
        "precedence": PRECEDENCE_VERSION,
    }
