"""Role-based access control for LexManage.

Written by the factory WRITER role (codewhale exec).

Roles come from the C-BRIEF: the people who run a law firm's platform are
firm operators and admins. A role carries a permission set over capabilities;
a caller without the permission is refused with HTTP 403 before any block is
reached. Authentication itself (401) stays in app/auth.py.

    operator  matter / intake / document / billing / portal day-to-day work,
              read-only legal_analytics and compliance_audit, rag read+write
    admin     everything, including legal_analytics and compliance_audit

The role itself always comes from the authenticated principal (app/tenancy.py)
— a payload that names its own role is not trusted to grant anything.
"""

from __future__ import annotations

from typing import Dict, FrozenSet, Iterable, Mapping, Optional, Sequence, Tuple

WRITE = "write"
READ = "read"

ROLE_PERMISSIONS: Dict[str, FrozenSet[str]] = {
    "operator": frozenset(
        {
            "matter_management:read",
            "matter_management:write",
            "client_intake:read",
            "client_intake:write",
            "document_management:read",
            "document_management:write",
            "time_and_billing:read",
            "time_and_billing:write",
            "client_portal:read",
            "client_portal:write",
            "legal_analytics:read",
            "compliance_audit:read",
            "rag:read",
            "rag:write",
        }
    ),
    "admin": frozenset(
        {
            "matter_management:read",
            "matter_management:write",
            "client_intake:read",
            "client_intake:write",
            "document_management:read",
            "document_management:write",
            "time_and_billing:read",
            "time_and_billing:write",
            "client_portal:read",
            "client_portal:write",
            "legal_analytics:read",
            "legal_analytics:write",
            "compliance_audit:read",
            "compliance_audit:write",
            "rag:read",
            "rag:write",
        }
    ),
}

#: Capability → the permission a write to it requires.
CAPABILITY_PERMISSION: Dict[str, str] = {
    "matter_management": "matter_management:write",
    "client_intake": "client_intake:write",
    "document_management": "document_management:write",
    "time_and_billing": "time_and_billing:write",
    "client_portal": "client_portal:write",
    "legal_analytics": "legal_analytics:write",
    "compliance_audit": "compliance_audit:write",
}


class AccessDenied(PermissionError):
    """The principal's role does not carry the permission."""


def permissions_for(roles: Iterable[str]) -> FrozenSet[str]:
    granted: set = set()
    for role in roles or ():
        granted |= ROLE_PERMISSIONS.get(str(role).strip().lower(), frozenset())
    return frozenset(granted)


def has_permission(roles: Iterable[str], permission: str) -> bool:
    return str(permission) in permissions_for(roles)


def require_permission(roles: Sequence[str], permission: str) -> None:
    if not has_permission(roles, permission):
        raise AccessDenied(
            "role(s) %s lack %s" % (", ".join(roles) or "none", permission)
        )


def capability_permission(capability_id: str, action: str = WRITE) -> Optional[str]:
    base = CAPABILITY_PERMISSION.get(str(capability_id or ""))
    if base is None:
        return None
    if action == READ:
        return base.split(":", 1)[0] + ":read"
    return base


def describe_roles() -> Dict[str, list]:
    """The access matrix as data, for GET /v1/roles."""
    return {role: sorted(perms) for role, perms in sorted(ROLE_PERMISSIONS.items())}
