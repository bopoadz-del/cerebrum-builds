"""Request security for the clinic platform.

Two rules, both enforced from the authenticated principal:

* a capability write requires the platform bearer token (HTTP 401 otherwise);
* tenancy is resolved server-side from that token, and a payload that tries to
  name its own tenant is refused rather than trusted.

The heavy lifting lives in :mod:`app.tenancy` (token → tenant) and
:mod:`app.auth` (token + payload contract); this module is the small surface
the rest of the app imports so the rule has one spelling.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping

from fastapi import HTTPException, Request

from app.auth import require_platform_token
from app.tenancy import RESERVED_TENANT_KEYS, Tenant, TenantRefused, resolve_tenant

__all__ = [
    "RESERVED_TENANT_KEYS",
    "SecurityError",
    "assert_no_tenant_keys",
    "authenticate",
    "tenant_of",
]


class SecurityError(PermissionError):
    """The request violates a platform security rule."""


def assert_no_tenant_keys(payload: Mapping[str, Any] | None) -> None:
    """Refuse a payload that names its own tenant."""
    for key in RESERVED_TENANT_KEYS:
        if isinstance(payload, Mapping) and key in payload:
            raise SecurityError(
                f"{key!r} may not be supplied by a caller; tenancy is resolved "
                "from the authenticated principal"
            )


def authenticate(request: Request) -> Tenant:
    """Bearer token → tenant, or HTTP 401/403 by the documented contract."""
    try:
        return require_platform_token(request)
    except HTTPException:
        raise
    except TenantRefused as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def tenant_of(request: Request) -> Tenant:
    """Resolve the tenant without raising on a missing token (read paths)."""
    try:
        return resolve_tenant(request.headers)
    except TenantRefused as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
