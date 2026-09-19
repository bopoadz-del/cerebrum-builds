"""Declarative workflows this platform runs (see workflows.json).

Written by the factory WRITER role (codewhale exec)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

_PATH = Path(__file__).resolve().parent / "workflows.json"


def load() -> Dict[str, Any]:
    """The declared workflows, read from disk (no import-time state)."""
    if not _PATH.is_file():
        return {"schema_version": "workflows.v1", "workflows": []}
    return json.loads(_PATH.read_text(encoding="utf-8"))


def for_capability(capability_id: str) -> List[Dict[str, Any]]:
    """Workflows owned by one capability."""
    return [w for w in load().get("workflows", []) if w.get("capability") == capability_id]
