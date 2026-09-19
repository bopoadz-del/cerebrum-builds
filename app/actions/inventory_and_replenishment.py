"""Handler for capability inventory_and_replenishment.

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

CAPABILITY_ID = "inventory_and_replenishment"
ENTITY = 'inventory_and_replenishment'
BLOCK_IDS = ['database', 'analytics', 'notification', 'workflow', 'estate_registry', 'readiness_engine']
#: Each block's declared default action (block.json / Store registry map).
#: Blocks are action-dispatched; execute() with action=None is answered
#: "Unknown action: None".
BLOCK_DEFAULT_ACTIONS = {'database': 'query', 'analytics': 'track_event', 'notification': 'send', 'workflow': 'run', 'estate_registry': 'create', 'readiness_engine': 'evaluate'}
#: This capability's own domain columns. The kernel strips trust-scope keys
#: from caller arguments, so the domain columns are declared here.
CAPABILITY_FIELDS = ['reference', 'status', 'branch', 'item_name', 'item_type', 'quantity_on_hand', 'reorder_threshold', 'unit', 'supplier', 'transfer_to_branch', 'low_stock']


_REQUIRED_FIELDS = ['reference', 'status', 'branch', 'item_name', 'item_type']



def _replenishment_plan(record):
    """Reorder decision and transfer suggestion, computed from the record."""
    from app import formulas

    on_hand = record.get('quantity_on_hand')
    threshold = record.get('reorder_threshold')
    plan = {'item_name': str(record.get('item_name') or ''), 'branch': str(record.get('branch') or ''),
            'item_type': str(record.get('item_type') or 'ingredient')}
    if on_hand is None or threshold is None:
        plan['decision'] = 'insufficient_data'
        plan['note'] = 'quantity_on_hand and reorder_threshold are needed to decide a reorder'
        return plan
    try:
        needing = formulas.reorder_required(quantity_on_hand=on_hand, reorder_threshold=threshold)
    except formulas.FormulaError as exc:
        plan['decision'] = 'insufficient_data'
        plan['note'] = str(exc)
        return plan
    plan['decision'] = 'reorder' if needing else 'hold'
    plan['quantity_on_hand'] = on_hand
    plan['reorder_threshold'] = threshold
    plan['transfer_to_branch'] = str(record.get('transfer_to_branch') or '')
    plan['source'] = 'central-kitchen' if needing else ''
    return plan


def _platform_side(record, unavailable):
    """Low-stock alerting and the replenishment call, done by the platform."""
    plan = _replenishment_plan(record)
    alert = None
    if plan['decision'] == 'reorder':
        from app import notifications

        alert = notifications.deliver(
            branch=str(record.get('branch') or ''),
            subject='low stock: %s' % plan['item_name'],
            message=('reorder %s at %s (on hand %s, threshold %s)' % (
                plan['item_name'], plan['branch'], plan.get('quantity_on_hand'),
                plan.get('reorder_threshold'))),
            channel='mcp',
            record=record,
        )
    return {'replenishment': plan, 'alert': alert,
            'blocks_unavailable': sorted(unavailable)}


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Ingredient and finished-good stock, low-stock alerting, and branch transfers."""
    import app.dispatch as _dispatch
    from app.block_feed import block_input as _block_input
    from app.block_inputs import default_block_action as _default_block_action
    from app.block_inputs import prepare_block_input as _prepare_block_input
    from app.block_inputs import split_execute_action as _split_execute_action

    # Reads the stock record; writes one result envelope. The route persists.
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
