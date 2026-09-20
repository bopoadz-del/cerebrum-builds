"""Handler for capability role_based_access.

Written by the factory WRITER role (codewhale exec)
Authored by the coding agent (codewhale exec) under the factory WRITER role.

Management, technicians and cleaners, and complainants each see and
act on only what they should. This module resolves a principal's
effective permissions from the platform's own role matrix, refuses a
scope wider than the role grants, and records the grant for audit.
Persistence is route-scoped: the tenant-scoped save in app/routes.py
writes the request after SUCCESS.

Scope
  READS   the access record handed in by the route, the platform's role
          matrix, and the vendored team, audit and validation blocks.
  WRITES  its own result envelope only (app/routes.py persists).
  NEVER   the tenant store, the network, or another capability's state.

Domain rule: a role may not widen its own scope -- a technician
asks for assigned jobs, management holds the portfolio, and a
request for anything wider is reported as refused.
"""

from __future__ import annotations

from typing import Any, Dict

from app import formulas
from app.dispatch import execute

PRODUCT_NAME = "Facility Management Platform for Schools"
CAPABILITY_ID = "role_based_access"
ENTITY = "role_based_access"
BLOCK_IDS = ['team', 'audit', 'validation']
#: Each block's declared default action (block.json / Store registry map).
#: Blocks are action-dispatched; execute() with action=None is answered
#: "Unknown action: None". Passed as a keyword, never inside the payload.
BLOCK_DEFAULT_ACTIONS = {'team': 'get_team_context', 'audit': 'log', 'validation': 'validate_pipeline'}
#: This capability's own domain columns. The kernel strips trust-scope keys
#: from caller arguments, so the domain columns are declared here.
CAPABILITY_FIELDS = ['reference', 'status', 'principal', 'principal_email', 'role', 'school', 'access_scope', 'permissions', 'granted_by', 'effective_from', 'last_review_at', 'active', 'notes']

_REQUIRED_FIELDS = ['reference', 'status', 'principal', 'role', 'school', 'access_scope']


#: The permission matrix the platform enforces. Management sees the whole
#: estate; field staff see the jobs assigned to them; complainants see
#: only what they raised. This is data so it can be reviewed and changed.
PERMISSIONS_BY_ROLE = {
    "management": [
        "portfolio:read", "school:read", "complaint:read", "complaint:write",
        "complaint:assign", "team:read", "team:write", "report:read",
        "access:grant",
    ],
    "admin": [
        "portfolio:read", "school:read", "complaint:read", "complaint:write",
        "team:read", "team:write", "report:read", "access:grant",
        "access:revoke",
    ],
    "technician": [
        "complaint:read", "complaint:update", "job:read", "job:update",
    ],
    "cleaner": [
        "complaint:read", "complaint:update", "job:read", "job:update",
    ],
    "school_staff": ["complaint:read", "complaint:create", "school:read"],
    "complainant": ["complaint:create", "complaint:read"],
}

#: The access scope each role resolves to. A role may not widen its own.
SCOPE_BY_ROLE = {
    "management": "portfolio",
    "admin": "portfolio",
    "technician": "assigned_jobs",
    "cleaner": "assigned_jobs",
    "school_staff": "school",
    "complainant": "own_complaints",
}


def _grant(record):
    """The effective permission set for one principal."""
    role = str(record.get("role") or "complainant").lower()
    declared = PERMISSIONS_BY_ROLE.get(role)
    out = {
        "principal": str(record.get("principal") or ""),
        "role": role,
        "school": str(record.get("school") or ""),
        "access_scope": SCOPE_BY_ROLE.get(
            role, str(record.get("access_scope") or "own_complaints")),
        "known_role": declared is not None,
    }
    if declared is None:
        out["permissions"] = []
        out["refused"] = "unknown role: %s" % role
        return out
    requested = str(record.get("access_scope") or "").strip()
    if requested and requested != out["access_scope"]:
        # management keeps portfolio scope; everyone else is narrowed to
        # the scope their role grants, never widened by the request.
        out["scope_refused"] = (
            "requested %s but role %s resolves to %s"
            % (requested, role, out["access_scope"])
        )
    out["permissions"] = list(declared)
    out["active"] = record.get("active") is not False
    return out


