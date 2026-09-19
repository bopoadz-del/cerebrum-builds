"""Beverage formulas of record, versioned as data (see universal_definitions.json)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

_PATH = Path(__file__).resolve().parent / "universal_definitions.json"
FORMULA_VERSION = "formulas.v1"


def definitions() -> Dict[str, Any]:
    if not _PATH.is_file():
        return {"version": FORMULA_VERSION, "formulas": {}}
    return json.loads(_PATH.read_text(encoding="utf-8"))


def names() -> List[str]:
    return sorted((definitions().get("formulas") or {}).keys())


def get(name: str) -> Optional[Dict[str, Any]]:
    return (definitions().get("formulas") or {}).get(str(name or ""))
