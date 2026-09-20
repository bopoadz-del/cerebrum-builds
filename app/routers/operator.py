"""Operator surfaces: retrieval, money settings, valuation formulas, authority.

Every route authenticates with the platform token and resolves the tenant from
the authenticated principal (never from the payload). None makes an outbound
call: retrieval reads the contractor's own sqlite rows, valuations are priced
by app/formulas.py, and authority resolution is pure ranking over the claims
the caller supplies. Each answer carries its precedence.v1 layer label so an
operator can see whether a number came from a signed record, an uploaded
document, a platform formula or a standing procedure.
"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Request

from app import retrieval
from app.authority import AuthorityError, resolve
from app.security import authenticate, assert_no_tenant_keys

router = APIRouter()


@router.get("/retrieval")
def retrieval_query(request: Request, q: str = "", limit: int = 10) -> Dict[str, Any]:
    """Rank the tenant's own records against ``q``."""
    tenant = authenticate(request)
    try:
        return retrieval.query(q, token="", entities=None, limit=limit)
    except retrieval.RetrievalError as exc:
        return {"ok": False, "error": str(exc)}
    except retrieval.TenantRefused as exc:  # pragma: no cover - defensive
        return {"ok": False, "tenant_id": tenant.tenant_id, "error": str(exc)}


@router.post("/authority/resolve")
def authority_resolve(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """Resolve ranked claims for one subject under precedence.v1."""
    authenticate(request)
    assert_no_tenant_keys(payload)
    subject = str((payload or {}).get("subject") or "").strip()
    claims: List[Dict[str, Any]] = list((payload or {}).get("claims") or [])
    if not subject:
        return {"ok": False, "error": "subject required"}
    if not claims:
        return {"ok": False, "error": "claims required"}
    try:
        resolution = resolve(subject, claims)
    except (AuthorityError, TypeError, ValueError) as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    return {"ok": True, "resolution": resolution.to_dict()}


@router.get("/settings/money")
def money_settings(request: Request) -> Dict[str, Any]:
    """Country, currency and every rate this deployment has been given.

    The brief fixes the country (UAE) and the currency (AED). It does not fix
    a VAT rate, so the platform reports which money settings are set and which
    are still missing rather than assuming a rate.
    """
    authenticate(request)
    from app import money

    return {"ok": True, "settings": money.configured()}


@router.post("/formulas/valuation")
def valuation_formula(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """Price an interim payment application / valuation from its own record.

    Rates travel with the record when it carries them; otherwise they come
    from the named settings in app/money.py, which refuse rather than default.
    The answer is labelled as the ``formulas`` layer of precedence.v1.
    """
    authenticate(request)
    assert_no_tenant_keys(payload)
    from app import formulas, money

    record = dict(payload or {})
    try:
        priced = formulas.valuation_summary(record)
    except money.SettingMissing as exc:
        return {"ok": False, "error": str(exc), "setting": exc.name}
    except formulas.FormulaError as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    subject = str(
        record.get("valuation_number") or record.get("reference") or "valuation"
    )
    claim = {
        "subject": subject,
        "layer": "formulas",
        "value": priced["certified_value_aed"],
        "source_ref": "app/formulas.py:valuation_summary",
    }
    try:
        resolution = resolve(subject, [claim])
    except (AuthorityError, TypeError, ValueError) as exc:  # pragma: no cover
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    priced["authority"] = resolution.to_dict()
    priced["authority_label"] = resolution.winner.get("label") if resolution.winner else "platform formula"
    return {"ok": True, "valuation": priced}


@router.post("/formulas/evaluate")
def formula_evaluate(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """Evaluate one arithmetic expression in the safe formula grammar."""
    authenticate(request)
    assert_no_tenant_keys(payload)
    from app import formulas

    expression = str((payload or {}).get("expression") or "").strip()
    variables = (payload or {}).get("variables") or {}
    if not expression:
        return {"ok": False, "error": "expression required"}
    if not isinstance(variables, dict):
        return {"ok": False, "error": "variables must be an object"}
    try:
        value = formulas.evaluate(expression, variables)
    except formulas.FormulaError as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    return {
        "ok": True,
        "expression": expression,
        "value": value,
        "authority_label": "platform formula (precedence.v1 layer 3)",
    }
