"""Versioned formula registry -- precedence layer 3.

Written by the factory WRITER role (codewhale exec)

Every formula is data: an id, a version, the parameter set it needs, the unit
it answers in, and a small expression evaluated in a restricted namespace
(no builtins beyond the arithmetic whitelist). The vendored ``formula_executor``
block executes a formula for a capability; this registry is the platform's own
catalogue of the calculations it will defend in an answer.

Scope
-----
READS  its own versioned data; the caller's parameter values.
WRITES nothing.
NEVER  network, ``eval`` with builtins, ``vendor/**``.
"""

from __future__ import annotations

import ast
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Tuple

FORMULA_REGISTRY_VERSION = "hotel-front-desk.formulas.v1"

#: Functions a formula expression may call.
_ALLOWED_CALLS: Dict[str, Any] = {"round": round, "min": min, "max": max, "abs": abs}
_ALLOWED_NAMES: Dict[str, Any] = {"math": math, "pi": math.pi}


class FormulaError(ValueError):
    """The formula is unknown, or the parameters do not satisfy it."""


@dataclass(frozen=True)
class Formula:
    """One versioned calculation."""

    id: str
    version: str
    description: str
    params: Tuple[str, ...]
    unit: str
    expression: str
    aliases: Tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "version": self.version,
            "description": self.description,
            "params": list(self.params),
            "unit": self.unit,
            "expression": self.expression,
        }


FORMULAS: Tuple[Formula, ...] = (
    Formula(
        id="stay_charge_projection",
        version="1.0.0",
        description="Projected room charge: nightly rate times the nights booked",
        params=("nightly_rate", "nights"),
        unit="currency",
        expression="round(nightly_rate * nights, 2)",
        aliases=("stay_charge", "room_charge"),
    ),
    Formula(
        id="room_occupancy_percent",
        version="1.0.0",
        description="Occupancy: occupied rooms as a percentage of sellable rooms",
        params=("occupied_rooms", "sellable_rooms"),
        unit="percent",
        expression="round(100.0 * occupied_rooms / sellable_rooms, 2)",
        aliases=("occupancy", "occupancy_percent"),
    ),
    Formula(
        id="revenue_per_available_room",
        version="1.0.0",
        description="RevPAR: room revenue divided by sellable rooms",
        params=("room_revenue", "sellable_rooms"),
        unit="currency",
        expression="round(room_revenue / sellable_rooms, 2)",
        aliases=("revpar",),
    ),
    Formula(
        id="average_length_of_stay",
        version="1.0.0",
        description="Average nights per check-in: room nights divided by check-ins",
        params=("room_nights", "check_ins"),
        unit="night",
        expression="round(room_nights / check_ins, 2)",
        aliases=("alos",),
    ),
)

_BY_ID: Dict[str, Formula] = {}
for _formula in FORMULAS:
    _BY_ID[_formula.id] = _formula
    for _alias in _formula.aliases:
        _BY_ID.setdefault(_alias, _formula)


def registry() -> List[Dict[str, Any]]:
    """The catalogue, as data (this is what an answer cites)."""
    return [f.to_dict() for f in FORMULAS]


def lookup(formula_id: str) -> Formula:
    key = str(formula_id or "").strip().lower()
    if key not in _BY_ID:
        raise FormulaError(f"unknown formula: {formula_id!r}")
    return _BY_ID[key]


def _safe_eval(expression: str, values: Mapping[str, float]) -> float:
    """Evaluate an arithmetic expression with no names beyond the whitelist."""
    tree = ast.parse(expression, mode="eval")
    allowed = (
        ast.Expression, ast.BinOp, ast.UnaryOp, ast.Call, ast.Load, ast.Name,
        ast.Constant, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod,
        ast.USub, ast.UAdd,
    )
    for node in ast.walk(tree):
        if not isinstance(node, allowed):
            raise FormulaError(f"formula uses an unsupported construct: {type(node).__name__}")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in _ALLOWED_CALLS:
                raise FormulaError("formula calls a function outside the whitelist")
        if (
            isinstance(node, ast.Name)
            and node.id not in values
            and node.id not in _ALLOWED_NAMES
            and node.id not in _ALLOWED_CALLS
        ):
            raise FormulaError(f"formula needs a parameter that was not supplied: {node.id}")
    namespace = {
        **_ALLOWED_NAMES,
        **_ALLOWED_CALLS,
        **{k: float(v) for k, v in values.items()},
    }
    return float(eval(compile(tree, "<formula>", "eval"), {"__builtins__": {}}, namespace))


def compute(formula_id: str, values: Mapping[str, Any]) -> Dict[str, Any]:
    """Run one formula. Missing or unknown parameters are refused, not guessed."""
    formula = lookup(formula_id)
    missing = [name for name in formula.params if name not in (values or {})]
    if missing:
        raise FormulaError("missing formula parameter(s): " + ", ".join(missing))
    try:
        params = {name: float(values[name]) for name in formula.params}
    except (TypeError, ValueError) as exc:
        raise FormulaError(f"formula parameters must be numeric: {exc}") from exc
    return {
        "formula_id": formula.id,
        "version": formula.version,
        "unit": formula.unit,
        "result": _safe_eval(formula.expression, params),
        "inputs": params,
    }


def declaration() -> Dict[str, Any]:
    return {"registry": FORMULA_REGISTRY_VERSION, "formulas": registry()}
