"""Tenancy for CallOps: one tenant per request, always.

PSI is a tenant; a second brokerage is a row, not a rebuild. The tenant is
resolved from the authenticated principal — the bearer token the caller
presented — and never from a client-supplied name. A payload that tries to
name its own tenant is refused rather than trusted (see
``security.RESERVED_TENANT_KEYS``).

Token → tenant mapping comes from the environment:

    PLATFORM_TOKEN      the platform token (dev default ``dev-local-token``)
    PLATFORM_TENANT     tenant that token owns (default ``local``)
    PLATFORM_TOKEN_B    second operator token (dev default ``dev-local-token-b``)
    PLATFORM_TENANT_B   tenant that token owns (default ``psi-partner-b``)
    TENANT_TOKENS       "token:tenant,token:tenant" for further tenants
    TENANT_NAMES        "tenant:display name" for readable names

Every capability read and write goes through the tenant resolved here —
``app/store.py`` scopes every row by ``tenant_id``. An unknown token is
refused (401 by the HTTP layer); it is never folded into a default tenant,
because that is how one brokerage reads another's leads.

A READ in a single-tenant deployment (see ``single_tenant_posture``) is the
one exception, and it is a posture rather than a default: a deployment that
binds exactly one operator tenant lets a token-less read resolve to its own
tenant, so the console and the platform's own probes can read the queue they
run. Bind ``PLATFORM_TOKEN_B`` or ``TENANT_TOKENS`` and reads demand a
principal like everything else. A write never takes this path.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Tuple

#: Reserved keys a capability payload may never carry: tenancy is
#: server-side, resolved from the token, never from the payload.
RESERVED_TENANT_KEYS = (
    "tenant",
    "tenant_id",
    "tenant_name",
    "org_id",
    "organisation_id",
    "organization_id",
)

DEFAULT_TENANT = os.environ.get("PLATFORM_TENANT", "local")


class TenantRefused(PermissionError):
    """No token, an unbound token, or a payload that named its own tenant."""


ALL_PERMISSIONS: Tuple[str, ...] = ("read", "write", "process")


def permission_map() -> Dict[str, Tuple[str, ...]]:
    """tenant → permissions, from ``TENANT_PERMISSIONS``.

    ``TENANT_PERMISSIONS="psi:read+write+process,other-brokerage:read"`` — a
    read-only brokerage is then refused on a write with 403, which is the
    point of having permissions at all. Unlisted tenants get the full set,
    which is what a platform with one operator needs and is stated here
    rather than left implicit.
    """
    out: Dict[str, Tuple[str, ...]] = {}
    for entry in str(os.environ.get("TENANT_PERMISSIONS", "") or "").split(","):
        chunk = entry.strip()
        if not chunk or ":" not in chunk:
            continue
        tenant, _, grants = chunk.partition(":")
        granted = tuple(
            name.strip()
            for name in grants.replace("|", "+").split("+")
            if name.strip() in ALL_PERMISSIONS
        )
        if tenant.strip():
            out[tenant.strip()] = granted or ("read",)
    return out


@dataclass(frozen=True)
class Tenant:
    tenant_id: str
    name: str
    roles: Tuple[str, ...] = ("operator",)
    permissions: Tuple[str, ...] = ALL_PERMISSIONS

    def to_dict(self) -> Dict[str, object]:
        return {
            "tenant_id": self.tenant_id,
            "name": self.name,
            "roles": list(self.roles),
            "permissions": list(self.permissions),
        }

    def can(self, permission: str) -> bool:
        return permission in self.permissions


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
    """token → tenant_id. Every operator token owns exactly one tenant."""
    out: Dict[str, str] = {}
    platform = (os.environ.get("PLATFORM_TOKEN") or "dev-local-token").strip()
    if platform:
        out[platform] = (os.environ.get("PLATFORM_TENANT") or DEFAULT_TENANT).strip()
    second = (os.environ.get("PLATFORM_TOKEN_B") or "dev-local-token-b").strip()
    if second:
        out[second] = (os.environ.get("PLATFORM_TENANT_B") or "psi-partner-b").strip()
    for token, tenant in _pairs(os.environ.get("TENANT_TOKENS", "")):
        out[token] = tenant
    return out


def name_map() -> Dict[str, str]:
    return dict(_pairs(os.environ.get("TENANT_NAMES", "")))


def display_name(tenant_id: str) -> str:
    return name_map().get(tenant_id, tenant_id)


def presented_token(headers: Mapping[str, str]) -> str:
    """The bearer token, from either header spelling. Never from the body."""
    lowered = {str(k).lower(): v for k, v in dict(headers or {}).items()}
    header = str(lowered.get("authorization") or "")
    token = str(lowered.get("x-platform-token") or "").strip()
    if header.lower().startswith("bearer "):
        token = header[7:].strip()
    return token


def single_tenant_posture() -> bool:
    """True when this deployment binds exactly one operator tenant.

    One operator token and no ``TENANT_TOKENS``: the deployment *is* one
    brokerage, so a token-less read resolves to its own tenant — the console
    an operator opens, and the platform's own probes, read the queue with no
    request principal in hand. Bind ``PLATFORM_TOKEN_B`` (a second operator)
    or any ``TENANT_TOKENS`` entry and this is false: reads then demand a
    principal exactly like writes, because two tenants exist and a read can
    no longer be answered for "the" tenant.
    """
    if _pairs(os.environ.get("TENANT_TOKENS", "")):
        return False
    return not (os.environ.get("PLATFORM_TOKEN_B") or "").strip()


def read_tenant(headers: Mapping[str, str]) -> Tenant:
    """The tenant a READ resolves to.

    A presented token is resolved exactly as a write would resolve it: a
    token this deployment does not know is refused (401), never folded into
    a default tenant. With no token at all, a single-tenant deployment
    answers as its own tenant and every other deployment refuses by name.
    """
    if presented_token(headers):
        return resolve_tenant(headers)
    if single_tenant_posture():
        tenant_id = (os.environ.get("PLATFORM_TENANT") or DEFAULT_TENANT).strip()
        return Tenant(
            tenant_id=tenant_id,
            name=display_name(tenant_id),
            permissions=permission_map().get(tenant_id, ALL_PERMISSIONS),
        )
    raise TenantRefused("no token presented")


def deployment_tenant() -> str:
    """The tenant a handler runs as when no principal was injected.

    Two callers exist and only one of them is a request. The route always
    hands a handler the tenant its bearer token resolved; the platform's own
    in-process runner (``app/domain_ops.py``, the acceptance harness, the
    dial-queue prober) calls ``handle()`` with no request at all. For that
    second caller the deployment's own declared tenant applies -- the one
    ``PLATFORM_TENANT`` names, defaulting to this deployment's default.

    A CLIENT can never reach this: ``validate_payload`` refuses a payload that
    carries a tenancy key before any handler sees it, so the only tenant a
    handler is ever handed over HTTP is the one the token resolved. That is
    the property that matters, and it is enforced at the edge rather than
    assumed here.
    """
    return (os.environ.get("PLATFORM_TENANT") or DEFAULT_TENANT).strip() or DEFAULT_TENANT


def resolve_tenant(headers: Mapping[str, str]) -> Tenant:
    """Resolve the caller's tenant from the request headers.

    Refuses by name: no token, or a token that is not bound to a tenant.
    The caller is never silently mapped to a default tenant.
    """
    token = presented_token(headers)
    if not token:
        raise TenantRefused("no token presented")
    tenant_id = token_map().get(token)
    if not tenant_id:
        raise TenantRefused("token is not bound to a tenant")
    return Tenant(
        tenant_id=tenant_id,
        name=display_name(tenant_id),
        permissions=permission_map().get(tenant_id, ALL_PERMISSIONS),
    )


def assert_no_payload_tenancy(payload: Mapping[str, object] | None) -> None:
    """A payload may not name its own tenant. Refused, never honoured."""
    if not isinstance(payload, Mapping):
        return
    for key in RESERVED_TENANT_KEYS:
        if key in payload:
            raise TenantRefused(
                f"payload carries reserved tenancy key {key!r}; tenancy is "
                "resolved from the authenticated principal"
            )


@dataclass
class TenantDirectory:
    """Row-level view of the tenants on this platform (a second brokerage)."""

    rows: List[Dict[str, object]] = field(default_factory=list)

    def register(self, tenant_id: str, name: str = "") -> Dict[str, object]:
        row = {"tenant_id": tenant_id, "name": name or display_name(tenant_id)}
        self.rows = [r for r in self.rows if r["tenant_id"] != tenant_id] + [row]
        return row
