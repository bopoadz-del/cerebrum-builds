"""Role-based access control for RetailOS.

Written by the factory WRITER role (codewhale exec).

Roles come from the C-BRIEF: the people who run a retailer's platform are
store operators and admins. A role carries a permission set over
capabilities; a caller without the permission is refused with HTTP 403
before any block is reached. Authentication itself (401) stays in
app/auth.py.

    operator  inventory / sales / customer / supplier / sync day-to-day work,
              read-only analytics and compliance
    admin     everything, including analytics_dashboard and
              compliance_and_audit writes

The role itself always comes from the authenticated principal
(app/tenancy.py) — a payload that names its own role is not trusted to
grant anything.
"""

from __future__ import annotations

from typing import Dict, FrozenSet, Iterable, Mapping, Optional, Sequence, Tuple

WRITE = "write"
READ = "read"

ROLE_PERMISSIONS: Dict[str, FrozenSet[str]] = {
    "operator": frozenset(
        {
            "analytics_dashboard:read",
            "analytics_dashboard:write",
            "compliance_and_audit:read",
            "compliance_and_audit:write",
            "customer_insights:read",
            "customer_insights:write",
            "inventory_management:read",
            "inventory_management:write",
            "omnichannel_integration:read",
            "omnichannel_integration:write",
            "sales_and_orders:read",
            "sales_and_orders:write",
            "supplier_and_purchasing:read",
            "supplier_and_purchasing:write",
            "rag:read",
            "rag:write",
        }
    ),
    "admin": frozenset(
        {
            "analytics_dashboard:read",
            "analytics_dashboard:write",
            "compliance_and_audit:read",
            "compliance_and_audit:write",
            "customer_insights:read",
            "customer_insights:write",
            "inventory_management:read",
            "inventory_management:write",
            "omnichannel_integration:read",
            "omnichannel_integration:write",
            "sales_and_orders:read",
            "sales_and_orders:write",
            "supplier_and_purchasing:read",
            "supplier_and_purchasing:write",
            "rag:read",
            "rag:write",
        }
    ),
}

#: Capability → the permission a write to it requires.
CAPABILITY_PERMISSION: Dict[str, str] = {
    "inventory_management": "inventory_management:write",
    "sales_and_orders": "sales_and_orders:write",
    "customer_insights": "customer_insights:write",
    "analytics_dashboard": "analytics_dashboard:write",
    "supplier_and_purchasing": "supplier_and_purchasing:write",
    "omnichannel_integration": "omnichannel_integration:write",
    "compliance_and_audit": "compliance_and_audit:write",
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
