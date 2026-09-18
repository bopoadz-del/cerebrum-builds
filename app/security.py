"""Bearer principals for the platform's HTTP surface.

Written by the factory WRITER role (codewhale exec)

The tenant a request runs as is resolved from the authenticated principal --
never from the request body and never from an ``X-Tenant`` header. A header
that disagrees with the token is refused (403) instead of trusted; the same
rule as app/tenancy.py, applied at the HTTP edge so a handler never sees a
tenant it did not earn.

Scope
-----
READS  request headers; ``PLATFORM_TOKEN`` / ``TENANT_TOKENS`` (process env).
WRITES nothing.
NEVER  network; the request body; a client-supplied tenant name.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Tuple

from fastapi import HTTPException, Request

import app.tenancy as tenancy

TENANT_HEADER = "x-tenant"


@dataclass(frozen=True)
class Principal:
    """The authenticated caller: a token, its tenant, and its roles."""

    token: str
    tenant: str
    roles: Tuple[str, ...] = ("operator",)

    def to_dict(self) -> dict:
        return {
            "tenant_id": self.tenant,
            "roles": list(self.roles),
            "token_fingerprint": fingerprint(self.token),
        }


def fingerprint(token: str) -> str:
    """A stable, non-reversible label for a token (never the token itself)."""
    import hashlib

    return hashlib.sha256(str(token).encode("utf-8")).hexdigest()[:12]


def bearer_token(request: Request) -> str:
    """The presented bearer token, or '' when the caller presented none."""
    header = str(request.headers.get("authorization") or "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return str(request.headers.get("x-platform-token") or "").strip()


def principal_from_header(token: str) -> Principal:
    """Resolve a token to a principal, refusing unknown tokens by name."""
    mapping = tenancy.token_map()
    tenant = mapping.get(str(token).strip())
    if not tenant:
        raise tenancy.TenantRefused("token is not bound to a tenant")
    return Principal(token=str(token).strip(), tenant=tenant)


def refuse_tenant_spoof(request: Request, principal: Principal) -> None:
    """An X-Tenant that disagrees with the principal is refused, not trusted."""
    named = str(request.headers.get(TENANT_HEADER) or "").strip()
    if named and named != principal.tenant:
        raise HTTPException(status_code=403, detail="tenant_mismatch")


def require_principal(request: Request) -> Principal:
    """Resolve the caller or answer 401 -- the one path HTTP uses."""
    token = bearer_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="authentication_required")
    try:
        principal = principal_from_header(token)
    except tenancy.TenantRefused:
        raise HTTPException(status_code=401, detail="authentication_required")
    refuse_tenant_spoof(request, principal)
    return principal


def headers_of(mapping: Mapping[str, str] | None) -> Mapping[str, str]:
    return mapping or {}
