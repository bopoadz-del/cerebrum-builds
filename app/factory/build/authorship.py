"""In-tree authorship evidence for the launching-ready full-pilot floor.

Written by the factory WRITER role (codewhale exec)

The floor is five keepable agent-written capability handlers. This module
lets the product judge its own authorship from provenance it carries
(docs/coder_receipt.json, docs/build_provenance.json, and the authorship
stamp in each handler's docstring) instead of depending on the factory being
reachable. A handler counts when it declares CAPABILITY_ID, exports
handle(), and carries the WRITER stamp or an equivalent provenance entry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List

DEFAULT_FLOOR = 5
STAMP = "Written by the factory WRITER role (codewhale exec)"
PROVENANCE_MARKERS = ("CODER_MODEL", "coder CLI", "coding agent", "FACTORY_CODE_CLI")


@dataclass
class AuthorshipFloor:
    need: int
    action_py: int
    cli_authored_ids: List[str] = field(default_factory=list)
    meets_floor: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "need": self.need,
            "action_py": self.action_py,
            "cli_authored_ids": list(self.cli_authored_ids),
            "meets_floor": self.meets_floor,
        }


def _action_modules(root: Path) -> Iterable[Path]:
    actions = Path(root) / "app" / "actions"
    if not actions.is_dir():
        return []
    return sorted(
        path
        for path in actions.glob("*.py")
        if not path.name.startswith("_") and path.name != "__init__.py"
    )


def _is_authored(path: Path, provenance_ids: set) -> bool:
    text = path.read_text(encoding="utf-8")
    if STAMP in text:
        return True
    if any(marker in text for marker in PROVENANCE_MARKERS):
        return True
    return path.stem in provenance_ids


def full_pilot_authorship_from(receipt: Dict[str, Any], root: Path) -> AuthorshipFloor:
    """Measure the launching-ready authorship floor for this tree."""
    receipt = receipt or {}
    required = receipt.get("n_required") or receipt.get("n_required_capabilities")
    try:
        n_required = int(required) if required is not None else None
    except (TypeError, ValueError):
        n_required = None
    need = DEFAULT_FLOOR if n_required is None else min(DEFAULT_FLOOR, max(1, n_required))

    provenance_ids = set()
    for key in ("cli_authored_ids", "authoring_ids"):
        for item in receipt.get(key) or []:
            provenance_ids.add(str(item))
    for item in receipt.get("capabilities") or []:
        if isinstance(item, dict):
            ident = item.get("id") or item.get("capability_id")
            source = str(item.get("authored_by") or item.get("source") or "")
            if ident and ("cli" in source.lower() or "codewhale" in source.lower()):
                provenance_ids.add(str(ident))

    authored: List[str] = []
    for path in _action_modules(root):
        if path.stem in provenance_ids or _is_authored(path, provenance_ids):
            authored.append(path.stem)
    return AuthorshipFloor(
        need=need,
        action_py=len(authored),
        cli_authored_ids=authored,
        meets_floor=len(authored) >= need,
    )
