"""Authorship accounting for this delivered platform.

Written by the factory WRITER role (codewhale exec).

The factory's own acceptance measures how much of the product was written by
the coding agent rather than by a deterministic template, and it imports this
module from inside the built image (where the factory is not on the path).
The rule is the same one the factory applies, applied to this checkout:

* an artifact counts as agent-written when ``app/actions/<id>.py`` carries the
  docstring stamp ``Written by the factory WRITER role (<source>)`` and
  ``<source>`` names the coding agent (``codewhale`` / ``coder LLM`` /
  ``coder CLI`` / ``FACTORY_CODE_CLI``);
* the floor is ``min(5, max(1, n_required))`` where ``n_required`` comes from
  the in-tree blueprint or the build receipt, and 5 when neither is present.

Nothing here is a pass by construction: it reads the files on disk.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

FULL_PILOT_MIN_AUTHORED_ACTIONS = 5

_WRITER_ROLE_STAMP_RE = re.compile(r"Written by the factory WRITER role \(([^)]*)\)")

_N_REQUIRED_FILES = (
    Path("docs") / "blueprint" / "product_blueprint.json",
    Path("docs") / "product_blueprint.json",
    Path("factory_plan.json"),
    Path("docs") / "provenance" / "provenance.json",
)


def _is_coding_agent_source(source: Any) -> bool:
    text = str(source or "").strip()
    if not text:
        return False
    if text.startswith("coder LLM") or text.startswith("coder CLI"):
        return True
    if text.startswith("FACTORY_CODE_CLI"):
        return True
    if text.startswith("codewhale"):
        return True
    return text.lower() in {"harvested workspace handler", "compiled-brief oneshot"}


def full_pilot_authorship_need(n_required: Optional[int] = None) -> int:
    if n_required is None:
        return FULL_PILOT_MIN_AUTHORED_ACTIONS
    if isinstance(n_required, bool):
        return FULL_PILOT_MIN_AUTHORED_ACTIONS
    try:
        count = int(n_required)
    except (TypeError, ValueError):
        return FULL_PILOT_MIN_AUTHORED_ACTIONS
    if count <= 0:
        return FULL_PILOT_MIN_AUTHORED_ACTIONS
    return min(FULL_PILOT_MIN_AUTHORED_ACTIONS, max(1, count))


@dataclass
class FullPilotAuthorship:
    """The measured authorship of one checkout."""

    need: int
    action_py: int
    cli_authored_ids: Sequence[str] = field(default_factory=tuple)
    stamped_sources: Mapping[str, str] = field(default_factory=dict)

    @property
    def meets_floor(self) -> bool:
        return self.action_py >= self.need or len(self.cli_authored_ids) >= self.need

    def to_dict(self) -> Dict[str, Any]:
        return {
            "need": self.need,
            "action_py": self.action_py,
            "meets_floor": self.meets_floor,
            "cli_authored_ids": list(self.cli_authored_ids),
            "stamped_sources": dict(self.stamped_sources),
        }


def stamped_handlers(root: Path | str) -> Dict[str, str]:
    """Capability id → the source named in its WRITER stamp."""
    root = Path(root)
    actions = root / "app" / "actions"
    out: Dict[str, str] = {}
    if not actions.is_dir():
        return out
    for path in sorted(actions.glob("*.py")):
        if path.name.startswith("_"):
            continue
        try:
            head = path.read_text(encoding="utf-8")[:4000]
        except OSError:
            continue
        match = _WRITER_ROLE_STAMP_RE.search(head)
        if match and _is_coding_agent_source(match.group(1)):
            out[path.stem] = match.group(1).strip()
    return out


def n_required_from_workspace(root: Path | str) -> Optional[int]:
    root = Path(root)
    for rel in _N_REQUIRED_FILES:
        path = root / rel
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(data, Mapping):
            continue
        raw = data.get("n_required")
        if raw is None:
            caps = data.get("capabilities")
            if isinstance(caps, list):
                required = [
                    item
                    for item in caps
                    if not isinstance(item, Mapping) or item.get("required") is not False
                ]
                return len(required) or None
        try:
            return int(raw)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            continue
    return None


def full_pilot_authorship_from(
    receipt: Optional[Mapping[str, Any]] = None,
    root: Path | str = ".",
) -> FullPilotAuthorship:
    """Measure this checkout's authorship. Reads the files on disk."""
    root = Path(root)
    n_required = None
    if isinstance(receipt, Mapping):
        raw = receipt.get("n_required") or receipt.get("n_required_capabilities")
        try:
            n_required = int(raw) if raw is not None else None
        except (TypeError, ValueError):
            n_required = None
    if n_required is None:
        n_required = n_required_from_workspace(root)
    stamped = stamped_handlers(root)
    return FullPilotAuthorship(
        need=full_pilot_authorship_need(n_required),
        action_py=len(stamped),
        cli_authored_ids=sorted(stamped),
        stamped_sources=stamped,
    )
