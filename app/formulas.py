"""The versioned formula registry (precedence layer 3).

Written by the factory WRITER role (codewhale exec)

Every formula the front desk uses is versioned data, evaluated in process
with plain arithmetic -- the same formulas the vendored ``formula_executor``
block runs when a capability asks it to compute a stay charge. Nothing here
calls out; no expression is eval'd.

Scope
-----
READS  the caller's numbers (pure functions).
WRITES nothing.
NEVER  network; eval/exec; a formula the registry does not define.
"""

from __future__ import annotations

from typing import Any, Dict, List

VERSION = "formulas.v1"
HOUSE_ROOMS = 40
DEFAULT_NIGHTLY_RATE = 145.0

REGISTRY: List[Dict[str, Any]] = [
    {
        "key": "stay_nights",
        "version": "1.0.0",
        "description": "Nights between an arrival date and a departure date",
        "params": ["check_in_date", "check_out_date"],
    },
    {
        "key": "room_charge",
        "version": "1.0.0",
        "description": "Room charge for a stay at the house nightly rate",
        "params": ["nights", "nightly_rate"],
    },
    {
        "key": "occupancy_percent",
        "version": "1.0.0",
        "description": "Occupancy of a 40-room house for a given arrival count",
        "params": ["arrivals_count", "house_rooms"],
    },
]


class UnknownFormula(KeyError):
    """The registry does not define that formula."""


def _registry_map() -> Dict[str, Dict[str, Any]]:
    return {item["key"]: item for item in REGISTRY}


def evaluate(key: str, inputs: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Evaluate one versioned formula. Raises rather than guessing."""
    defined = _registry_map()
    if key not in defined:
        raise UnknownFormula(f"unknown formula: {key}")
    values = dict(inputs or {})
    spec = defined[key]
    if key == "stay_nights":
        from datetime import date

        start = date.fromisoformat(str(values.get("check_in_date")))
        end = date.fromisoformat(str(values.get("check_out_date")))
        nights = (end - start).days
        if nights <= 0:
            raise ValueError("check_out_date must be later than check_in_date")
        result = float(nights)
    elif key == "room_charge":
        nights = float(values.get("nights") or 0)
        rate = float(values.get("nightly_rate") or DEFAULT_NIGHTLY_RATE)
        if nights <= 0:
            raise ValueError("nights must be positive")
        result = round(nights * rate, 2)
    elif key == "occupancy_percent":
        arrivals = float(values.get("arrivals_count") or 0)
        rooms = float(values.get("house_rooms") or HOUSE_ROOMS)
        result = round(100.0 * arrivals / rooms, 2)
    else:  # pragma: no cover - registry is closed
        raise UnknownFormula(f"unknown formula: {key}")
    return {
        "key": key,
        "version": spec["version"],
        "inputs": values,
        "result": result,
        "layer": "formula",
    }


def declaration() -> Dict[str, Any]:
    """The registry as data, for GET /v1/formulas."""
    return {
        "ok": True,
        "version": VERSION,
        "formulas": REGISTRY,
        "house_rooms": HOUSE_ROOMS,
        "default_nightly_rate": DEFAULT_NIGHTLY_RATE,
        "evaluation": "in process, plain arithmetic, no eval/exec",
    }
