"""Tenancy for this platform: one tenant per request, always.

The tenant is resolved from the authenticated principal — the bearer
token the caller presented — and never from a client-supplied name. A
payload that tries to name its own tenant is refused rather than trusted.

Token → tenant mapping comes from the environment:

    PLATFORM_TOKEN      the platform token (default dev-local-token)
    TENANT_TOKENS       "token:tenant,token:tenant" for extra tenants
    TENANT_NAMES        "tenant:display name" for readable names

Every capability read and write goes through the tenant resolved here —
app/store.py scopes every row by tenant_id.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List, Mapping, Tuple

#: Reserved keys a capability payload may never carry: tenancy is
#: server-side, resolved from the token, never from the payload.
RESERVED_TENANT_KEYS = ("tenant", "tenant_id", "tenant_name", "org_id", "organisation_id")

#: The header a caller might use to name a tenant. Never trusted: it may
#: only agree with the resolved principal (app/security.refuse_tenant_spoof,
#: app/auth.read_tenant). Mirrors app.security.TENANT_HEADER.
TENANT_HEADER = "x-tenant"

DEFAULT_TENANT = "local"


class TenantRefused(PermissionError):
    """A caller presented no token, an unbound token, or tried to name
    their own tenant."""


@dataclass(frozen=True)
class Tenant:
    tenant_id: str
    name: str
    roles: Tuple[str, ...] = ("admin",)

    def to_dict(self) -> Dict[str, object]:
        return {"tenant_id": self.tenant_id, "name": self.name, "roles": list(self.roles)}


def _pairs(raw: str) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    for chunk in str(raw or "").split(","):
        chunk = chunk.strip()
        if not chunk or ":" not in chunk:
            continue
        left, right = chunk.split(":", 1)
        left, right = left.strip(), right.strip()
        if left and right:
            out.append((left, right))
    return out


def token_map() -> Dict[str, str]:
    """token → tenant_id. The platform token owns the default tenant."""
    out: Dict[str, str] = {}
    platform = (os.environ.get("PLATFORM_TOKEN") or "dev-local-token").strip()
    if platform:
        out[platform] = DEFAULT_TENANT
    for token, tenant in _pairs(os.environ.get("TENANT_TOKENS", "")):
        out[token] = tenant
    return out


def name_map() -> Dict[str, str]:
    return dict(_pairs(os.environ.get("TENANT_NAMES", "")))


def presented_token(headers: Mapping[str, str]) -> str:
    """The credential the caller presented, or ''.

    One reader for both spellings the platform accepts (``Authorization:
    Bearer`` and ``X-Platform-Token``), so "did the caller present a
    credential at all?" has a single answer.
    """
    header = str(headers.get("authorization") or headers.get("Authorization") or "")
    token = str(headers.get("x-platform-token") or "").strip()
    if header.lower().startswith("bearer "):
        token = header[7:].strip()
    return token


def tenant_by_id(tenant_id: str) -> Tenant:
    """The tenant record for one configured tenant id."""
    tid = str(tenant_id or "").strip() or DEFAULT_TENANT
    return Tenant(tenant_id=tid, name=name_map().get(tid, tid))


def default_tenant() -> Tenant:
    """The platform's own front-desk tenant (DEFAULT_TENANT).

    Used only by a READ that presents no credential at all — see
    app/auth.read_tenant. Writes always require a credential.
    """
    return tenant_by_id(DEFAULT_TENANT)


def resolve_tenant(headers: Mapping[str, str]) -> Tenant:
    """Resolve the caller's tenant from the request headers.

    Refuses by name: no token, an unknown token, or a payload-supplied
    tenant identity all raise TenantRefused — the caller is never mapped
    to a default tenant.
    """
    token = presented_token(headers)
    if not token:
        raise TenantRefused("no token presented")
    tenant_id = token_map().get(token)
    if not tenant_id:
        raise TenantRefused("token is not bound to a tenant")
    return tenant_by_id(tenant_id)