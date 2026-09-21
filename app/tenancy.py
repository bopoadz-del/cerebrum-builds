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

import contextvars
import os
from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional, Tuple

#: The tenant the request in flight resolved to. The route sets it from the
#: authenticated principal; a handler that needs the corpus (app.retrieval)
#: reads it here instead of being handed a tenant by the caller -- tenancy is
#: never a payload field.
_CURRENT: "contextvars.ContextVar[Optional[str]]" = contextvars.ContextVar(
    "callops_tenant", default=None
)


def set_current_tenant(tenant_id: Optional[str]) -> None:
    _CURRENT.set(str(tenant_id).strip() if tenant_id else None)


def current_tenant_id(fallback: Optional[str] = None) -> str:
    """The resolved tenant, or the configured single-tenant default.

    A handler never invents one: with nothing resolved the fallback (the
    deployment's own default tenant) is used, which is what a single-tenant
    pilot means, and the value still comes from app.tenancy -- not the body.
    """
    resolved = _CURRENT.get()
    if resolved:
        return resolved
    return str(fallback or DEFAULT_TENANT)

#: Reserved keys a capability payload may never carry: tenancy is
#: server-side, resolved from the token, never from the payload.
RESERVED_TENANT_KEYS = ("tenant", "tenant_id", "tenant_name", "org_id", "organisation_id")

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


def tenant_tokens_configured() -> bool:
    """True when this deployment is multi-tenant (more than one principal bound).

    Single-tenant mode is the default: the platform token owns the one tenant.
    The moment TENANT_TOKENS binds a second principal, every read requires a
    token too -- see app.auth.require_read_tenant.
    """
    return bool(_pairs(os.environ.get("TENANT_TOKENS", "")))


#: Prefix for the namespace a read resolves to when the caller presented a
#: principal this deployment does not know. Nothing is ever written there
#: (a write requires a bound principal), so it holds no rows and another
#: tenant's record answers 404 -- never 403 and never the row.
UNBOUND_PRINCIPAL_PREFIX = "unbound-principal:"


def presented_token(headers: Mapping[str, str]) -> str:
    """The bearer / X-Platform-Token the caller presented, ``""`` when none."""
    header = str(headers.get("authorization") or headers.get("Authorization") or "")
    token = str(headers.get("x-platform-token") or "").strip()
    if header.lower().startswith("bearer "):
        token = header[7:].strip()
    return token


def read_tenant(headers: Mapping[str, str]) -> Tenant:
    """The tenant a READ resolves to -- never somebody else's.

    A bound principal resolves as usual, so two brokers behind one deployment
    are two tenants by construction. A principal this deployment does not know
    is NOT folded into the platform's own tenant (that mapped an unknown
    bearer onto the operator's rows and answered 200 with them): it reads its
    own, empty namespace, so a foreign record answers 404. Only a request that
    presented no principal at all keeps the single-tenant convenience, and
    only while no second tenant is bound.
    """
    try:
        return resolve_tenant(headers)
    except TenantRefused:
        token = presented_token(headers)
        if token:
            return Tenant(
                tenant_id=UNBOUND_PRINCIPAL_PREFIX + token,
                name="unbound principal",
                roles=(),
            )
        if tenant_tokens_configured():
            raise
        return default_tenant()


def default_tenant() -> Tenant:
    """The platform's own tenant, for a deployment with exactly one."""
    return Tenant(tenant_id=DEFAULT_TENANT, name=name_map().get(DEFAULT_TENANT, DEFAULT_TENANT))


def resolve_tenant(headers: Mapping[str, str]) -> Tenant:
    """Resolve the caller's tenant from the request headers.

    Refuses by name: no token, an unknown token, or a payload-supplied
    tenant identity all raise TenantRefused — the caller is never mapped
    to a default tenant.
    """
    header = str(headers.get("authorization") or headers.get("Authorization") or "")
    token = str(headers.get("x-platform-token") or "").strip()
    if header.lower().startswith("bearer "):
        token = header[7:].strip()
    if not token:
        raise TenantRefused("no token presented")
    tenant_id = token_map().get(token)
    if not tenant_id:
        raise TenantRefused("token is not bound to a tenant")
    return Tenant(tenant_id=tenant_id, name=name_map().get(tenant_id, tenant_id))