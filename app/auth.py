"""Capability write routes require a platform token.

POST /v1/<capability> without a bearer / X-Platform-Token is HTTP 401.
Missing required fields and invalid enums are HTTP 422. JSON ``ok: false``
with HTTP 200 is not an auth or validation pass.

READS take one of two explicit paths, both in this module:

* ``require_platform_token`` — the caller must present a credential; an
  unknown, unbound, or absent one is refused by name. WRITE routes use it.
* ``read_tenant`` — a credential that is presented must still resolve
  (an unknown token is 401, never silently anonymous); a request that
  presents none reads the platform's own front-desk tenant. The arrival
  board is polled by the duty-manager wall display, which holds no
  per-user token, and the rows still come from the tenant store rather
  than from a client-supplied name — a caller may never name its own
  tenant, and an X-Tenant that disagrees is refused.
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
        return tenancy.resolve_tenant(request.headers)
    except tenancy.TenantRefused:
        raise HTTPException(status_code=401, detail="authentication_required")


def read_tenant(request: Request) -> Any:
    """Resolve the tenant for a capability READ.

    A presented credential must resolve: an unknown or unbound token is
    HTTP 401, exactly as on a write — a bad credential never degrades into
    an anonymous read. A request that presents no credential reads the
    platform's own front-desk tenant (``tenancy.DEFAULT_TENANT``), because
    the arrival board is a shared front-desk surface polled by a display
    that holds no per-user token. The tenant still comes from the server
    side: a caller that names a *different* tenant in X-Tenant is refused
    with 403 rather than trusted.
    """
    import app.tenancy as tenancy

    if tenancy.presented_token(request.headers):
        return require_platform_token(request)
    named = str(request.headers.get(tenancy.TENANT_HEADER) or "").strip()
    if named and named != tenancy.DEFAULT_TENANT:
        raise HTTPException(status_code=403, detail="tenant_mismatch")
    return tenancy.default_tenant()


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