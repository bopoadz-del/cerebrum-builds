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


# --------------------------------------------------------------------------
# Construction commercial formulas (AED, UAE).
#
# A valuation is measured work priced at a BOQ rate, less retention, plus VAT
# on the net, less what was already certified. Every rate comes from the record
# or from a named deployment setting (app/money.py) -- never from a literal.
# --------------------------------------------------------------------------

def line_value(measured_quantity: Any, unit_rate: Any) -> float:
    """Value of a BOQ line: measured quantity x unit rate, to the fils."""
    return round(_number(measured_quantity) * _number(unit_rate), 2)


def retention_amount(gross_value: Any, retention_percent: Any) -> float:
    """Retention withheld from a gross valuation."""
    return round(_number(gross_value) * _number(retention_percent) / 100.0, 2)


def vat_amount(net_value: Any, vat_rate_percent: Any) -> float:
    """VAT on the net (post-retention) value at the given rate."""
    return round(_number(net_value) * _number(vat_rate_percent) / 100.0, 2)


def certified_value(gross_value: Any, retention_aed: Any, vat_aed: Any) -> float:
    """Net certified value: gross, less retention, plus VAT."""
    return round(
        _number(gross_value) - _number(retention_aed) + _number(vat_aed), 2
    )


def payment_due(certified_value_aed: Any, previously_certified_aed: Any = 0.0) -> float:
    """Amount payable this cycle, floored at zero."""
    return round(
        max(_number(certified_value_aed) - _number(previously_certified_aed), 0.0), 2
    )


def valuation_summary(record: Dict[str, Any]) -> Dict[str, Any]:
    """Price one interim payment application from its own record.

    Rates travel with the record when it carries them; otherwise they come
    from the named settings in app/money.py, which refuse rather than default.
    The answer names where every rate came from, so a valuation can be
    audited back to its source.
    """
    from app import money

    data = dict(record or {})
    gross = data.get("gross_value_aed")
    quantity, rate = data.get("measured_quantity"), data.get("unit_rate_aed")
    if gross in (None, "") and quantity not in (None, "") and rate not in (None, ""):
        gross = line_value(quantity, rate)
    gross = _number(gross)

    retention_rate = money.rate_from(
        data, "retention_percent", setting_name="DEFAULT_RETENTION_PERCENT"
    )
    retention = data.get("retention_aed")
    if retention in (None, ""):
        retention = retention_amount(gross, retention_rate)
    retention_rate_source = (
        "record" if data.get("retention_percent") not in (None, "") else "setting"
    )

    vat_rate = money.rate_from(data, "vat_rate_percent", setting_name="UAE_VAT_RATE_PERCENT")
    net = round(gross - _number(retention), 2)
    vat = data.get("vat_amount_aed")
    if vat in (None, ""):
        vat = vat_amount(net, vat_rate)
    vat_rate_source = "record" if data.get("vat_rate_percent") not in (None, "") else "setting"

    certified = data.get("certified_value_aed")
    if certified in (None, ""):
        certified = certified_value(gross, retention, vat)
    due = data.get("amount_due_aed")
    due = payment_due(certified) if due in (None, "") else _number(due)

    return {
        "currency": money.CURRENCY,
        "country": money.COUNTRY,
        "gross_value_aed": round(gross, 2),
        "retention_percent": retention_rate,
        "retention_percent_source": retention_rate_source,
        "retention_aed": round(_number(retention), 2),
        "net_value_aed": net,
        "vat_rate_percent": vat_rate,
        "vat_rate_source": vat_rate_source,
        "vat_amount_aed": round(_number(vat), 2),
        "certified_value_aed": round(_number(certified), 2),
        "amount_due_aed": due,
        "formula": "certified = gross - retention + VAT",
    }
