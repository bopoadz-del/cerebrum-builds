"""precedence.v1 — authority layers for RetailOS answers.

Written by the factory WRITER role (codewhale exec).

Every answer this platform gives about firm practice is assembled from
versioned data, and the winner between conflicting sources is decided here —
never by the model:

    layer 1  certified      the firm's certified practice protocols
    layer 2  documents      the firm's own SOPs and ingested corpus
    layer 3  formulas       calculated / formula-derived values
    layer 4  procedures     operational procedure notes

The ladder is data (``precedence_ladder.v1.json``, emitted with the
platform). Each answer carries its per-claim layer label and every
divergence between sources, so a reader can see which source was overruled
and why. The model is told the winner; it never chooses.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

PRECEDENCE_VERSION = "precedence.v1"

LAYER_CERTIFIED = 1
LAYER_DOCUMENTS = 2
LAYER_FORMULAS = 3
LAYER_PROCEDURES = 4

LAYER_NAMES = {
    LAYER_CERTIFIED: "certified",
    LAYER_DOCUMENTS: "documents",
    LAYER_FORMULAS: "formulas",
    LAYER_PROCEDURES: "procedures",
}

DEFAULT_LADDER: Tuple[Dict[str, Any], ...] = (
    {
        "layer": LAYER_CERTIFIED,
        "id": "certified",
        "source": "practice_protocols",
        "description": "Certified practice protocols issued by the firm principal.",
    },
    {
        "layer": LAYER_DOCUMENTS,
        "id": "documents",
        "source": "firm_corpus",
        "description": "The firm's own SOPs, guidance and ingested documents.",
    },
    {
        "layer": LAYER_FORMULAS,
        "id": "formulas",
        "source": "app.formulas",
        "description": "Billable, tax and total calculations derived by formula.",
    },
    {
        "layer": LAYER_PROCEDURES,
        "id": "procedures",
        "source": "operational_notes",
        "description": "Front-desk and operational procedure notes.",
    },
)


@dataclass
class Claim:
    """One statement, its source layer, and the chart of who disagrees."""

    text: str
    layer: int
    source: str
    value: Any = None
    divergences: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def label(self) -> str:
        return "%s:%s" % (LAYER_NAMES.get(self.layer, "unknown"), self.source)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "layer": self.layer,
            "layer_name": LAYER_NAMES.get(self.layer, "unknown"),
            "source": self.source,
            "label": self.label,
            "value": self.value,
            "divergences": list(self.divergences),
        }


def ladder_path() -> Path:
    return Path(__file__).resolve().parent / "precedence_ladder.v1.json"


def load_ladder() -> List[Dict[str, Any]]:
    """The ladder as versioned data, or the compiled default."""
    path = ladder_path()
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = None
        layers = (data or {}).get("layers") if isinstance(data, dict) else None
        if isinstance(layers, list) and layers:
            return [dict(item) for item in layers if isinstance(item, dict)]
    return [dict(item) for item in DEFAULT_LADDER]


def leader(layers: Optional[Iterable[Mapping[str, Any]]] = None) -> Dict[str, Any]:
    """The winning layer for a conflict: lowest layer number wins."""
    entries = list(layers or load_ladder())
    if not entries:
        return dict(DEFAULT_LADDER[0])
    return dict(min(entries, key=lambda item: int(item.get("layer") or 99)))


def resolve(claims: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """Decide the winner between conflicting claims, and record divergences."""
    normalised: List[Claim] = []
    for raw in claims or ():
        if not isinstance(raw, Mapping):
            continue
        normalised.append(
            Claim(
                text=str(raw.get("text") or ""),
                layer=int(raw.get("layer") or LAYER_PROCEDURES),
                source=str(raw.get("source") or "unknown"),
                value=raw.get("value"),
            )
        )
    if not normalised:
        return {
            "version": PRECEDENCE_VERSION,
            "winner": None,
            "claims": [],
            "divergences": [],
        }
    ranked = sorted(normalised, key=lambda claim: (claim.layer, claim.source))
    winner = ranked[0]
    for other in ranked[1:]:
        if str(other.value) != str(winner.value):
            winner.divergences.append(
                {
                    "overruled_layer": other.layer,
                    "overruled_layer_name": LAYER_NAMES.get(other.layer, "unknown"),
                    "overruled_source": other.source,
                    "overruled_value": other.value,
                    "reason": "layer %d precedes layer %d"
                    % (winner.layer, other.layer),
                }
            )
    return {
        "version": PRECEDENCE_VERSION,
        "winner": winner.to_dict(),
        "claims": [claim.to_dict() for claim in ranked],
        "divergences": list(winner.divergences),
    }


def precedent(tenant: str, query: str, *, top_k: int = 3) -> Dict[str, Any]:
    """Documents-layer claims for a query, resolved with their divergences."""
    from app import retrieval

    hits = retrieval.search(tenant, query, top_k=top_k)
    claims = [
        {
            "text": hit.get("text"),
            "layer": LAYER_DOCUMENTS,
            "source": (hit.get("metadata") or {}).get("collection") or "firm_corpus",
            "value": hit.get("text"),
        }
        for hit in hits
    ]
    resolved = resolve(claims)
    resolved["grounded"] = bool(claims)
    resolved["query"] = query
    resolved["tenant"] = tenant
    return resolved
