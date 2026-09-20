"""Tenancy for this platform: one tenant per request, always.

The tenant is resolved from the authenticated principal — the bearer
 token the caller presented — and never from a client-supplied name. A
payload that tries to name its own tenant is refused rather than trusted.

Token → tenant mapping comes from the environment:

    PLATFORM_TOKEN      the platform token (default dev-local-token)
    TENANT_TOKENS       "token:tenant,token:tenant" for extra tenants
    TENANT_NAMES        "tenant:display name" for readable names

Staff sessions
  A request may present its credential in one of two ways, and both are
  resolved here so there is exactly one answer to "whose rows are these?":

  * ``Authorization: Bearer <platform token>`` (or ``X-Platform-Token``):
    the token the staff member was issued; or
  * the session cookie this module mints. A caller that has just
    authenticated with a token receives an opaque, server-side session id
    (never the token itself) bound to exactly the tenant that token
    resolved to. That is what lets the served staff console and the
    generated API client continue a working session without re-sending the
    platform token on every call.

  A request that presents neither is refused; it is never mapped to a
  default tenant. The session store is process-local, like the rate
  limiter, and bounded so an unauthenticated caller cannot grow it: only a
  request that already authenticated with a valid token can mint one.

Every capability read and write goes through the tenant resolved here —
app/store.py scopes every row by tenant_id.
"""

from __future__ import annotations

import os
import secrets
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional, Tuple

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


def resolve_tenant(headers: Mapping[str, str]) -> Tenant:
    """Resolve the caller's tenant from the presented credential.

    Credential order: bearer header, then X-Platform-Token, then the staff
    session cookie minted by :func:`mint_session`. A session id is opaque
    and server-issued, so it is a credential the platform itself handed
    out, not a client-supplied tenant name: the mapping session → tenant
    lives on this side only.

    Refuses by name: no credential at all, an unknown token, an expired or
    unknown session, or a payload-supplied tenant identity all raise
    TenantRefused — the caller is never mapped to a default tenant.
    """
    header = str(headers.get("authorization") or headers.get("Authorization") or "")
    token = str(headers.get("x-platform-token") or "").strip()
    if header.lower().startswith("bearer "):
        token = header[7:].strip()
    if token:
        tenant_id = token_map().get(token)
        if not tenant_id:
            raise TenantRefused("token is not bound to a tenant")
        return Tenant(tenant_id=tenant_id, name=name_map().get(tenant_id, tenant_id))
    session = session_tenant(headers)
    if session is not None:
        return session
    raise TenantRefused("no token presented")


# -- staff sessions -------------------------------------------------------

#: Name of the session cookie a token-authenticated caller is issued.
SESSION_COOKIE = "fleetops_session"

#: Seconds a session stays valid. Env-tunable: SESSION_TTL_SECONDS.
SESSION_TTL_ENV = "SESSION_TTL_SECONDS"
SESSION_TTL_DEFAULT = 8 * 60 * 60

#: Upper bound on live sessions so the store cannot grow without limit.
SESSION_LIMIT = 1024

#: session id -> (tenant_id, issued_at). One process, one table, bounded.
_SESSIONS: "OrderedDict[str, Tuple[str, float]]" = OrderedDict()


def session_ttl_seconds() -> int:
    raw = (os.environ.get(SESSION_TTL_ENV) or "").strip()
    try:
        value = int(raw) if raw else SESSION_TTL_DEFAULT
    except ValueError:
        return SESSION_TTL_DEFAULT
    return value if value > 0 else SESSION_TTL_DEFAULT


def mint_session(tenant_id: str) -> Tuple[str, int]:
    """Issue an opaque session id bound to one tenant. Returns (id, ttl)."""
    now = time.time()
    ttl = session_ttl_seconds()
    for key, (_, issued) in list(_SESSIONS.items()):
        if now - issued > ttl:
            _SESSIONS.pop(key, None)
    while len(_SESSIONS) >= SESSION_LIMIT:
        _SESSIONS.popitem(last=False)
    session_id = secrets.token_urlsafe(32)
    _SESSIONS[session_id] = (str(tenant_id), now)
    return session_id, ttl


def drop_session(session_id: str) -> bool:
    """Forget one session (sign-out). True when it existed."""
    return _SESSIONS.pop(str(session_id or ""), None) is not None


def _cookie_value(headers: Mapping[str, str], name: str) -> Optional[str]:
    raw = headers.get("cookie") or headers.get("Cookie") or ""
    for chunk in str(raw).split(";"):
        chunk = chunk.strip()
        if not chunk or "=" not in chunk:
            continue
        key, value = chunk.split("=", 1)
        if key.strip() == name:
            return value.strip()
    return None


def session_tenant(headers: Mapping[str, str]) -> Optional[Tenant]:
    """The tenant behind the presented session cookie, or None."""
    session_id = _cookie_value(headers, SESSION_COOKIE)
    if not session_id:
        return None
    entry = _SESSIONS.get(session_id)
    if entry is None:
        return None
    tenant_id, issued = entry
    if time.time() - issued > session_ttl_seconds():
        _SESSIONS.pop(session_id, None)
        return None
    return Tenant(tenant_id=tenant_id, name=name_map().get(tenant_id, tenant_id))


def active_session_count() -> int:
    """Live sessions in this process (operational visibility only)."""
    return len(_SESSIONS)