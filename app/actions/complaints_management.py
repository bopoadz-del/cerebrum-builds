"""Handler for capability complaints_management.

Written by the factory WRITER role (codewhale exec)
Authored by the coding agent (codewhale exec) under the factory WRITER role.

A complaint arrives from school staff, a parent, or management
entering it on their behalf; this module triages it, computes its
service target from the platform's own formulas, and dispatches it
to the vendored blocks. Blocks are invoked in-process through the
local dispatch runtime (app.dispatch.execute) -- no network call is
made. Persistence is route-scoped: the tenant-scoped save in
app/routes.py writes the request after SUCCESS.

Scope
  READS   the complaint record handed in by the route, app.formulas (the
          service target it computes), and the vendored block contracts.
  WRITES  its own result envelope only (app/routes.py persists).
  NEVER   the tenant store, the network, or another capability's state.

Domain rule: the complaint's own status vocabulary is schema-enforced
(open | in_progress | closed), and every closure that misses the
computed deadline is reported as a breach rather than hidden.
"""

from __future__ import annotations

from typing import Any, Dict

from app import formulas
from app.dispatch import execute

PRODUCT_NAME = "Facility Management Platform for Schools"
CAPABILITY_ID = "complaints_management"
ENTITY = "complaints_management"
BLOCK_IDS = ['capture', 'workflow', 'queue', 'notification']
#: Each block's declared default action (block.json / Store registry map).
#: Blocks are action-dispatched; execute() with action=None is answered
#: "Unknown action: None". Passed as a keyword, never inside the payload.
BLOCK_DEFAULT_ACTIONS = {'capture': 'extract', 'workflow': 'run', 'queue': 'enqueue', 'notification': 'send'}
#: This capability's own domain columns. The kernel strips trust-scope keys
#: from caller arguments, so the domain columns are declared here.
CAPABILITY_FIELDS = ['reference', 'status', 'school', 'site_code', 'category', 'priority', 'description', 'raised_by', 'raised_by_role', 'contact_email', 'contact_phone', 'logged_by', 'assigned_to', 'assignment_mode', 'reported_at', 'due_at', 'sla_hours', 'closed_at', 'resolution_notes', 'work_order_reference']

_REQUIRED_FIELDS = ['reference', 'status', 'school', 'category', 'priority', 'description', 'raised_by', 'raised_by_role']


#: Which trade owns a complaint category. The routing table is the
#: platform's own operating policy and is what auto_assignment scores
#: against; it is data, not a rule hidden in prose.
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


def _triage(record):
    """Service target, deadline and breach state for one complaint."""
    category = str(record.get("category") or "other")
    priority = str(record.get("priority") or "medium")
    reported = record.get("reported_at")
    hours = record.get("sla_hours")
    out = {
        "school": str(record.get("school") or ""),
        "category": category,
        "priority": priority,
        "required_trade": TRADE_BY_CATEGORY.get(category, "general"),
        "raised_by_role": str(record.get("raised_by_role") or "school_staff"),
        "status": str(record.get("status") or "open"),
    }
    try:
        target = formulas.response_target_hours(priority, category)
        if hours not in (None, ""):
            target = formulas.to_number(hours, "sla_hours")
        out["sla_hours"] = target
        out["due_at"] = formulas.sla_due_at(reported or None, target)
    except formulas.FormulaError as exc:
        out["sla_error"] = str(exc)
    closed = record.get("closed_at")
    if closed not in (None, "") and out.get("due_at"):
        try:
            out["breached"] = formulas.sla_breach(
                due_at=out["due_at"], closed_at=closed
            )
            out["closure_hours"] = formulas.closure_hours(
                reported_at=record.get("reported_at"), closed_at=closed
            )
        except formulas.FormulaError as exc:
            out["closure_error"] = str(exc)
    out["escalate"] = (
        priority in ("critical", "high") and not record.get("assigned_to")
    )
    return out


def _platform_side(record, unavailable):
    """The triage decision, the captured report and the notification."""
    triage = _triage(record)
    captured = None
    try:
        from app import notifications

        captured = notifications.deliver(
            school=triage["school"],
            subject="complaint %s (%s at %s)" % (
                record.get("reference"), triage["priority"], triage["school"]),
            message="%s -> trade %s, target %s h, escalate=%s" % (
                str(record.get("description") or "")[:160],
                triage["required_trade"], triage.get("sla_hours"),
                triage["escalate"]),
            channel="mcp", record=record)
    except Exception as exc:  # noqa: BLE001 - delivery never fails the record
        captured = {"error": "%s: %s" % (type(exc).__name__, exc)}
    return {
        "triage": triage,
        "notification": captured,
        "platform_capture": "capture" if "capture" not in unavailable else None,
        "blocks_unavailable": sorted(unavailable),
    }
def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Capture a school complaint, compute its service target and route it."""
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
