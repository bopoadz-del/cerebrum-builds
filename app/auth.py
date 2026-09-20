"""Capability routes require an authenticated staff credential.

POST /v1/<capability> without a bearer token, X-Platform-Token, or the
staff session cookie is HTTP 401. Missing required fields and invalid enums
are HTTP 422. JSON ``ok: false`` with HTTP 200 is not an auth or validation
pass.

A caller that authenticates with the platform token is issued an opaque
session cookie (see app.tenancy) so the served console can keep working
without re-sending the token on every call. Minting happens on the way out
of a request that already authenticated; an anonymous request is never
given a session, and an anonymous call is still refused with 401.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from fastapi import HTTPException, Request

PLATFORM_TOKEN_ENV = "PLATFORM_TOKEN"
DEFAULT_PLATFORM_TOKEN = "dev-local-token"

#: Keys a domain record may never carry: the tenant and the dispatch action
#: are server-side facts, not caller-supplied fields.
RESERVED_PAYLOAD_KEYS = (
    "tenant",
    "tenant_id",
    "tenant_name",
    "org_id",
    "organisation_id",
    "action",
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


def session_cookie_secure() -> bool:
    """Whether the session cookie is TLS-only.

    Default off because a pilot runs over plain http on localhost; a
    deployment behind TLS sets SESSION_COOKIE_SECURE=1. Named, not assumed:
    the operator decides.
    """
    raw = (os.environ.get("SESSION_COOKIE_SECURE") or "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def attach_session(request: Request, response: Any) -> Optional[str]:
    """Issue a staff session cookie to a caller that just authenticated.

    Returns the session id when one was minted, else None. Nothing happens
    for a request that presented no token, an unbound token, or a live
    session of its own — so an anonymous caller can neither create nor
    extend a session, and a working console is not rotated on every call.

    Never raises: it runs on the way out of every request, and a session
    cookie is a convenience for an already-authenticated caller, not a
    precondition for answering one.
    """
    import app.tenancy as tenancy

    headers = request.headers
    header = str(headers.get("authorization") or "")
    token = str(headers.get("x-platform-token") or "").strip()
    if header.lower().startswith("bearer "):
        token = header[7:].strip()
    if not token:
        return None
    tenant_id = tenancy.token_map().get(token)
    if not tenant_id:
        return None
    if tenancy.session_tenant(headers) is not None:
        return None
    session_id, ttl = tenancy.mint_session(tenant_id)
    try:
        response.set_cookie(
            tenancy.SESSION_COOKIE,
            session_id,
            max_age=ttl,
            httponly=True,
            samesite="strict",
            secure=session_cookie_secure(),
            path="/",
        )
    except Exception:  # noqa: BLE001 - a response that cannot carry a cookie
        return None
    return session_id


def reject_invalid_payload(capability_id: str, payload: Dict[str, Any] | None) -> None:
    from app.models import MODELS

    cls = MODELS.get(capability_id)
    if cls is None:
        raise HTTPException(status_code=422, detail="unknown capability")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="payload must be an object")
    # Reserved keys: tenancy and dispatch scope come from the authenticated
    # principal, never from the record. A caller that names its own tenant is
    # refused by name rather than quietly mapped or ignored.
    for reserved in sorted(RESERVED_PAYLOAD_KEYS):
        if reserved in payload:
            raise HTTPException(
                status_code=422,
                detail="reserved field refused: " + reserved,
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
        value = payload[name]
        allowed = rules.get("allowed_values")
        if allowed is not None and value not in allowed:
            raise HTTPException(
                status_code=422,
                detail=name + " must be one of: " + ", ".join(str(v) for v in allowed),
            )
        low, high = rules.get("min"), rules.get("max")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if low is not None and value < low:
                raise HTTPException(
                    status_code=422,
                    detail="%s must be >= %s" % (name, low),
                )
            if high is not None and value > high:
                raise HTTPException(
                    status_code=422,
                    detail="%s must be <= %s" % (name, high),
                )
        if rules.get("format") == "date" and value not in (None, ""):
            try:
                from datetime import date as _date

                _date.fromisoformat(str(value)[:10])
            except ValueError:
                raise HTTPException(
                    status_code=422,
                    detail=name + " must be an ISO date (YYYY-MM-DD)",
                ) from None