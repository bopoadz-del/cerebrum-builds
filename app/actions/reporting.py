"""Handler for capability reporting.

Written by the factory WRITER role (codewhale exec)
Authored by the coding agent (codewhale exec) under the factory WRITER role.

Scheduled and on-demand reporting on complaint volumes, closure
times and per-school performance. This module computes the report's
figures from the record it was given and evaluates them through the
platform's formula layer before delivery. Persistence is
route-scoped: the tenant-scoped save in app/routes.py writes the
request after SUCCESS.

Scope
  READS   the report record handed in by the route, app.formulas (volumes,
          closure time and per-school rate), and the vendored blocks.
  WRITES  its own result envelope only (app/routes.py persists).
  NEVER   the tenant store, the network, or another capability's state.

Domain rule: the estate carries ten schools, and a per-school rate
is computed against that estate size rather than a figure the
report invents.
"""

from __future__ import annotations

from typing import Any, Dict

from app import formulas
from app.dispatch import execute

PRODUCT_NAME = "Facility Management Platform for Schools"
CAPABILITY_ID = "reporting"
ENTITY = "reporting"
BLOCK_IDS = ['analytics', 'portfolio_rollup', 'formula_executor', 'notification']
#: Each block's declared default action (block.json / Store registry map).
#: Blocks are action-dispatched; execute() with action=None is answered
#: "Unknown action: None". Passed as a keyword, never inside the payload.
BLOCK_DEFAULT_ACTIONS = {'analytics': 'track_event', 'portfolio_rollup': 'aggregate', 'formula_executor': 'execute', 'notification': 'send'}
#: This capability's own domain columns. The kernel strips trust-scope keys
#: from caller arguments, so the domain columns are declared here.
CAPABILITY_FIELDS = ['reference', 'status', 'report_type', 'scope', 'school', 'period_start', 'period_end', 'complaints_total', 'closed_total', 'avg_closure_hours', 'sla_compliance_pct', 'top_category', 'busiest_school', 'recipients', 'generated_at']

_REQUIRED_FIELDS = ['reference', 'status', 'report_type', 'scope', 'school', 'period_start', 'period_end', 'complaints_total']


def _report(record):
    """The report's own figures: volume, closure time and compliance."""
    out = {
        "report_type": str(record.get("report_type") or "on_demand"),
        "scope": str(record.get("scope") or "school"),
        "school": str(record.get("school") or ""),
        "period_start": str(record.get("period_start") or ""),
        "period_end": str(record.get("period_end") or ""),
        "complaints_total": record.get("complaints_total"),
        "closed_total": record.get("closed_total"),
    }
    try:
        total = formulas.to_number(record.get("complaints_total"),
                                   "complaints_total")
    except formulas.FormulaError as exc:
        out["total_error"] = str(exc)
        return out
    try:
        closed = formulas.to_number(record.get("closed_total") or 0,
                                    "closed_total")
        out["open_total"] = round(max(0.0, total - closed), 4)
        if closed > 0:
            out["closure_share_pct"] = round((closed / total) * 100.0, 4) if total else 0.0
    except formulas.FormulaError as exc:
        out["closed_error"] = str(exc)
    hours = record.get("avg_closure_hours")
    if hours not in (None, ""):
        try:
            out["avg_closure_hours"] = formulas.to_number(
                hours, "avg_closure_hours")
        except formulas.FormulaError as exc:
            out["hours_error"] = str(exc)
    try:
        out["complaints_per_school"] = formulas.complaint_rate_per_school(
            complaints=total, schools=formulas.estate_total(
                schools=list(range(10))))
    except formulas.FormulaError as exc:
        out["rate_error"] = str(exc)
    return out


def _platform_side(record, unavailable):
    """The report body and the delivery of it to its audience."""
    body = _report(record)
    delivered = None
    try:
        from app import notifications

        delivered = notifications.deliver(
            school=body["school"] or "estate",
            subject="%s report %s..%s" % (
                body["report_type"], body["period_start"], body["period_end"]),
            message="%s complaints, %s closed, %s per school" % (
                body["complaints_total"], body["closed_total"],
                body.get("complaints_per_school")),
            channel="mcp", record=record)
    except Exception as exc:  # noqa: BLE001
        delivered = {"error": "%s: %s" % (type(exc).__name__, exc)}
    return {
        "report": body,
        "delivery": delivered,
        "blocks_unavailable": sorted(unavailable),
    }
def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Produce an on-demand or scheduled estate report and deliver it."""
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
