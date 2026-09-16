"""Extra HTTP surfaces over the capability actions.

Written by the factory WRITER role (codewhale exec).

``app/routes.py`` is the kernel-dispatched surface: POST /v1/{capability}
through ``execute_action`` plus list/get/update/delete per capability. This
router adds what a front desk actually uses and the kernel template does not
carry — and it adds them without colliding with the kernel's paths:

    GET    /v1/schema/{capability_id}             the capability's own contract
                                                  (columns, constraints, binds)
    POST   /v1/{capability_id}/{item_id}/document render a stored record
                                                  through the document bind
    GET    /v1/roles                              the RBAC matrix
    GET    /v1/formulas                           the formula catalogue
    GET    /v1/authority                          precedence.v1 layers
    GET    /v1/llm                                LLM posture + sealed-vendor
                                                  substitutions
    GET    /v1/offline                            offline posture detail
    GET    /v1/jobs/coverage                      role jobs and gate coverage

Every route resolves the tenant from the authenticated principal
(app/tenancy.py), checks the role's permission (app.security) and refuses a
payload that names its own tenant. Handlers are reached through
``app.kernel_bridge.run_capability`` — the same seam the kernel routes use —
so a failing block stays fail-closed.
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request

from app import authority, formulas, jobs, llm, security, store, tenancy
from app.kernel_bridge import run_capability

router = APIRouter()


def _principal(request: Request) -> tenancy.Tenant:
    try:
        return tenancy.resolve_tenant(request.headers)
    except tenancy.TenantRefused:
        raise HTTPException(status_code=401, detail="authentication_required")


def _require(tenant: tenancy.Tenant, permission: str) -> None:
    try:
        security.require_permission(tenant.roles, permission)
    except security.AccessDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc))


def _entity(capability_id: str) -> str:
    from app.models import MODELS

    name = str(capability_id or "").replace("-", "_")
    if name not in MODELS:
        raise HTTPException(status_code=404, detail="unknown capability: " + name)
    return name


def _clean_payload(payload: Any) -> Dict[str, Any]:
    data = payload if isinstance(payload, dict) else {}
    try:
        tenancy.refuse_client_tenant(data)
    except tenancy.TenantRefused as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return data


@router.get("/v1/schema/{capability_id}")
def capability_schema(capability_id: str, request: Request) -> Dict[str, Any]:
    """The capability's own contract: columns, constraints, binds, defaults.

    A handler that persists also runs its blocks, so a "dry run" write route
    would either persist anyway or lie. This surface reports the contract
    instead, and the front desk reads it before composing a payload.
    """
    import importlib

    name = _entity(capability_id)
    tenant = _principal(request)
    _require(tenant, security.capability_permission(name, security.READ) or "compliance_audit:read")
    from app.models import MODELS

    cls = MODELS[name]
    module = importlib.import_module("app.actions." + name)
    return {
        "ok": True,
        "capability": name,
        "entity": name,
        "tenant": tenant.to_dict(),
        "fields": list(getattr(cls, "FIELDS", [])),
        "constraints": dict(getattr(cls, "CONSTRAINTS", {}) or {}),
        "blocks": list(getattr(module, "BLOCK_IDS", [])),
        "default_actions": dict(getattr(module, "BLOCK_DEFAULT_ACTIONS", {})),
        "required_fields": list(getattr(module, "REQUIRED_FIELDS", [])),
        "write_permission": security.capability_permission(name, security.WRITE),
    }


@router.post("/v1/{capability_id}/{item_id}/document")
def capability_document(
    capability_id: str, item_id: int, request: Request
) -> Dict[str, Any]:
    """Render one stored record through the document_engine bind."""
    name = _entity(capability_id)
    tenant = _principal(request)
    _require(tenant, security.capability_permission(name, security.READ) or "compliance_audit:read")
    record = store.get(name, int(item_id))
    if record is None:
        raise HTTPException(status_code=404, detail="record not found")
    from app.block_inputs import default_block_action, prepare_block_input
    from app.dispatch import execute
    from app.offline_blocks import install_offline_block_adapters

    install_offline_block_adapters()
    defaults = {"document_engine": "parse"}
    body = "; ".join(
        "%s=%s" % (key, value) for key, value in sorted(record.items()) if key != "id"
    )
    prepared = prepare_block_input(
        "document_engine",
        {"content": "%s record %s: %s" % (name, item_id, body), "output_format": "text"},
        action=default_block_action("document_engine", defaults),
        roster=[name],
        entity=name,
        default_actions=defaults,
    )
    answer = execute("document_engine", prepared, action=defaults["document_engine"])
    ok = not (isinstance(answer, dict) and (answer.get("status") == "error" or answer.get("error")))
    return {
        "ok": ok,
        "capability": name,
        "item_id": int(item_id),
        "tenant": tenant.to_dict(),
        "document": answer,
        "error": None if ok else str(answer.get("error"))[:200],
    }


@router.get("/v1/roles")
def list_roles(request: Request) -> Dict[str, Any]:
    tenant = _principal(request)
    _require(tenant, "compliance_audit:read")
    return {
        "ok": True,
        "tenant": tenant.to_dict(),
        "roles": security.describe_roles(),
        "capability_permissions": dict(security.CAPABILITY_PERMISSION),
    }


@router.get("/v1/formulas")
def list_formulas(request: Request) -> Dict[str, Any]:
    _principal(request)
    return {"ok": True, **formulas.catalogue()}


@router.get("/v1/authority")
def authority_ladder(request: Request) -> Dict[str, Any]:
    _principal(request)
    return {
        "ok": True,
        "version": authority.PRECEDENCE_VERSION,
        "layers": authority.load_ladder(),
        "winner": authority.leader(),
    }


@router.get("/v1/llm")
def llm_posture(request: Request) -> Dict[str, Any]:
    _principal(request)
    from app.offline_blocks import offline_block_notes

    return {"ok": True, "llm": llm.status(), "sealed_vendor": offline_block_notes()}


@router.get("/v1/offline")
def offline_posture(request: Request) -> Dict[str, Any]:
    _principal(request)
    from app.offline_blocks import offline_block_notes
    from app import retrieval

    return {
        "ok": True,
        "network": "none (posture P1)",
        "sealed_vendor": offline_block_notes(),
        "corpus": retrieval.index_for("local").stats(),
    }


@router.get("/v1/jobs/coverage")
def jobs_coverage(request: Request) -> Dict[str, Any]:
    _principal(request)
    return {"ok": True, "jobs": jobs.JOBS, "gates": jobs.GATES}
