"""Handler for capability workforce_management.

Written by the factory WRITER role (codewhale exec)
Authored by the coding agent (codewhale exec) under the factory WRITER role.

Technician and cleaner teams are organised per school. This module
records the team, computes its load against the platform's own
capacity setting, and flags a team that is carrying more than its
cap. Persistence is route-scoped: the tenant-scoped save in
app/routes.py writes the request after SUCCESS.

Scope
  READS   the team record handed in by the route, app.formulas (utilisation
          and workload), and the vendored block contracts.
  WRITES  its own result envelope only (app/routes.py persists).
  NEVER   the tenant store, the network, or another capability's state.

Domain rule: headcount and the jobs-per-member cap are the
operator's settings; the platform computes load from them and never
invents a capacity figure of its own.
"""

from __future__ import annotations

from typing import Any, Dict

from app import formulas
from app.dispatch import execute

PRODUCT_NAME = "Facility Management Platform for Schools"
CAPABILITY_ID = "workforce_management"
ENTITY = "workforce_management"
BLOCK_IDS = ['team', 'workflow', 'queue']
#: Each block's declared default action (block.json / Store registry map).
#: Blocks are action-dispatched; execute() with action=None is answered
#: "Unknown action: None". Passed as a keyword, never inside the payload.
BLOCK_DEFAULT_ACTIONS = {'team': 'get_team_context', 'workflow': 'run', 'queue': 'enqueue'}
#: This capability's own domain columns. The kernel strips trust-scope keys
#: from caller arguments, so the domain columns are declared here.
CAPABILITY_FIELDS = ['reference', 'status', 'school', 'team_name', 'team_type', 'trade', 'shift', 'headcount', 'lead_name', 'lead_email', 'contact_phone', 'active', 'open_jobs', 'notes']

_REQUIRED_FIELDS = ['reference', 'status', 'school', 'team_name', 'team_type', 'shift', 'headcount']


#: The platform's own cap on concurrent jobs per field-staff member. It is
#: a named operating setting, not a law of the domain.
JOBS_PER_MEMBER_CAP = 5


def _team_state(record):
    """Headcount, shift coverage and load for one school team."""
    headcount = record.get("headcount")
    open_jobs = record.get("open_jobs")
    out = {
        "school": str(record.get("school") or ""),
        "team_name": str(record.get("team_name") or ""),
        "team_type": str(record.get("team_type") or "technician"),
        "shift": str(record.get("shift") or "morning"),
        "active": record.get("active") is not False,
        "headcount": headcount,
    }
    try:
        members = formulas.to_number(headcount, "headcount")
    except formulas.FormulaError as exc:
        out["headcount_error"] = str(exc)
        return out
    jobs = 0
    if open_jobs not in (None, ""):
        try:
            jobs = formulas.to_number(open_jobs, "open_jobs")
        except formulas.FormulaError as exc:
            out["open_jobs_error"] = str(exc)
    try:
        out["utilisation_pct"] = formulas.utilisation_pct(
            open_jobs=jobs, headcount=members)
        out["workload_score"] = formulas.workload_score(
            open_jobs=jobs, headcount=members, cap=JOBS_PER_MEMBER_CAP)
    except formulas.FormulaError as exc:
        out["load_error"] = str(exc)
    out["capacity"] = round(members * JOBS_PER_MEMBER_CAP, 4)
    out["spare_capacity"] = round(
        max(0.0, members * JOBS_PER_MEMBER_CAP - jobs), 4
    )
    out["under_staffed"] = bool(
        out.get("workload_score") and out["workload_score"] > 80
    )
    return out


def _platform_side(record, unavailable):
    """The team's load picture and the audit entry for the change."""
    state = _team_state(record)
    delivered = None
    try:
        from app import notifications

        delivered = notifications.deliver(
            school=state["school"],
            subject="team %s (%s shift) headcount %s" % (
                state["team_name"], state["shift"], state["headcount"]),
            message="utilisation %s%%, spare capacity %s" % (
                state.get("utilisation_pct"), state.get("spare_capacity")),
            channel="mcp", record=record)
    except Exception as exc:  # noqa: BLE001
        delivered = {"error": "%s: %s" % (type(exc).__name__, exc)}
    return {
        "team_state": state,
        "notification": delivered,
        "platform_team": "team" if "team" not in unavailable else None,
        "blocks_unavailable": sorted(unavailable),
    }
def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Organise a technician or cleaner team per school and track its load."""
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
