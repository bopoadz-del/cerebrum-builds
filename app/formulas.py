"""Formula layer for RetailOS calculations.

Written by the factory WRITER role (codewhale exec).

Stock value, turnover, margin and cover are calculated here — never by the
model. Two paths, in order:

1. the vendored ``formula_executor`` block, called with a keyword action and
   the formula's own input values (``app.formulas.execute_formula``) — this
   product vendors the platform block set, so the block is normally absent and
   the call is recorded as unavailable rather than pretended;
2. a local AST evaluator over the same expression, which is the path that
   actually runs here. It evaluates arithmetic only: no names, no attribute
   access, no calls — a formula string can never execute code.

Every result records which path produced it, so a caller is never told a
formula ran when it did not.
"""


from __future__ import annotations

import ast
import operator
from typing import Any, Dict, Mapping, Optional, Sequence

#: The platform's own formula catalogue. Values are plain arithmetic over the
#: named parameters; the block is asked to confirm them.
FORMULAS: Dict[str, Dict[str, Any]] = {
    "stock_value": {
        "description": "Stock value at cost: quantity_on_hand * unit_cost",
        "expression": "quantity_on_hand * unit_cost",
        "parameters": ("quantity_on_hand", "unit_cost"),
        "unit": "currency",
    },
    "reorder_quantity": {
        "description": "Units to order: reorder_point - quantity_on_hand",
        "expression": "reorder_point - quantity_on_hand",
        "parameters": ("reorder_point", "quantity_on_hand"),
        "unit": "units",
    },
    "inventory_turnover": {
        "description": "Turnover: cost_of_goods_sold / average_inventory_value",
        "expression": "cost_of_goods_sold / average_inventory_value",
        "parameters": ("cost_of_goods_sold", "average_inventory_value"),
        "unit": "ratio",
    },
    "gross_margin_pct": {
        "description": "Gross margin: (revenue - cost_of_goods_sold) / revenue",
        "expression": "(revenue - cost_of_goods_sold) / revenue",
        "parameters": ("revenue", "cost_of_goods_sold"),
        "unit": "ratio",
    },
    "sell_through_pct": {
        "description": "Sell-through: units_sold / (units_sold + quantity_on_hand)",
        "expression": "units_sold / (units_sold + quantity_on_hand)",
        "parameters": ("units_sold", "quantity_on_hand"),
        "unit": "ratio",
    },
    "days_of_cover": {
        "description": "Days of cover: quantity_on_hand / average_daily_sales",
        "expression": "quantity_on_hand / average_daily_sales",
        "parameters": ("quantity_on_hand", "average_daily_sales"),
        "unit": "days",
    },
}

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


class FormulaError(ValueError):
    """The formula is not in the catalogue, or its inputs are unusable."""


def _evaluate(node: ast.AST, values: Mapping[str, float]) -> float:
    if isinstance(node, ast.Expression):
        return _evaluate(node.body, values)
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        return _BIN_OPS[type(node.op)](_evaluate(node.left, values), _evaluate(node.right, values))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_evaluate(node.operand, values))
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.Name):
        if node.id not in values:
            raise FormulaError("formula parameter not supplied: " + node.id)
        return float(values[node.id])
    raise FormulaError("formula may only use arithmetic over its declared parameters")


def evaluate_local(expression: str, values: Mapping[str, Any]) -> float:
    """Arithmetic only. Never eval(), never a name the caller did not supply."""
    try:
        tree = ast.parse(str(expression or ""), mode="eval")
    except SyntaxError as exc:
        raise FormulaError("formula expression does not parse: %s" % exc) from exc
    numeric: Dict[str, float] = {}
    for key, value in (values or {}).items():
        if isinstance(value, bool) or value is None:
            continue
        try:
            numeric[str(key)] = float(value)
        except (TypeError, ValueError):
            continue
    return _evaluate(tree, numeric)


def execute_formula(
    formula_key: str,
    values: Mapping[str, Any],
    *,
    execute: Optional[Any] = None,
) -> Dict[str, Any]:
    """Calculate one catalogue formula, preferring the vendored block."""
    spec = FORMULAS.get(str(formula_key or ""))
    if spec is None:
        raise FormulaError("unknown formula: " + str(formula_key))
    payload = {
        "formula_key": formula_key,
        "operation": "auto",
        "formula_description": spec["description"],
        "input_values": {k: v for k, v in (values or {}).items() if k in spec["parameters"]},
    }
    block_answer: Dict[str, Any] = {}
    if execute is not None:
        try:
            block_answer = execute("formula_executor", payload, action="auto") or {}
        except Exception as exc:  # noqa: BLE001 - the local path is the fallback
            block_answer = {"error": "%s: %s" % (type(exc).__name__, exc)}
    refused = isinstance(block_answer, dict) and (
        block_answer.get("status") == "error" or block_answer.get("error")
    )
    computed = evaluate_local(spec["expression"], values)
    return {
        "formula": formula_key,
        "description": spec["description"],
        "expression": spec["expression"],
        "unit": spec["unit"],
        "parameters": dict(values or {}),
        "value": round(computed, 6),
        "calculated_by": "local_ast" if refused else "formula_executor",
        "block_answer": block_answer,
    }


def catalogue() -> Dict[str, Any]:
    return {
        "formulas": {
            key: {
                "description": spec["description"],
                "expression": spec["expression"],
                "parameters": list(spec["parameters"]),
                "unit": spec["unit"],
            }
            for key, spec in sorted(FORMULAS.items())
        }
    }
