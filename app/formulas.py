"""Safe arithmetic for billing totals, dosage references and due dates.

The platform never ``eval()``s caller text. Expressions are parsed with
:mod:`ast` and only a whitelisted node set is evaluated (numbers, the four
operators, parentheses, and a named-variable mapping). Anything else is
refused by name, so a refused formula is a stated error rather than a silent
zero on an invoice.
"""

from __future__ import annotations

import ast
import operator
from datetime import date, timedelta
from typing import Any, Dict, Mapping

_BINARY = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}


class FormulaError(ValueError):
    """The expression is not in the safe formula grammar."""


def evaluate(expression: str, variables: Mapping[str, Any] | None = None) -> float:
    """Evaluate an arithmetic expression against ``variables``."""
    text = str(expression or "").strip()
    if not text:
        raise FormulaError("expression required")
    try:
        tree = ast.parse(text, mode="eval")
    except SyntaxError as exc:
        raise FormulaError(f"expression is not parseable: {exc.msg}") from exc
    scope: Dict[str, Any] = dict(variables or {})
    return float(_eval(tree.body, scope))


def _eval(node: ast.AST, scope: Mapping[str, Any]) -> float:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise FormulaError(f"literal {node.value!r} is not a number")
        return float(node.value)
    if isinstance(node, ast.Name):
        if node.id not in scope:
            raise FormulaError(f"unknown variable: {node.id}")
        value = scope[node.id]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise FormulaError(f"variable {node.id} is not a number")
        return float(value)
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
        left = _eval(node.left, scope)
        right = _eval(node.right, scope)
        if isinstance(node.op, (ast.Div, ast.Mod)) and right == 0:
            raise FormulaError("division by zero")
        return float(_BINARY[type(node.op)](left, right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return float(_UNARY[type(node.op)](_eval(node.operand, scope)))
    raise FormulaError(f"unsupported formula node: {type(node).__name__}")


def invoice_balance(invoice_total: Any, amount_paid: Any) -> float:
    """Outstanding balance, floored at zero."""
    total = _number(invoice_total)
    paid = _number(amount_paid)
    return round(max(total - paid, 0.0), 2)


def dose_per_10kg(dosage_mg: Any) -> float:
    """Reference dose for a 10kg animal, rounded to 4 decimals."""
    return round(_number(dosage_mg) / 10.0, 4)


def next_due(administered_on: str, interval_days: int = 365) -> str:
    """ISO date one vaccination interval after ``administered_on``."""
    try:
        base = date.fromisoformat(str(administered_on)[:10])
    except ValueError as exc:
        raise FormulaError(f"administered_on is not an ISO date: {administered_on!r}") from exc
    return (base + timedelta(days=int(interval_days))).isoformat()


def _number(value: Any) -> float:
    if isinstance(value, bool) or value in (None, ""):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise FormulaError(f"{value!r} is not a number") from exc
