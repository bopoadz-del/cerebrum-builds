"""Handler for capability management_dashboards.

Written by the factory WRITER role (codewhale exec)
Authored by the coding agent (codewhale exec) under the factory WRITER role.

Management sees complaints, jobs and status per site and across the
estate of ten schools. This module builds the dashboard's rows and
computes its compliance figure from the record's own numbers before
handing them to the vendored dashboard, analytics and rollup blocks.
Persistence is route-scoped: the tenant-scoped save in app/routes.py
writes the request after SUCCESS.

Scope
  READS   the dashboard record handed in by the route, the estate school
          list, app.formulas, and the vendored block contracts.
  WRITES  its own result envelope only (app/routes.py persists).
  NEVER   the tenant store, the network, or another capability's state.

Domain rule: a portfolio record covers all ten schools and a
per-site record covers one; the platform never reports a portfolio
figure it cannot derive from the record it was given.
"""

from __future__ import annotations

from typing import Any, Dict

from app import formulas
from app.dispatch import execute

PRODUCT_NAME = "Facility Management Platform for Schools"
CAPABILITY_ID = "management_dashboards"
ENTITY = "management_dashboards"
BLOCK_IDS = ['dashboard', 'analytics', 'portfolio_rollup']
#: Each block's declared default action (block.json / Store registry map).
#: Blocks are action-dispatched; execute() with action=None is answered
#: "Unknown action: None". Passed as a keyword, never inside the payload.
BLOCK_DEFAULT_ACTIONS = {'dashboard': 'render', 'analytics': 'track_event', 'portfolio_rollup': 'aggregate'}
#: This capability's own domain columns. The kernel strips trust-scope keys
#: from caller arguments, so the domain columns are declared here.
CAPABILITY_FIELDS = ['reference', 'status', 'scope', 'school', 'period', 'complaints_open', 'complaints_in_progress', 'complaints_closed', 'jobs_in_progress', 'sla_breaches', 'sla_compliance_pct', 'avg_closure_hours', 'headline', 'generated_at']

_REQUIRED_FIELDS = ['reference', 'status', 'scope', 'school', 'period', 'complaints_open']


#: The schools this estate covers. Management oversight is per-site and
#: portfolio-wide, so the platform names the sites rather than counting a
#: number it cannot check.
SCHOOLS = (
    "al-barsha-primary",
    "al-quoz-secondary",
    "deira-primary",
    "jumeirah-primary",
    "karama-secondary",
    "mirdif-primary",
    "nad-al-shema-secondary",
    "silicon-oasis-primary",
    "the-gardens-primary",
    "warqa-secondary",
)


def _school_rows(record):
    """Per-school rows the dashboard renders and the rollup sums.

    A per-site record reports its own school; a portfolio record reports
    the whole estate, so the estate headcount is used for the per-school
    average rather than a figure the block cannot check.
    """
    scope = str(record.get("scope") or "school").lower()
    school = str(record.get("school") or "estate")
    if scope == "portfolio" and school == "estate":
        return [{"id": name, "value": 1.0, "status": "open"} for name in SCHOOLS]
    return [{"id": school, "value": 1.0, "status": str(record.get("status") or "open")}]


def _snapshot(record):
    """The dashboard's own numbers, with compliance computed not guessed."""
    open_count = record.get("complaints_open")
    closed = record.get("complaints_closed")
    breaches = record.get("sla_breaches")
    out = {
        "scope": str(record.get("scope") or "school"),
        "school": str(record.get("school") or ""),
        "period": str(record.get("period") or ""),
        "complaints_open": open_count,
        "complaints_closed": closed,
        "sla_breaches": breaches,
    }
    try:
        total = formulas.to_number(open_count, "complaints_open") + formulas.to_number(
            closed or 0, "complaints_closed"
        )
        if total > 0:
            out["sla_compliance_pct"] = formulas.sla_compliance_pct(
                within_target=max(0.0, total - formulas.to_number(breaches or 0, "sla_breaches")),
                total=total,
            )
    except formulas.FormulaError as exc:
        out["compliance_error"] = str(exc)
    try:
        out["estate_schools"] = formulas.estate_total(schools=list(SCHOOLS))
    except formulas.FormulaError as exc:
        out["estate_error"] = str(exc)
    return out


def _platform_side(record, unavailable):
    """The rendered dashboard, its rollup rows and the headline."""
    snapshot = _snapshot(record)
    headline = "%s %s: %s open, %s closed, %s breach(es)" % (
        snapshot["scope"], snapshot["school"], snapshot["complaints_open"],
        snapshot["complaints_closed"], snapshot["sla_breaches"])
    return {
        "snapshot": snapshot,
        "headline": headline,
        "rows": _school_rows(record),
        "blocks_unavailable": sorted(unavailable),
    }
def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Per-site and portfolio dashboards across the ten-school estate."""
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
