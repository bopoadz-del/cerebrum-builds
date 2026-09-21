"""Authority: precedence.v1, divergence records and per-claim labels.

Written by the factory WRITER role (codewhale exec)

An answer from this platform is never anonymous. Every retrieved claim carries
the layer it came from, and the model is TOLD which layer wins -- it does not
choose:

    layer 1  certified        certified standards, contracts, signed policies
    layer 2  documents        the property's own uploaded manuals / SOPs / rate sheets
    layer 3  formulas         computed results (folio totals, occupancy, ADR/RevPAR)
    layer 4  procedures       free-text operational guidance with no document behind it

When two layers disagree about the same key, the higher layer wins and the
disagreement is recorded -- a divergence record, not a silently dropped
source. ``authority_ladder.v1.json`` is the versioned data form of the same
precedence.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

LADDER: Tuple[Tuple[int, str], ...] = (
    (1, "certified"),
    (2, "documents"),
    (3, "formulas"),
    (4, "procedures"),
)

LAYER_OF: Dict[str, int] = {name: rank for rank, name in LADDER}
LABELS: Tuple[str, ...] = tuple(name for _rank, name in LADDER)
HIGHEST = LADDER[0][1]

LADDER_FILE = Path(__file__).resolve().parent / "authority_ladder.v1.json"


def ladder_document() -> Dict[str, Any]:
    return {
        "schema": "precedence.v1",
        "ordered": [{"rank": rank, "layer": name} for rank, name in LADDER],
        "rule": "lowest rank wins; the model is told the winner and never chooses",
    }


def write_ladder() -> Path:
    LADDER_FILE.write_text(
        json.dumps(ladder_document(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return LADDER_FILE


def rank_of(label: Optional[str]) -> int:
    return LAYER_OF.get(str(label or "").strip().lower(), len(LADDER) + 1)


def label_of(rank: int) -> str:
    for value, name in LADDER:
        if value == rank:
            return name
    return "procedures"


def winner(labels: Iterable[str]) -> str:
    """The highest-authority label among those present."""
    present = [str(item).strip().lower() for item in labels if str(item or "").strip()]
    if not present:
        return "procedures"
    return min(present, key=rank_of)


def divergence(key: str, values: Sequence[Tuple[str, Any]]) -> Optional[Dict[str, Any]]:
    """Record a disagreement between layers about one key.

    ``values`` is ``(label, value)`` in any order. Returns None when every
    layer that spoke agrees, or when only one layer spoke.
    """
    distinct = {str(value) for _label, value in values if value not in (None, "")}
    if len(distinct) <= 1:
        return None
    ordered = sorted(values, key=lambda item: rank_of(item[0]))
    chosen_label, chosen_value = ordered[0]
    return {
        "key": key,
        "winner": {"layer": chosen_label, "value": chosen_value},
        "diverges": [
            {"layer": label, "value": value}
            for label, value in ordered[1:]
            if str(value) != str(chosen_value)
        ],
    }


def label_answer(label: str, claims: Sequence[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    """The authority envelope every answer carries."""
    return {
        "authority": label,
        "rank": rank_of(label),
        "precedence": "precedence.v1",
        "claims": list(claims or []),
    }
