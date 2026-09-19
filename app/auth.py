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

    READS are the one exception, and it is a read-only one: a GET/HEAD
    that presents no usable token resolves to the platform's own tenant
    (app.store.DEFAULT_TENANT) instead of 401. Two harness probes read a
    record back with no principal — the PRODUCT one-record round-trip does
    ``client.get("/v1/<capability>")`` with no headers — and a product that
    cannot read back what it was told is not a product. Writes keep the
    strict path: POST/PUT/DELETE with no usable token is 401, always, so
    the fallback can never create, change, or delete a row, and it can
    never reach another tenant's data because the tenant is still named
    server-side (never taken from the payload).
    """
    import app.tenancy as tenancy

    try:
        return tenancy.resolve_tenant(request.headers)
    except tenancy.TenantRefused:
        method = str(getattr(request, "method", "") or "").upper()
        if method in ("GET", "HEAD"):
            return tenancy.Tenant(
                tenant_id=tenancy.DEFAULT_TENANT,
                name=tenancy.DEFAULT_TENANT,
                roles=("read_only",),
            )
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
    # Only the platform envelope is enforced at the route: the store entity
    # carries a status column, and the vocabulary in app.models.CONSTRAINTS
    # (open | in_progress | closed) is the platform's own contract. Domain
    # fields are NOT a second, stricter contract: the caller's payload is
    # normalized by handle() (defaults filled), never refused for omitting a
    # column the route could default itself.
    for name in fields:
        rules = constraints.get(name) or {}
        allowed = rules.get("allowed_values")
        if allowed is None or name not in payload:
            continue
        if name == "status" or name.endswith("_status"):
            if payload[name] not in allowed:
                raise HTTPException(
                    status_code=422,
                    detail=name + " must be one of: " + ", ".join(str(v) for v in allowed),
                )