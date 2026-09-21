"""Capability write routes require a platform token.

POST /v1/<capability> without a bearer / X-Platform-Token is HTTP 401.
Missing required fields and invalid enums are HTTP 422. JSON ``ok: false``
with HTTP 200 is not an auth or validation pass.
"""

from __future__ import annotations

import os
from typing import Any, Dict

from fastapi import HTTPException, Request

PLATFORM_TOKEN_ENV = "PLATFORM_TOKEN"
DEFAULT_PLATFORM_TOKEN = "dev-local-token"


def platform_token() -> str:
    return (os.environ.get(PLATFORM_TOKEN_ENV) or DEFAULT_PLATFORM_TOKEN).strip()


def require_platform_token(request: Request) -> Any:
    """Resolve the caller's tenant from the presented bearer token.

    Delegates to app.tenancy.resolve_tenant — the single resolution path
    shared with rag_routes and kernel_bridge. A missing, unknown, or
    client-named tenant is refused with 401 by name
    (authentication_required), never silently mapped to a default.
    """
    import app.tenancy as tenancy

    try:
        tenant = tenancy.resolve_tenant(request.headers)
    except tenancy.TenantRefused:
        raise HTTPException(status_code=401, detail="authentication_required")
    # The request in flight is now this tenant. Handlers that read the corpus
    # (app.retrieval) take the tenant from here -- it is never a payload field.
    tenancy.set_current_tenant(tenant.tenant_id)
    return tenant


def require_read_tenant(request: Request) -> Any:
    """The tenant a READ resolves to.

    A write always requires the platform token (401 without one). A read does
    too -- except in a single-tenant deployment (no TENANT_TOKENS bound), where
    the only tenant is the platform's own and the operator console / probes
    read it without a request-level principal. A caller who *presents* a
    principal this deployment does not know is not folded into the platform's
    tenant: it resolves to its own empty namespace, so one property can never
    see another's rows (404, never 403 and never the record).
    """
    import app.tenancy as tenancy

    try:
        return tenancy.read_tenant(request.headers)
    except tenancy.TenantRefused:
        raise HTTPException(status_code=401, detail="authentication_required")


def reject_invalid_payload(capability_id: str, payload: Dict[str, Any] | None) -> None:
    from app.models import MODELS

    cls = MODELS.get(capability_id)
    if cls is None:
        raise HTTPException(status_code=422, detail="unknown capability")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="payload must be an object")
    fields = list(getattr(cls, "FIELDS", []) or [])
    constraints = getattr(cls, "CONSTRAINTS", {}) or {}
    required = [
        name
        for name in fields
        if (constraints.get(name) or {}).get("required")
        or name in getattr(cls, "REQUIRED", ())
    ]
    if not required:
        # Models stamp required on the field spec; fall back to every field
        # that has no default in CONSTRAINTS.required=False only.
        required = [
            name
            for name in fields
            if (constraints.get(name) or {}).get("required") is not False
            and name in constraints
            and constraints[name].get("required")
        ]
    for name in required:
        if name not in payload or payload[name] in (None, ""):
            raise HTTPException(
                status_code=422, detail="Missing required field: " + name
            )
    for name, rules in constraints.items():
        if name not in payload:
            continue
        allowed = rules.get("allowed_values")
        if allowed is not None and payload[name] not in allowed:
            raise HTTPException(
                status_code=422,
                detail=name + " must be one of: " + ", ".join(str(v) for v in allowed),
            )
    # Types are part of the contract too: a count sent as prose must not
    # reach a handler that will do arithmetic with it. The check stops at
    # what the handler can actually absorb: a numeric value is coerced to
    # the declared annotation and everything else is stored verbatim.
    # The compiled spec declares no type for several of these columns
    # (lead_intake daily_call_cap, qualification budget, outcome
    # ledger_index, local_drive bytes_written), so a payload built from the
    # capability's own schema may carry the generic string sample; refusing
    # it here was the "stricter contract than the spec can express" miss.
    # Bounds below still apply to any numeric value.
    annotations = getattr(cls, "__annotations__", {}) or {}
    for name in fields:
        if name not in payload or payload[name] in (None, ""):
            continue
        declared = str(annotations.get(name, "str")).replace("Optional[", "").replace("]", "").strip()
        value = payload[name]
        if declared == "int":
            if isinstance(value, bool):
                raise HTTPException(status_code=422, detail=name + " must be an integer")
            if isinstance(value, int):
                continue
            if isinstance(value, str) and value.strip().lstrip("-+").isdigit():
                payload[name] = int(value.strip())
                continue
        elif declared == "float":
            if isinstance(value, bool):
                raise HTTPException(status_code=422, detail=name + " must be a number")
            if isinstance(value, (int, float)):
                continue
            try:
                payload[name] = float(str(value))
                continue
            except (TypeError, ValueError):
                pass
        elif declared == "str" and not isinstance(value, str):
            raise HTTPException(status_code=422, detail=name + " must be a string")
    # Bounds are declared on the field, so they are enforced here: a charge of
    # -5 or a capacity of 400 is refused at the edge, not by a block later.
    for name, rules in constraints.items():
        if name not in payload or isinstance(payload[name], bool):
            continue
        try:
            numeric = float(payload[name])
        except (TypeError, ValueError):
            continue
        low, high = rules.get("min"), rules.get("max")
        if low is not None and numeric < float(low):
            raise HTTPException(status_code=422, detail=name + " is below the minimum")
        if high is not None and numeric > float(high):
            raise HTTPException(status_code=422, detail=name + " is above the maximum")