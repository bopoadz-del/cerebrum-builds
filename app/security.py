"""Principal authentication for the platform's HTTP surface.

Written by the factory WRITER role (codewhale exec)

One bearer token (``PLATFORM_TOKEN``) identifies one principal. The principal
carries the roles the platform recognises (``operator``, ``admin``) and the
tenant it belongs to; nothing in a request may override the tenant -- a
client-supplied ``X-Tenant`` that disagrees with the authenticated principal is
refused rather than trusted.

Scope
-----
READS  the request headers, ``PLATFORM_TOKEN``.
WRITES nothing.
NEVER  network, credential stores, ``vendor/**``.
"""

from __future__ import annotations

import hmac
import os
from dataclasses import dataclass, field
from typing import Dict, Optional, Sequence

from fastapi import HTTPException, Request

PLATFORM_TOKEN_ENV = "PLATFORM_TOKEN"
DEFAULT_PLATFORM_TOKEN = "dev-local-token"

#: Roles the domain pack declares for this platform.
ROLES: Sequence[str] = ("operator", "admin")
#: The tenant the development principal belongs to.
DEFAULT_TENANT = "local"


@dataclass(frozen=True)
class Principal:
    """The authenticated caller. The tenant comes from here, never the request."""

    subject: str
    tenant: str
    roles: Sequence[str] = field(default_factory=tuple)

    @property
    def is_admin(self) -> bool:
        return "admin" in self.roles

    def to_dict(self) -> Dict[str, object]:
        return {"subject": self.subject, "tenant": self.tenant, "roles": list(self.roles)}


def platform_token() -> str:
    return (os.environ.get(PLATFORM_TOKEN_ENV) or DEFAULT_PLATFORM_TOKEN).strip()


def bearer_token(request: Request) -> str:
    header = request.headers.get("authorization") or ""
    token = (request.headers.get("x-platform-token") or "").strip()
    if header.lower().startswith("bearer "):
        token = header[7:].strip()
    return token


def authenticate(request: Request) -> Principal:
    """Resolve the principal, or raise 401. Constant-time token compare."""
    token = bearer_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="authentication_required")
    if not hmac.compare_digest(token, platform_token()):
        raise HTTPException(status_code=401, detail="authentication_required")
    return Principal(subject="platform-token", tenant=DEFAULT_TENANT, roles=ROLES)


def require_role(principal: Principal, role: str) -> Principal:
    if role not in principal.roles:
        raise HTTPException(status_code=403, detail="role_required: " + role)
    return principal


def principal_from_header(value: Optional[str]) -> Principal:
    """Test/dev helper: build a principal for a token without an HTTP request."""
    token = (value or "").strip()
    if token and hmac.compare_digest(token, platform_token()):
        return Principal(subject="platform-token", tenant=DEFAULT_TENANT, roles=ROLES)
    raise HTTPException(status_code=401, detail="authentication_required")
