"""Role-based access for the FleetOps Back-Office Platform.

Written by the factory WRITER role (codewhale exec)

Scope
  READS   the authenticated principal on the request and the caller's payload.
  WRITES  the caller's response (a refusal raises before any handler runs).
  NEVER   a client-supplied branch or tenant name: branch scope comes from the
          principal, never from the payload.

The company runs 4 branches with 5 staff each: 2 sales agents, 2 accountants
and 1 branch manager. Sales agents see their own branch's rentals and fleet;
accountants see their branch's money; branch managers see their branch whole
and -- when granted the company scope -- the rollup across all locations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, Iterable, Mapping, Optional, Sequence

#: Reserved keys a caller may never set as domain data.
RESERVED_KEYS: FrozenSet[str] = frozenset(
    {"action", "tenant", "tenant_id", "tenant_name", "org_id", "organisation_id"}
)

ROLE_SALES_AGENT = "sales_agent"
ROLE_ACCOUNTANT = "accountant"
ROLE_BRANCH_MANAGER = "branch_manager"

ROLES: FrozenSet[str] = frozenset(
    {ROLE_SALES_AGENT, ROLE_ACCOUNTANT, ROLE_BRANCH_MANAGER}
)

#: capability -> the roles allowed to write it.
CAPABILITY_ROLES: Dict[str, FrozenSet[str]] = {
    "fleet_registry": frozenset({ROLE_SALES_AGENT, ROLE_BRANCH_MANAGER}),
    "rental_contract_management": frozenset({ROLE_SALES_AGENT, ROLE_BRANCH_MANAGER}),
    "maintenance_scheduling": frozenset({ROLE_BRANCH_MANAGER}),
    "pricing_and_rate_cards": frozenset({ROLE_ACCOUNTANT, ROLE_BRANCH_MANAGER}),
    "invoicing_and_deposits": frozenset({ROLE_ACCOUNTANT, ROLE_BRANCH_MANAGER}),
    "multi_branch_rollup": frozenset({ROLE_BRANCH_MANAGER}),
    "reporting_analytics": frozenset(
        {ROLE_SALES_AGENT, ROLE_ACCOUNTANT, ROLE_BRANCH_MANAGER}
    ),
    "audit_trail": frozenset({ROLE_ACCOUNTANT, ROLE_BRANCH_MANAGER}),
}

#: capability -> True when the caller must hold the company-wide scope.
COMPANY_SCOPE_ONLY: FrozenSet[str] = frozenset({"multi_branch_rollup"})


class AccessRefused(PermissionError):
    """A principal asking for something its role does not cover."""


@dataclass(frozen=True)
class Principal:
    """The authenticated staff member behind one request."""

    user_id: str
    role: str
    branch: str = ""
    company_scope: bool = False

    @property
    def is_manager(self) -> bool:
        return self.role == ROLE_BRANCH_MANAGER


def principal_from_headers(headers: Mapping[str, str]) -> Principal:
    """Build the principal from trusted request headers.

    The branch is taken from the principal, never from the payload: a sales
    agent cannot widen its own visibility by asking for another branch.
    """
    lowered = {str(k).lower(): str(v) for k, v in (headers or {}).items()}
    raw_role = lowered.get("x-staff-role") or lowered.get("x-role") or ROLE_SALES_AGENT
    role = raw_role.strip().lower().replace("-", "_")
    if role not in ROLES:
        raise AccessRefused("unknown staff role: %r" % (raw_role,))
    return Principal(
        user_id=(lowered.get("x-staff-id") or "local").strip() or "local",
        role=role,
        branch=(lowered.get("x-branch") or "").strip(),
        company_scope=(lowered.get("x-company-scope") or "").strip().lower()
        in {"1", "true", "yes", "company"},
    )


def reject_reserved_keys(payload: Dict[str, Any] | None) -> None:
    """A domain record may not carry trust-scope or dispatch keys."""
    for key in sorted(RESERVED_KEYS):
        if isinstance(payload, dict) and key in payload:
            raise AccessRefused("reserved field: " + key)


def require_capability_access(principal: Principal, capability_id: str) -> None:
    """Refuse a principal whose role does not cover this capability."""
    allowed = CAPABILITY_ROLES.get(str(capability_id))
    if allowed is None:
        raise AccessRefused("unknown capability: %r" % (capability_id,))
    if principal.role not in allowed:
        raise AccessRefused(
            "role %r may not act on %s" % (principal.role, capability_id)
        )
    if capability_id in COMPANY_SCOPE_ONLY and not principal.company_scope:
        raise AccessRefused(
            "%s requires the company-wide scope" % capability_id
        )


def visible_branches(principal: Principal, branches: Iterable[str]) -> list:
    """The branches this principal may see, from the principal alone."""
    known = [str(b) for b in branches or ()]
    if principal.company_scope:
        return known
    if not principal.branch:
        return []
    return [b for b in known if b == principal.branch]
