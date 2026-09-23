"""Outcome & dashboard: the numbers the operator asked for.

    GET /v1/dashboard?campaign=      attempted, answered, interest split,
                                     transfers, conversion — plus a chart
    GET /v1/metrics/campaigns        the same metric per campaign
    GET /v1/calls/{call_sid}         one call, reconstructed from its ledgers
    GET|POST /v1/ledger/verify       walk the hash chains; POST names one SID

Every figure is computed by ``app/formulas.py`` and carries the ``formulas``
authority label, so the console can show where the number came from.
"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request

from app import dispatch, domain, formulas
from app.config import SettingMissing
from app.dispatch import BlockRefused
from app.auth import int_query, json_object, optional_int, require_permission, resolve_principal
from app.tenancy import Tenant

router = APIRouter(tags=["dashboard"])


def _campaign_totals(tenant_id: str) -> List[Dict[str, Any]]:
    """The brief's per-campaign metric list, split by the three outcomes.

    attempted, answered, the interest split across the fixed three-outcome
    vocabulary, transfers and conversion -- per campaign. ``calls`` stays
    as an alias of ``attempted`` so a console that already renders it keeps
    working; ``interest`` always carries all three keys (zero included) so a
    campaign with no qualification of one kind is not silently absent, which
    is the shape an operator reads a month-on-month trend from.
    """
    campaigns: Dict[str, Dict[str, Any]] = {}
    for row in domain.campaign_rows(tenant_id):
        name = str(row.get("campaign") or "unassigned")
        entry = campaigns.setdefault(
            name,
            {
                "campaign": name,
                "calls": 0,
                "answered": 0,
                "qualified": 0,
                "transfers": 0,
                "outcomes": {},
                "interest": {outcome: 0 for outcome in domain.OUTCOME_VOCABULARY},
            },
        )
        entry["calls"] += 1
        entry["answered"] += 1 if row.get("answered") else 0
        if row.get("outcome"):
            outcome = str(row["outcome"])
            entry["qualified"] += 1
            entry["outcomes"][outcome] = entry["outcomes"].get(outcome, 0) + 1
            if outcome in entry["interest"]:
                entry["interest"][outcome] += 1
        if str(row.get("transfer_outcome") or "") == "transferred":
            entry["transfers"] += 1
    for entry in campaigns.values():
        calls = entry["calls"] or 1
        entry["attempted"] = entry["calls"]
        entry["answer_rate"] = round(entry["answered"] / calls, 4)
        entry["qualify_rate"] = round(entry["qualified"] / calls, 4)
        entry["conversion"] = round(entry["transfers"] / calls, 4)
    return sorted(campaigns.values(), key=lambda item: item["campaign"])


@router.get("/v1/dashboard")
def dashboard(request: Request, tenant: Tenant = Depends(resolve_principal)) -> Dict[str, Any]:
    require_permission(tenant, "read")
    campaign = request.query_params.get("campaign")
    report = domain.campaign_metrics(tenant.tenant_id, campaign)
    metrics = report["metrics"]
    chart = {
        "attempted": metrics["attempted"],
        "answered": metrics["answered"],
        "transfers": metrics["transfers"],
    }
    from app import dispatch

    rendered = dispatch.execute("chart_renderer", "bars", {"series": chart})
    return {
        "ok": True,
        "tenant": tenant.to_dict(),
        "campaign": campaign or None,
        "metrics": metrics,
        "interest": metrics["interest"],
        "conversion": metrics["conversion"],
        "chart": rendered.get("svg"),
        "campaigns": _campaign_totals(tenant.tenant_id),
        "calls": report["calls"],
        "authority": report["authority"],
    }


@router.get("/v1/metrics/campaigns")
def campaign_metrics(request: Request, tenant: Tenant = Depends(resolve_principal)) -> Dict[str, Any]:
    require_permission(tenant, "read")
    totals = _campaign_totals(tenant.tenant_id)
    return {
        "ok": True,
        "tenant": tenant.to_dict(),
        "campaigns": totals,
        "count": len(totals),
        "authority": {
            "precedence": "precedence.v1",
            "layer": "formulas",
            "label": "formulas:campaign_metrics",
        },
    }


@router.get("/v1/calls/{call_sid}")
def call_detail(call_sid: str, request: Request, tenant: Tenant = Depends(resolve_principal)) -> Dict[str, Any]:
    require_permission(tenant, "read")
    history = domain.call_history(tenant.tenant_id, call_sid)
    if not history["events"]:
        raise HTTPException(status_code=404, detail="no events for that call sid")
    from app import store

    qualifications = [
        row
        for row in store.list_all("qualification_and_broker_summary", tenant.tenant_id)
        if str(row.get("call_sid") or "") == call_sid
    ]
    transfers = [
        row
        for row in store.list_all("warm_transfer", tenant.tenant_id)
        if str(row.get("call_sid") or "") == call_sid
    ]
    return {
        "ok": True,
        "tenant": tenant.to_dict(),
        "call_sid": call_sid,
        "history": history,
        "qualification": qualifications,
        "transfers": transfers,
        "authority": {
            "precedence": "precedence.v1",
            "layer": "procedures",
            "label": "procedures:domain.call_history",
        },
    }


@router.get("/v1/ledger/verify")
def verify_ledger(request: Request, tenant: Tenant = Depends(resolve_principal)) -> Dict[str, Any]:
    """Verify this tenant's ledger chains — read-only, whole-tenant by default.

    The audit ledger is the platform's memory of every call event, so the
    cheap question an operator asks is "does it still verify?" — not
    "verify this one SID". With no ``call_sid`` the whole tenant ledger is
    walked, one chain per call, and the answer names every chain that does
    not link. An empty ledger verifies (zero entries, zero violations):
    nothing to reconstruct is not a failing check.
    """
    require_permission(tenant, "read")
    call_sid = str(request.query_params.get("call_sid") or "")
    from app import store

    entries = store.list_all("outcome_capture_and_ledger", tenant.tenant_id)
    if call_sid:
        entries = [row for row in entries if str(row.get("call_sid") or "") == call_sid]
    chains: Dict[str, List[Dict[str, Any]]] = {}
    for row in entries:
        chains.setdefault(str(row.get("call_sid") or ""), []).append(row)
    report: List[Dict[str, Any]] = []
    violations: List[Dict[str, Any]] = []
    for sid in sorted(chains):
        verified = domain.verify_chain(chains[sid])
        report.append(
            {
                "call_sid": sid,
                "entries": verified.get("entries", len(chains[sid])),
                "verified": verified.get("verified", not verified.get("violations")),
            }
        )
        for problem in verified.get("violations") or []:
            violations.append({"call_sid": sid, **problem})
    return {
        "ok": True,
        "tenant": tenant.to_dict(),
        "call_sid": call_sid or None,
        "entries": sum(item["entries"] for item in report),
        "chains": report,
        "chain_count": len(report),
        "violations": violations,
        "verified": not violations,
        "authority": {
            "precedence": "precedence.v1",
            "layer": "procedures",
            "label": "procedures:domain.ledger_verify",
        },
    }


@router.post("/v1/ledger/verify")
async def verify(request: Request, tenant: Tenant = Depends(resolve_principal)) -> Dict[str, Any]:
    require_permission(tenant, "read")
    body = await json_object(request)
    call_sid = str((body or {}).get("call_sid") or "")
    if not call_sid:
        raise HTTPException(status_code=422, detail="Missing required field: call_sid")
    from app import store

    entries = [
        row
        for row in store.list_all("outcome_capture_and_ledger", tenant.tenant_id)
        if str(row.get("call_sid") or "") == call_sid
    ]
    if not entries:
        raise HTTPException(status_code=404, detail="no ledger entries for that call sid")
    report = domain.verify_chain(entries)
    return {"ok": True, "call_sid": call_sid, **report}


@router.get("/v1/formulas")
def formula_catalog(request: Request, tenant: Tenant = Depends(resolve_principal)) -> Dict[str, Any]:
    require_permission(tenant, "read")
    return {
        "ok": True,
        "tenant": tenant.to_dict(),
        "formulas": list(formulas.CATALOG),
        "count": len(formulas.CATALOG),
        "authority": {
            "precedence": "precedence.v1",
            "layer": "formulas",
            "label": "formulas:catalog",
        },
    }


@router.post("/v1/formulas/{name}")
async def run_formula(name: str, request: Request, tenant: Tenant = Depends(resolve_principal)) -> Dict[str, Any]:
    """Run one formula with the operator's inputs. Never guesses a currency."""
    require_permission(tenant, "read")
    body = await json_object(request)
    try:
        result = dispatch.execute(
            "formula_executor", "run", {"formula": name, "inputs": dict(body or {})}
        )
    except BlockRefused as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SettingMissing as exc:
        # A money formula the operator has not configured refuses by name.
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except TypeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True, "tenant": tenant.to_dict(), **result}
