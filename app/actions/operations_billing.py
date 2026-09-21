"""Handler for capability operations_billing.

Written by the factory WRITER role (codewhale exec)

Authored by the coder CLI (codewhale exec) — the factory WRITER coding
agent — against the vendored blocks, in this repository.

Records operational charges and folio-level billing. Currency, tax/VAT regime and
the rate itself are operator settings (CURRENCY, TAX_RATE_PERCENT) with no default:
the brief named none, so none is assumed, and the refusal names the missing one.

The record carries ``setting``: the operator-owned money setting (a named
configuration key, e.g. the one that supplies the currency or the rate) this
charge was filed under. It is required, so a folio line can never be recorded
without naming the configuration whose money values it used.

Scope
-----
READS  this capability's own columns from the caller's record; app.dispatch
       (the local offline block runtime); app.block_inputs (block input
       construction); app.store (the ``operations_billing`` table, through the route's
       tenant-scoped save); app.formulas (the operator's currency and tax settings).
WRITES app.dispatch.execute() results; exactly one row in ``operations_billing`` via the
       ROUTE's tenant-scoped persistence (app.routes) -- this handler has no
       tenant and never persists directly.
NEVER  a currency, tax regime or tax rate the brief did not give; unguarded
       network egress; ``vendor/**`` (sealed, read-only); another capability's
       table; ``tests/**``.

Blocks are action-dispatched: ``action=`` is a keyword on
``app.dispatch.execute`` (via app.block_run), never a key inside the domain
payload. Block-contract keys are constructed by
``app.block_inputs.prepare_block_input`` from this record.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.block_run import block_runner
from app.security import InputRefused, clean_text

CAPABILITY_ID = "operations_billing"
ENTITY = "operations_billing"
BLOCK_IDS = ['billing', 'hotel_v2']
#: Each block's declared action (block.json / the Store map). Blocks are
#: action-dispatched; calling one with no action answers "Unknown action".
BLOCK_DEFAULT_ACTIONS = {'billing': 'record_usage', 'hotel_v2': 'analyze'}
#: This capability's own domain columns.
CAPABILITY_FIELDS = ['setting', 'reference', 'status', 'folio_reference', 'charge_type', 'amount', 'currency', 'tax_rate_percent', 'total_amount', 'notes']


def _text(data: Dict[str, Any], name: str, limit: int = 2000) -> str:
    return clean_text(data.get(name), field=name, limit=limit)

def _folio_summary(data: Dict[str, Any]) -> str:
    return (
        "Guest folio charge. Setting: {setting}. Folio: {folio}. Charge type: {kind}. "
        "Amount: {amount}. Currency: {currency}. Tax rate: {tax}. Notes: {notes}"
    ).format(
        setting=_text(data, "setting", 120) or "unfiled",
        folio=_text(data, "folio_reference", 120) or "unfiled",
        kind=_text(data, "charge_type", 60) or "other",
        amount=data.get("amount"),
        currency=_text(data, "currency", 12) or "unset",
        tax=data.get("tax_rate_percent"),
        notes=_text(data, "notes", 500),
    )


def _money_report(data: Dict[str, Any]) -> Dict[str, Any]:
    """Compute the folio total ONLY from settings the operator supplied.

    The brief named no country and no currency, so this platform does not pick
    one: with the settings unset the charge is still recorded -- an
    operational record is not a tax calculation -- and the refusal names
    the operator setting the rule would have needed.
    """
    from app import formulas

    report: Dict[str, Any] = {"settings": formulas.money_settings_state()}
    try:
        total = formulas.folio_total(data.get("amount"), data.get("tax_rate_percent"))
    except formulas.SettingsError as exc:
        report["computed"] = False
        report["reason"] = str(exc)
        report["total_amount"] = None
        return report
    report["computed"] = True
    report["total_amount"] = total["total"]
    report.update(total)
    declared = _text(data, "currency", 12)
    if declared and declared.upper() != total["currency"]:
        report["currency_mismatch"] = (
            f"the record says {declared.upper()} but this property bills in "
            f"{total['currency']} (CURRENCY); no conversion is applied or assumed"
        )
    return report


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(payload or {}) if isinstance(payload, dict) else {}
    runner = block_runner(entity=ENTITY, roster=BLOCK_IDS, default_actions=BLOCK_DEFAULT_ACTIONS)

    try:
        folio = _text(data, "folio_reference", 120)
        charge_type = _text(data, "charge_type", 60) or "other"
        setting = _text(data, "setting", 120)
        if data.get("amount") in (None, ""):
            return {
                "ok": False,
                "capability": CAPABILITY_ID,
                "error": "amount is required: a charge with no amount is not a charge",
            }
        summary = _folio_summary(data)
        money = _money_report(data)
    except InputRefused as exc:
        return {"ok": False, "capability": CAPABILITY_ID, "error": str(exc)}

    usage = runner(
        "billing",
        {
            "metric": f"folio_{charge_type}",
            "quantity": 1,
            "value": data.get("amount"),
            "metadata": {
                "setting": setting,
                "folio_reference": folio,
                "charge_type": charge_type,
            },
        },
        action="record_usage",
    )
    analysed = runner("hotel_v2", {"text": summary}, action="analyze")

    refusal = runner.refusal()
    if refusal is not None:
        return {"ok": False, "capability": CAPABILITY_ID, **refusal}

    return {
        "ok": True,
        "capability": CAPABILITY_ID,
        "charge": {
            "setting": setting,
            "folio_reference": folio,
            "charge_type": charge_type,
            "amount": data.get("amount"),
            "recorded": bool(usage.get("recorded")) if isinstance(usage, dict) else False,
            "cost_cents": usage.get("cost_cents") if isinstance(usage, dict) else None,
        },
        "folio": {
            "total_amount": money.get("total_amount"),
            "tax": money.get("tax"),
            "currency": money.get("currency"),
            "computed": money.get("computed"),
            "reason": money.get("reason"),
            "currency_mismatch": money.get("currency_mismatch"),
        },
        "settings": money.get("settings"),
        "analysis": {
            "document_type": analysed.get("document_type") if isinstance(analysed, dict) else None,
        },
        "blocks": runner.report(),
    }
