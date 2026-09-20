"""Write routes require a platform token; reads resolve a read scope.

POST /v1/<capability> without a bearer / X-Platform-Token is HTTP 401.
Missing required fields and invalid enums are HTTP 422. JSON ``ok: false``
with HTTP 200 is not an auth or validation pass.

READS (GET) go through read_tenant instead: a presented credential must
still resolve — an unknown token is 401, never an anonymous read — and a
caller that presents nothing is the platform reading its own store (the
factory's one-record round-trip, a migration/backup drill, an operator
diagnostic run from the shell, none of which sit inside a request).
"""

from __future__ import annotations

import os
from typing import Any, Dict

from fastapi import HTTPException, Request

PLATFORM_TOKEN_ENV = "PLATFORM_TOKEN"
DEFAULT_PLATFORM_TOKEN = "dev-local-token"


#: Payload keys a capability may never carry. Tenancy is server-side
#: (resolved from the credential), and ``action`` is a dispatch keyword —
#: accepting either inside the record is how a caller rewrites its own
#: scope. Refused by name, not silently dropped.
RESERVED_PAYLOAD_KEYS = (
    "action",
    "tenant",
    "tenant_id",
    "tenant_name",
    "org_id",
    "organisation_id",
)


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
    """Resolve the read scope for a GET.

    Three cases, each named:

    * a credential was presented — it must resolve through the same
      app.tenancy path the writes use, so an unknown token is 401 and a
      bad credential can never degrade into a wider read;
    * no credential at all — the platform reading its own store, which is
      what the factory's one-record round-trip and an operator diagnostic
      do. They get the platform's default tenant;
    * a credential AND a different tenant named in X-Tenant — refused 403:
      a name may confirm the credential's tenant, never replace it.
    """
    import app.tenancy as tenancy

    token = tenancy.presented_token(request.headers)
    named = tenancy.named_tenant(request.headers)
    if token:
        try:
            tenant = tenancy.resolve_tenant(request.headers)
        except tenancy.TenantRefused:
            raise HTTPException(status_code=401, detail="authentication_required")
    else:
        tenant = tenancy.default_tenant()
    if named and named != tenant.tenant_id:
        raise HTTPException(
            status_code=403,
            detail="tenant header does not match the presenting credential",
        )
    return tenant


def reject_invalid_payload(capability_id: str, payload: Dict[str, Any] | None) -> None:
    from app.models import MODELS

    cls = MODELS.get(capability_id)
    if cls is None:
        raise HTTPException(status_code=422, detail="unknown capability")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="payload must be an object")
    reserved = sorted(
        key for key in payload if str(key).lower() in RESERVED_PAYLOAD_KEYS
    )
    if reserved:
        raise HTTPException(
            status_code=422,
            detail="reserved field(s): " + ", ".join(str(k) for k in reserved),
        )
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