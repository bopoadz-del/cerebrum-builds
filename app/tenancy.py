"""One tenant per request, always.

Written by the factory WRITER role (codewhale exec)

The tenant is resolved from the authenticated principal (``app.security``) and
published in a context variable for the duration of the request. Corpus and
answer reads take the tenant from that context -- never from a query string, a
body field, or an ``X-Tenant`` header the caller made up. A header that
disagrees with the authenticated principal is refused, because silently
honouring it is how one customer's documents end up in another's answer.

Every table this platform owns lives in one STORAGE_PATH database; tenancy is a
column and a predicate, not a second file, so the single-persistence-root
contract holds.

Scope
-----
READS  the request (through app.security), ``PLATFORM_TOKEN``.
WRITES nothing.
NEVER  network, a second database file, ``vendor/**``.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator, Optional

from fastapi import HTTPException, Request

from app.security import DEFAULT_TENANT, Principal, authenticate

#: The tenant bound to the request in flight.
_current: ContextVar[Optional[str]] = ContextVar("hotel-front-desk_tenant", default=None)


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
    principal = resolve(request)
    return principal.tenant


def scoped(request: Request) -> Iterator[str]:
    """Bind the authenticated tenant for the rest of the request handler."""
    principal = resolve(request)
    return bind(principal.tenant)
