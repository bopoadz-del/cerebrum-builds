"""Tenancy for VetClinicOS: one tenant per request, always.

Written by the factory WRITER role (codewhale exec).

The tenant is resolved from the authenticated principal — the bearer token
the caller presented — and never from a client-supplied name. A payload that
tries to name its own tenant is refused rather than trusted, because trusting
it is the classic cross-tenant read.

Token → tenant mapping comes from the environment:

    PLATFORM_TOKEN            the platform token (default dev-local-token)
    VETCLINIC_TENANT_TOKENS   "token:tenant,token:tenant" for additional staff
    VETCLINIC_TENANT_NAMES    "tenant:display name" for readable tenant names

Every corpus read and write in this platform goes through the tenant store
resolved here (app/retrieval.py indexes per tenant).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

#: Reserved keys a capability payload may never carry: tenancy is server-side.
RESERVED_TENANT_KEYS = ("tenant", "tenant_id", "tenant_name", "org_id", "organisation_id")

DEFAULT_TENANT = "local"


class TenantRefused(PermissionError):
    """A caller tried to name their own tenant, or presented no principal."""


@dataclass(frozen=True)
class Tenant:
    tenant_id: str
    name: str
    roles: Tuple[str, ...] = ("admin",)

    def to_dict(self) -> Dict[str, Any]:
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
    token = (os.getenv("PLATFORM_TOKEN") or "dev-local-token").strip()
    mapping: Dict[str, str] = {token: DEFAULT_TENANT}
    for tok, tenant in _pairs(os.getenv("VETCLINIC_TENANT_TOKENS") or ""):
        mapping[tok] = tenant
    return mapping


def tenant_names() -> Dict[str, str]:
    names = {DEFAULT_TENANT: "VetClinicOS (local)"}
    for tenant, name in _pairs(os.getenv("VETCLINIC_TENANT_NAMES") or ""):
        names[tenant] = name
    return names


def role_map() -> Dict[str, Tuple[str, ...]]:
    """token → roles. Platform token is admin; staff tokens from env.

    ``VETCLINIC_ROLE_TOKENS`` is "token:role,token:role" with role in
    vet / receptionist / admin (see app/security.py).
    """
    token = (os.getenv("PLATFORM_TOKEN") or "dev-local-token").strip()
    mapping: Dict[str, Tuple[str, ...]] = {token: ("admin",)}
    for tok, role in _pairs(os.getenv("VETCLINIC_ROLE_TOKENS") or ""):
        mapping[tok] = tuple(part.strip() for part in role.split("+") if part.strip())
    return mapping


def bearer_token(headers: Mapping[str, str]) -> str:
    raw = str(headers.get("authorization") or "")
    if raw.lower().startswith("bearer "):
        return raw[7:].strip()
    return str(headers.get("x-platform-token") or "").strip()


def resolve_tenant(headers: Mapping[str, str]) -> Tenant:
    """The tenant of the authenticated principal. Never the caller's claim."""
    token = bearer_token(headers)
    if not token:
        raise TenantRefused("authentication_required")
    tenant_id = token_map().get(token)
    if not tenant_id:
        raise TenantRefused("authentication_required")
    roles = role_map().get(token, ("admin",))
    name = tenant_names().get(tenant_id, tenant_id)
    return Tenant(tenant_id=tenant_id, name=name, roles=roles)


def refuse_client_tenant(payload: Any) -> None:
    """A payload that carries a tenant key is refused, not silently stripped."""
    if not isinstance(payload, dict):
        return
    offending = sorted(key for key in RESERVED_TENANT_KEYS if key in payload)
    if offending:
        raise TenantRefused(
            "tenant is resolved from the authenticated principal; "
            "remove " + ", ".join(offending)
        )


def tenant_store(tenant: Tenant) -> Any:
    """The tenant's corpus store (app.retrieval). Nothing else is reachable."""
    from app import retrieval

    return retrieval.index_for(tenant.tenant_id)
