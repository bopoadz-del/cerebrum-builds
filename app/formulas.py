"""Formula layer for LexManage calculations.

Written by the factory WRITER role (codewhale exec).

Billable amounts, invoices and court deadlines are calculated here — never by the
model. Two paths, in order:

1. the vendored ``formula_executor`` block, called with a keyword action and
   the formula's own input values (``app.formulas.execute_formula``);
2. a local AST evaluator over the same expression, used when the block refuses
   or is unavailable offline. It evaluates arithmetic only: no names, no
   attribute access, no calls — a formula string can never execute code.

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
    "billable_amount": {
        "description": "Billable amount: hours * hourly_rate",
        "expression": "hours * hourly_rate",
        "parameters": ("hours", "hourly_rate"),
        "unit": "currency",
    },
    "invoice_total": {
        "description": "Invoice gross total: subtotal * (1 + tax_rate)",
        "expression": "subtotal * (1 + tax_rate)",
        "parameters": ("subtotal", "tax_rate"),
        "unit": "currency",
    },
    "invoice_tax": {
        "description": "Tax amount: subtotal * tax_rate",
        "expression": "subtotal * tax_rate",
        "parameters": ("subtotal", "tax_rate"),
        "unit": "currency",
    },
    "trust_balance": {
        "description": "Retainer balance: retainer_amount - fees_billed",
        "expression": "retainer_amount - fees_billed",
        "parameters": ("retainer_amount", "fees_billed"),
        "unit": "currency",
    },
    "realization_rate": {
        "description": "Realization: collected_amount / billed_amount",
        "expression": "collected_amount / billed_amount",
        "parameters": ("collected_amount", "billed_amount"),
        "unit": "ratio",
    },
    "matter_aging_days": {
        "description": "Matter age in days: open_days_elapsed",
        "expression": "open_days_elapsed",
        "parameters": ("open_days_elapsed",),
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