def _platform_side(record, unavailable):
    """The resolved grant and the audit trail entry for it."""
    grant = _grant(record)
    return {
        "grant": grant,
        "audit_entry": {
            "principal": grant["principal"],
            "role": grant["role"],
            "permissions": grant["permissions"],
            "scope": grant["access_scope"],
            "granted_by": str(record.get("granted_by") or "management"),
        },
        "blocks_unavailable": sorted(unavailable),
    }
def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve and record role-based access for one principal."""
    import app.dispatch as _dispatch
    from app.block_feed import block_input as _block_input
    from app.block_inputs import default_block_action as _default_block_action
    from app.block_inputs import prepare_block_input as _prepare_block_input
    from app.block_inputs import split_execute_action as _split_execute_action
    from app.vendor_compat import unavailable_reason as _unavailable_reason

    # Reads the caller's record; writes one result envelope. The stored row
    # is the request the ROUTE persists, never this handler's answer.
    results: Dict[str, Any] = {}
    block_errors: Dict[str, str] = {}
    unavailable: Dict[str, str] = {}


    def _invoke(block_id, data, action=None):
        resolved, record = _split_execute_action(
            data, action=action,
            default_action=_default_block_action(block_id, BLOCK_DEFAULT_ACTIONS))
        prepared = _prepare_block_input(
            block_id, record, action=resolved, roster=BLOCK_IDS,
            product_name=PRODUCT_NAME, entity=ENTITY,
            default_actions=BLOCK_DEFAULT_ACTIONS)
        prepared = _block_input(CAPABILITY_ID, block_id, prepared, record,
                                _REQUIRED_FIELDS)
        try:
            answer = _dispatch.execute(block_id, prepared, action=resolved)
        except Exception as exc:  # a block that cannot load is named, never hidden
            unavailable[block_id] = ('%s: %s' % (type(exc).__name__, exc))[:300]
            return {'ok': False, 'block': block_id, 'invoked': True,
                    'unavailable': True, 'reason': unavailable[block_id]}
        if isinstance(answer, dict) and (
            str(answer.get('status') or '').lower() == 'error'
            or 'error' in answer
        ):
            reason = _unavailable_reason(block_id)
            if reason:
                # Invoked and the vendored source cannot load: named, not
                # fatal -- the platform's own module performs that step.
                unavailable[block_id] = reason[:300]
                return {'ok': False, 'block': block_id, 'invoked': True,
                        'unavailable': True, 'reason': unavailable[block_id]}
        return answer

    # The workflow block runs last: its steps are the prepared children and
    # the Store workflow 0-indexes them.
    ordered = [b for b in BLOCK_IDS if b != 'workflow'] + (
        ['workflow'] if 'workflow' in BLOCK_IDS else [])
    for block_id in ordered:
        data = dict(payload) if isinstance(payload, dict) else {}

        answer = _invoke(block_id, data)

        results[block_id] = answer
        if not isinstance(answer, dict):
            continue
        status = str(answer.get('status') or '').lower()
        if status in ('error', 'failed', 'partial') or 'error' in answer:
            block_errors[block_id] = str(answer.get('error') or status)[:200]
        elif block_id == 'validation' and answer.get('passed') is False:
            block_errors[block_id] = 'validation block reported passed=false'
        elif block_id == 'team' and answer.get('ok') is False:
            block_errors[block_id] = str(answer.get('error') or 'team refused')[:200]

    if block_errors:
        return {'ok': False, 'capability': CAPABILITY_ID,
                'error': '; '.join('%s: %s' % (b, e)
                                   for b, e in sorted(block_errors.items())),
                'results': results, 'unavailable_blocks': sorted(unavailable)}

    record = payload if isinstance(payload, dict) else {}
    return {'ok': True, 'capability': CAPABILITY_ID, 'results': results,
            'unavailable_blocks': sorted(unavailable),
            'platform': _platform_side(record, unavailable)}
