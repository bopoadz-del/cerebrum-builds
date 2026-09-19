"""Product-side factory measurement helpers.

The platform's own `scripts/acceptance.py` measures the authorship floor
("is this a launching-ready full pilot, or a thin scaffold?") in-tree, so the
shipped product can judge itself without the factory host. That harness
imports ``app.factory.build.authorship``; this package is that import target.

It implements the factory's rule with the product's own provenance:

* a handler is agent-written when its ``app/actions/*.py`` docstring carries
  the WRITER stamp and the stamped source names a coding agent;
* the floor is ``need = min(5, max(1, n_required))`` agent-written handlers
  (or explicit ``cli_authored_ids``), unknown ``n_required`` meaning 5.

std lib only. No network.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

__all__ = [
    "FULL_PILOT_AUTHORSHIP_CHECK",
    "FULL_PILOT_MIN_AUTHORED_ACTIONS",
    "FullPilotAuthorship",
    "agent_written_handlers",
    "cli_authored_ids_from",
    "coding_agent_artifact_ids",
    "full_pilot_authorship_from",
    "full_pilot_authorship_need",
    "is_action_artifact_id",
    "is_coding_agent_source",
    "n_required_capabilities_from",
    "writer_authorship_counts",
]

FULL_PILOT_AUTHORSHIP_CHECK = "full_pilot_authorship"
FULL_PILOT_MIN_AUTHORED_ACTIONS = 5

_WRITER_ROLE_STAMP_RE = re.compile(r"Written by the factory WRITER role \(([^)]*)\)")

_BLUEPRINT_RELS = (
    Path("docs") / "blueprint" / "product_blueprint.json",
    Path("docs") / "product_blueprint.json",
    Path("factory_plan.json"),
)


def is_coding_agent_source(source: Any) -> bool:
    """True for a coding-agent WRITER stamp (CLI or LLM), not a template."""
    text = str(source or "").strip()
    if not text:
        return False
    if text.startswith(("coder LLM", "coder CLI", "FACTORY_CODE_CLI", "codewhale", "cli ")):
        return True
    return text.lower() in {"harvested workspace handler", "compiled-brief oneshot"}


def agent_written_handlers(workspace: Path | str | None) -> List[str]:
    """``app/actions/*.py`` modules whose stamp names a coding agent."""
    if workspace is None:
        return []
    root = Path(workspace)
    actions = root / "app" / "actions"
    if not actions.is_dir():
        return []
    ids: List[str] = []
    for path in sorted(actions.glob("*.py")):
        if path.name == "__init__.py" or path.name.startswith("_"):
            continue
        try:
            head = path.read_text(encoding="utf-8")[:4000]
        except OSError:
            continue
        match = _WRITER_ROLE_STAMP_RE.search(head)
        if match and is_coding_agent_source(match.group(1)):
            ids.append(path.stem)
    return ids


def is_action_artifact_id(item: Any) -> bool:
    text = str(item or "").strip()
    return bool(text) and not text.startswith("__")


def coding_agent_artifact_ids(sources: Optional[Mapping[str, Any]]) -> List[str]:
    return sorted(
        str(key) for key, value in dict(sources or {}).items() if is_coding_agent_source(value)
    )


def writer_authorship_counts(sources: Optional[Mapping[str, Any]]) -> Dict[str, int]:
    written = len(coding_agent_artifact_ids(sources))
    total = len(dict(sources or {}))
    return {"artifacts": total, "agent_written": written, "templated": total - written}


def _as_nonneg_int(value: Any) -> Optional[int]:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def n_required_capabilities_from(
    status: Optional[Mapping[str, Any]] = None,
    workspace: Path | str | None = None,
) -> Optional[int]:
    """Required-capability count from the receipt, else the blueprint."""
    blob = dict(status or {})
    for key in ("n_required", "n_required_capabilities"):
        found = _as_nonneg_int(blob.get(key))
        if found:
            return found
    if workspace is not None:
        for rel in _BLUEPRINT_RELS:
            path = Path(workspace) / rel
            if not path.is_file():
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            caps = data.get("capabilities")
            if isinstance(caps, list):
                required = [
                    cap
                    for cap in caps
                    if not isinstance(cap, dict) or cap.get("required") is not False
                ]
                if required:
                    return len(required)
    return None


def full_pilot_authorship_need(n_required: Optional[int] = None) -> int:
    if n_required is None:
        return FULL_PILOT_MIN_AUTHORED_ACTIONS
    try:
        value = int(n_required)
    except (TypeError, ValueError):
        return FULL_PILOT_MIN_AUTHORED_ACTIONS
    if value <= 0:
        return FULL_PILOT_MIN_AUTHORED_ACTIONS
    return min(FULL_PILOT_MIN_AUTHORED_ACTIONS, max(1, value))


def cli_authored_ids_from(status: Optional[Mapping[str, Any]]) -> Optional[List[str]]:
    """Explicit ``cli_authored_ids`` from the receipt, or None when absent."""
    blob = dict(status or {})
    dispatch = blob.get("brief_dispatch")
    if isinstance(dispatch, Mapping):
        blob = {**blob, **dispatch}
    if "cli_authored_ids" not in blob:
        return None
    ids: List[str] = []
    for item in blob.get("cli_authored_ids") or ():
        text = str(item or "").strip()
        if text and text not in ids:
            ids.append(text)
    return ids


@dataclass(frozen=True)
class FullPilotAuthorship:
    """Measured authorship against the launching-ready floor."""

    action_ids: List[str]
    cli_authored_ids: List[str]
    action_py: int
    measured: bool
    meets_floor: bool
    n_required: Optional[int] = None
    need: int = FULL_PILOT_MIN_AUTHORED_ACTIONS

    @property
    def below_floor(self) -> bool:
        return self.measured and not self.meets_floor


def full_pilot_authorship_from(
    status: Optional[Mapping[str, Any]] = None,
    workspace: Path | str | None = None,
    *,
    n_required: Optional[int] = None,
    plan: Any = None,
    blueprint: Any = None,
) -> FullPilotAuthorship:
    """Count agent-written action handlers / ``cli_authored_ids``."""
    blob = dict(status or {})
    resolved = n_required
    if resolved is None:
        resolved = n_required_capabilities_from(blob, workspace)
    if resolved is None and blueprint is not None:
        caps = getattr(blueprint, "capabilities", None) or ()
        ids = [cap for cap in caps if getattr(cap, "required", True) is not False]
        resolved = len(ids) or None
    need = full_pilot_authorship_need(resolved)

    cli_ids = cli_authored_ids_from(blob)
    action_ids = agent_written_handlers(workspace)
    action_py = len(action_ids)
    if action_py == 0:
        sources = blob.get("artifact_sources")
        if isinstance(sources, Mapping):
            action_ids = [
                cid for cid in coding_agent_artifact_ids(sources) if is_action_artifact_id(cid)
            ]
            action_py = len(action_ids)
    if action_py == 0:
        explicit = _as_nonneg_int((blob.get("authorship") or {}).get("action_py") if isinstance(blob.get("authorship"), Mapping) else None)
        if explicit is not None:
            action_py = explicit

    measured = bool(action_py or cli_ids is not None)
    meets = action_py >= need or len(cli_ids or []) >= need
    return FullPilotAuthorship(
        action_ids=list(action_ids),
        cli_authored_ids=list(cli_ids or []),
        action_py=action_py,
        measured=measured,
        meets_floor=bool(measured and meets),
        n_required=resolved,
        need=need,
    )
