"""Role-based access control for VetClinicOS.

Written by the factory WRITER role (codewhale exec).

Roles come from the C-BRIEF: the people who use a veterinary clinic are vets,
receptionists and admins. A role carries a permission set over capabilities;
a caller without the permission is refused with HTTP 403 before any block is
reached. Authentication itself (401) stays in app/auth.py.

    vet           patient_records:read/write, treatment_management:read/write,
                  appointment_scheduling:read, billing_invoicing:read
    receptionist  patient_records:read, appointment_scheduling:read/write,
                  billing_invoicing:read/write, client_communication:read/write
    admin         everything, including role_management and audit_trail

The role itself always comes from the authenticated principal (app/tenancy.py)
— a payload that names its own role is not trusted to grant anything.
"""

from __future__ import annotations

from typing import Dict, FrozenSet, Iterable, Mapping, Optional, Sequence, Tuple

WRITE = "write"
READ = "read"

ROLE_PERMISSIONS: Dict[str, FrozenSet[str]] = {
    "vet": frozenset(
        {
            "patient_records:read",
            "patient_records:write",
            "treatment_management:read",
            "treatment_management:write",
            "appointment_scheduling:read",
            "inventory_management:read",
            "billing_invoicing:read",
            "clinic_analytics:read",
        }
    ),
    "receptionist": frozenset(
        {
            "patient_records:read",
            "appointment_scheduling:read",
            "appointment_scheduling:write",
            "billing_invoicing:read",
            "billing_invoicing:write",
            "inventory_management:read",
        }
    ),
    "admin": frozenset(
        {
            "patient_records:read",
            "patient_records:write",
            "appointment_scheduling:read",
            "appointment_scheduling:write",
            "treatment_management:read",
            "treatment_management:write",
            "billing_invoicing:read",
            "billing_invoicing:write",
            "inventory_management:read",
            "inventory_management:write",
            "audit_trail:read",
            "audit_trail:write",
            "role_management:read",
            "role_management:write",
            "clinic_analytics:read",
            "clinic_analytics:write",
            "rag:read",
            "rag:write",
        }
    ),
}

#: Capability → the permission a write to it requires.
CAPABILITY_PERMISSION: Dict[str, str] = {
    "patient_records": "patient_records:write",
    "appointment_scheduling": "appointment_scheduling:write",
    "treatment_management": "treatment_management:write",
    "billing_invoicing": "billing_invoicing:write",
    "inventory_management": "inventory_management:write",
    "audit_trail": "audit_trail:write",
    "role_management": "role_management:write",
    "clinic_analytics": "clinic_analytics:write",
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
    """The access matrix as data, for the role_management capability."""
    return {role: sorted(perms) for role, perms in sorted(ROLE_PERMISSIONS.items())}
