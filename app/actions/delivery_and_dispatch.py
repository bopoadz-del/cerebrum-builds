"""Handler for capability delivery_and_dispatch.

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

CAPABILITY_ID = "delivery_and_dispatch"
ENTITY = 'delivery_and_dispatch'
BLOCK_IDS = ['workflow', 'queue', 'notification', 'capture', 'estate_maintenance', 'database', 'analytics']
#: Each block's declared default action (block.json / Store registry map).
#: Blocks are action-dispatched; execute() with action=None is answered
#: "Unknown action: None".
BLOCK_DEFAULT_ACTIONS = {'workflow': 'run', 'queue': 'enqueue', 'notification': 'send', 'capture': 'extract', 'estate_maintenance': 'create', 'database': 'query', 'analytics': 'track_event'}
#: This capability's own domain columns. The kernel strips trust-scope keys
#: from caller arguments, so the domain columns are declared here.
CAPABILITY_FIELDS = ['reference', 'status', 'branch', 'driver', 'vehicle_type', 'vehicle_code', 'delivery_zone', 'route', 'order_reference', 'proof_of_delivery', 'scheduled_at']


_REQUIRED_FIELDS = ['reference', 'status', 'branch', 'driver', 'vehicle_type']
FLEET = {'car': 2, 'bike': 10}



def _dispatch_plan(record):
    """Vehicle allocation and zone/route handling for one run."""
    from app import formulas

    vehicle = str(record.get('vehicle_type') or 'bike')
    capacity = formulas.delivery_capacity()
    return {
        'driver': str(record.get('driver') or ''),
        'vehicle_type': vehicle,
        'vehicle_code': str(record.get('vehicle_code') or '%s-1' % vehicle),
        'delivery_zone': str(record.get('delivery_zone') or 'unzoned'),
        'route': str(record.get('route') or 'unrouted'),
        'fleet_capacity': capacity,
        'vehicle_available': int(FLEET.get(vehicle, 0)) > 0,
        'scheduled_at': str(record.get('scheduled_at') or ''),
    }


def _platform_side(record, unavailable):
    """Dispatch assignment, status update, and proof-of-delivery capture."""
    plan = _dispatch_plan(record)
    notification = None
    try:
        from app import notifications

        notification = notifications.deliver(
            branch=str(record.get('branch') or ''),
            subject='dispatch: %s' % plan['vehicle_code'],
            message=('%s assigned %s (%s -> %s)' % (
                plan['driver'], plan['vehicle_code'], plan['route'], plan['delivery_zone'])),
            channel='mcp',
            record=record,
        )
    except Exception as exc:  # noqa: BLE001 - the delivery record is still returned
        notification = {'error': '%s: %s' % (type(exc).__name__, exc)}
    return {'dispatch': plan, 'notification': notification,
            'proof_of_delivery': str(record.get('proof_of_delivery') or ''),
            'delivery_status': str(record.get('status') or 'open'),
            'blocks_unavailable': sorted(unavailable)}


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Driver and fleet dispatch across two cars and ten bikes, with zones and proof of delivery."""
    import app.dispatch as _dispatch
    from app.block_feed import block_input as _block_input
    from app.block_inputs import default_block_action as _default_block_action
    from app.block_inputs import prepare_block_input as _prepare_block_input
    from app.block_inputs import split_execute_action as _split_execute_action

    # Reads the dispatch record; writes one result envelope. Dispatch state is the route's to store.
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
