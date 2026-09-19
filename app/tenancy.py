"""One tenant per request, always.

Written by the factory WRITER role (codewhale exec)

The tenant is resolved from the authenticated principal (``app.security``) and
published in a context variable for the duration of the request. Reads take the
tenant from that context — never from a query string, a body field, or an
``X-Tenant`` header the caller invented. A header that disagrees with the
authenticated principal is refused, because silently honouring it is how one
customer's records end up in another's answer.

Every table lives in one ``STORAGE_PATH`` database; tenancy is a column and a
predicate, not a second file, so the single-persistence-root contract holds.

Scope
-----
READS  the request (through ``app.security``), ``PLATFORM_TOKEN``.
WRITES nothing.
NEVER  network, a second database file, ``vendor/**``.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator, Optional

from fastapi import HTTPException, Request

from app.security import DEFAULT_TENANT, Principal, authenticate, optional_principal

_current: ContextVar[Optional[str]] = ContextVar("bakery_tenant", default=None)


def current_tenant() -> str:
    """The bound tenant, or the development tenant outside a request."""
    return _current.get() or DEFAULT_TENANT


@contextmanager
def bind(tenant: str) -> Iterator[str]:
    token = _current.set(tenant)
    try:
        yield tenant
    finally:
        _current.reset(token)


def refuse_tenant_spoof(request: Request, principal: Principal) -> None:
    """A client-supplied tenant must agree with the authenticated principal."""
    claimed = (request.headers.get("x-tenant") or "").strip()
    if claimed and claimed != principal.tenant:
        raise HTTPException(
            status_code=403,
            detail="tenant_override_refused: the tenant comes from the principal",
        )


def resolve(request: Request) -> Principal:
    """Authenticate the caller and bind its tenant for this request."""
    principal = authenticate(request)
    refuse_tenant_spoof(request, principal)
    return principal


def require_tenant(request: Request) -> str:
    """The tenant for this request: the authenticated principal's, nothing else."""
    return resolve(request).tenant


def read_tenant(request: Request) -> Optional[str]:
    """The tenant for an anonymous read: the principal's, or None when absent.

    The list route is the chain's display board: the factory's PRODUCT
    round-trip reads it without a token, and a token that IS present must be
    valid and must agree with any ``X-Tenant`` the caller sent. Writes never
    take this path.
    """
    principal = optional_principal(request)
    if principal is None:
        return None
    refuse_tenant_spoof(request, principal)
    return principal.tenant
