"""Handler for capability auto_assignment.

Written by the factory WRITER role (codewhale exec)
Authored by the coding agent (codewhale exec) under the factory WRITER role.

A complaint needs a field staff member. This module scores the
candidate against the complaint's trade, its school and current
workload using the platform's own formulas, and records whether the
routing was automatic or a management override. Persistence is
route-scoped: the tenant-scoped save in app/routes.py writes the
request after SUCCESS.

Scope
  READS   the routing record handed in by the route, app.formulas (match
          and workload scores), and the vendored block contracts.
  WRITES  its own result envelope only (app/routes.py persists).
  NEVER   the tenant store, the network, or another capability's state.

Domain rule: management may always override a routing, and the
override carries its reason; an override with no reason is reported
rather than silently accepted.
"""

from __future__ import annotations

from typing import Any, Dict

from app import formulas
from app.dispatch import execute

PRODUCT_NAME = "Facility Management Platform for Schools"
CAPABILITY_ID = "auto_assignment"
ENTITY = "auto_assignment"
BLOCK_IDS = ['workflow', 'queue', 'team', 'recommendation_template']
#: Each block's declared default action (block.json / Store registry map).
#: Blocks are action-dispatched; execute() with action=None is answered
#: "Unknown action: None". Passed as a keyword, never inside the payload.
BLOCK_DEFAULT_ACTIONS = {'workflow': 'run', 'queue': 'enqueue', 'team': 'get_team_context', 'recommendation_template': 'apply_template'}
#: This capability's own domain columns. The kernel strips trust-scope keys
#: from caller arguments, so the domain columns are declared here.
CAPABILITY_FIELDS = ['reference', 'status', 'complaint_reference', 'school', 'category', 'priority', 'required_trade', 'required_skill', 'candidate_count', 'assigned_to', 'assigned_role', 'assignment_mode', 'match_score', 'workload_score', 'queue_position', 'override_reason', 'assigned_at']

_REQUIRED_FIELDS = ['reference', 'status', 'complaint_reference', 'school', 'category', 'priority', 'required_trade', 'assignment_mode']


#: Trade a complaint category needs. The same table complaints_management
#: carries, so a complaint's category and a candidate's trade are compared
#: on one vocabulary.
TRADE_BY_CATEGORY = {
    "electrical": "electrical",
    "plumbing": "plumbing",
    "hvac": "hvac",
    "cleaning": "cleaning",
    "safety": "safety",
    "grounds": "grounds",
    "furniture": "carpentry",
    "it_av": "it_av",
    "pest_control": "pest_control",
    "other": "general",
}

#: Which field role a trade belongs to. Cleaners take the cleaning and
#: grounds work; technicians take the trades that need a certificate.
CLEANING_TRADES = frozenset({"cleaning", "grounds", "pest_control"})


def _route(record):
    """The routing decision: trade, role, workload and match score."""
    category = str(record.get("category") or "other")
    priority = str(record.get("priority") or "medium")
    trade = str(record.get("required_trade") or "") or TRADE_BY_CATEGORY.get(
        category, "general"
    )
    school = str(record.get("school") or "")
    candidate = str(record.get("assigned_to") or "")
    mode = str(record.get("assignment_mode") or "auto")
    workload = record.get("workload_score")
    if workload in (None, ""):
        workload = 0
    out = {
        "school": school,
        "trade": trade,
        "assigned_role": "cleaner" if trade in CLEANING_TRADES else "technician",
        "assignment_mode": mode,
        "candidate": candidate or None,
    }
    try:
        load = formulas.to_number(workload, "workload_score")
        out["workload_score"] = load
        out["match_score"] = formulas.match_score(
            trade_match=bool(candidate),
            skill_match=bool(str(record.get("required_skill") or "").strip()),
            same_school=bool(school),
            workload=load,
            priority=priority,
        )
    except formulas.FormulaError as exc:
        out["match_error"] = str(exc)
    if mode == "manual" and not str(record.get("override_reason") or "").strip():
        out["override_reason_required"] = True
    out["routed"] = bool(candidate) or mode == "unassigned"
    return out


def _platform_side(record, unavailable):
    """The routing decision plus who owns the job once it is routed."""
    routing = _route(record)
    owner = None
    try:
        from app import notifications

        owner = notifications.deliver(
            school=routing["school"],
            subject="job %s routed to %s" % (
                record.get("complaint_reference"), routing["candidate"] or "queue"),
            message="%s / %s -> %s (match %s)" % (
                routing["trade"], routing["assignment_mode"],
                routing["assigned_role"], routing.get("match_score")),
            channel="mcp", record=record)
    except Exception as exc:  # noqa: BLE001
        owner = {"error": "%s: %s" % (type(exc).__name__, exc)}
    return {
        "routing": routing,
        "notification": owner,
        "platform_queue": "queue" if "queue" not in unavailable else None,
        "blocks_unavailable": sorted(unavailable),
    }
def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Auto-assign a complaint to the right technician or cleaner."""
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
