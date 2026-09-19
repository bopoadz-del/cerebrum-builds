"""Handler for capability branch_books_and_accounting.

Written by the factory WRITER role (codewhale exec)

Bakery Branch Operations Platform. Blocks are invoked in-process through
the local dispatch runtime (app.dispatch.execute) -- this module makes no
network call. Persistence is route-scoped: the tenant-scoped save in
app/routes.py writes the request after SUCCESS. handle() is pure dispatch
and never touches the store.

Scope
  READS   the capability record handed in by the route, plus the vendored
          block contracts it feeds.
  WRITES  its own result envelope only (app/routes.py persists).
  NEVER   the tenant store, the filesystem, the network, or another
          capability's state.

A block that cannot be loaded from the sealed vendor tree is reported by
name in ``unavailable_blocks`` and the platform's own module performs that
step; a block that answers with an error fails the capability closed.

Authored by the coding agent (codewhale exec) under the factory WRITER role.
"""

from __future__ import annotations

from typing import Any, Dict

from app.dispatch import execute

CAPABILITY_ID = "branch_books_and_accounting"
ENTITY = 'branch_books_and_accounting'
BLOCK_IDS = ['database', 'formula_executor', 'analytics', 'portfolio_rollup', 'document_engine', 'validation']
#: Each block's declared default action (block.json / Store registry map).
#: Blocks are action-dispatched; execute() with action=None is answered
#: "Unknown action: None".
BLOCK_DEFAULT_ACTIONS = {'database': 'query', 'formula_executor': 'execute', 'analytics': 'track_event', 'portfolio_rollup': 'aggregate', 'document_engine': 'parse', 'validation': 'check_code_quality'}
#: This capability's own domain columns. The kernel strips trust-scope keys
#: from caller arguments, so the domain columns are declared here.
CAPABILITY_FIELDS = ['reference', 'status', 'branch', 'entry_type', 'entry_date', 'amount', 'margin_percent', 'ingredient', 'notes']


_REQUIRED_FIELDS = ['reference', 'status', 'branch', 'entry_type']




def _platform_side(record, unavailable):
    """Margin and daily-takings arithmetic, computed by the platform."""
    from app import formulas

    entry_type = str(record.get('entry_type') or 'sale')
    computed = {'entry_type': entry_type, 'branch': str(record.get('branch') or '')}
    if 'amount' in record:
        try:
            computed['takings'] = formulas.daily_takings([{**record, 'entry_type': entry_type}])
        except formulas.FormulaError as exc:
            computed['takings_error'] = str(exc)
    if 'amount' in record and 'margin_percent' in record:
        sale = record.get('amount')
        cost = record.get('cost')
        if cost is None:
            try:
                cost = float(sale) * (1.0 - float(record.get('margin_percent')) / 100.0)
            except (TypeError, ValueError):
                cost = None
        if cost is not None:
            try:
                computed['margin_percent'] = formulas.margin_percent(sale_price=sale, ingredient_cost=cost)
            except formulas.FormulaError as exc:
                computed['margin_error'] = str(exc)
    if str(record.get('ingredient') or ''):
        computed['price_list_entry'] = str(record.get('ingredient'))
    computed['blocks_unavailable'] = sorted(unavailable)
    return computed


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Sales, costs, price lists, margins, daily takings, and expense entries per branch."""
    import app.dispatch as _dispatch
    from app.block_feed import block_input as _block_input
    from app.block_inputs import default_block_action as _default_block_action
    from app.block_inputs import prepare_block_input as _prepare_block_input
    from app.block_inputs import split_execute_action as _split_execute_action

    # Reads the book entry; writes one result envelope. Margin arithmetic only, no ledger write.
    from app.vendor_compat import unavailable_reason as _unavailable_reason

    results: Dict[str, Any] = {}
    block_errors: Dict[str, str] = {}
    unavailable: Dict[str, str] = {}
    for block_id in BLOCK_IDS:
        reason = _unavailable_reason(block_id)
        if reason:
            unavailable[block_id] = reason
    live_roster = [b for b in BLOCK_IDS if b not in unavailable]

    def _invoke(block_id, data, action=None):
        resolved, record = _split_execute_action(
            data, action=action,
            default_action=_default_block_action(block_id, BLOCK_DEFAULT_ACTIONS))
        prepared = _prepare_block_input(
            block_id, record, action=resolved, roster=live_roster,
            entity=ENTITY, default_actions=BLOCK_DEFAULT_ACTIONS)
        prepared = _block_input(CAPABILITY_ID, block_id, prepared, record, _REQUIRED_FIELDS)
        try:
            return _dispatch.execute(block_id, prepared, action=resolved)
        except Exception as exc:  # a block that cannot load is named, never hidden
            unavailable[block_id] = ('%s: %s' % (type(exc).__name__, exc))[:300]
            return {'ok': False, 'block': block_id, 'unavailable': True,
                    'error': unavailable[block_id]}

    for block_id in BLOCK_IDS:
        if block_id in unavailable:
            # No block to call: the vendored module does not load. The
            # platform module for this concern runs instead, and the reason
            # is named in the response rather than hidden behind a success.
            results[block_id] = {'ok': False, 'block': block_id, 'invoked': False,
                                 'unavailable': True, 'error': unavailable[block_id]}
            continue
        answer = _invoke(block_id, payload)
        results[block_id] = answer
        if not isinstance(answer, dict):
            continue
        status = str(answer.get('status') or '').lower()
        if status in ('error', 'failed', 'partial') or 'error' in answer:
            block_errors[block_id] = str(answer.get('error') or status)[:200]
        elif block_id == 'validation' and answer.get('passed') is False:
            block_errors[block_id] = 'validation block reported passed=false'

    if block_errors:
        return {'ok': False, 'capability': CAPABILITY_ID,
                'error': '; '.join('%s: %s' % (b, e) for b, e in sorted(block_errors.items())),
                'results': results, 'unavailable_blocks': sorted(unavailable)}

    record = payload if isinstance(payload, dict) else {}
    return {'ok': True, 'capability': CAPABILITY_ID, 'results': results,
            'unavailable_blocks': sorted(unavailable),
            'platform': _platform_side(record, unavailable)}
