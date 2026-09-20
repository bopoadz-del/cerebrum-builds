"""Handler for capability booking_system_integration.

Written by the factory WRITER role (codewhale exec)
Authored by the coding agent (codewhale exec) under the factory WRITER role.

The customer's existing booking system is named but no connector is
attachable today, so this capability ships as a marked placeholder:
it records the booking it would place, publishes the booking event
on the local event bus, and refuses to report a confirmation that no
connector received. The workflow's event_bus child is prepared in
source. Persistence is route-scoped: the tenant-scoped save in
app/routes.py writes the request after SUCCESS.

Scope
  READS   the booking record handed in by the route, app.formulas (slot
          length), and the vendored workflow, event_bus and
          validation blocks.
  WRITES  its own result envelope only (app/routes.py persists).
  NEVER   the tenant store, the network, or another capability's state.

Honesty rule: this integration is NOT implemented. Every answer
carries mode=placeholder and sync_state=not_implemented, and the
platform never claims a booking it did not place.
"""

from __future__ import annotations

from typing import Any, Dict

from app import formulas
from app.dispatch import execute

PRODUCT_NAME = "Facility Management Platform for Schools"
CAPABILITY_ID = "booking_system_integration"
ENTITY = "booking_system_integration"
BLOCK_IDS = ['workflow', 'event_bus', 'validation']
#: Each block's declared default action (block.json / Store registry map).
#: Blocks are action-dispatched; execute() with action=None is answered
#: "Unknown action: None". Passed as a keyword, never inside the payload.
BLOCK_DEFAULT_ACTIONS = {'workflow': 'run', 'event_bus': 'publish', 'validation': 'validate_pipeline'}
#: This capability's own domain columns. The kernel strips trust-scope keys
#: from caller arguments, so the domain columns are declared here.
CAPABILITY_FIELDS = ['reference', 'status', 'integration', 'mode', 'booking_reference', 'school', 'facility', 'slot_start', 'slot_end', 'requested_by', 'sync_state', 'last_sync_at', 'detail', 'notes']

_REQUIRED_FIELDS = ['reference', 'status', 'integration', 'mode', 'booking_reference', 'school', 'facility', 'slot_start']


PLACEHOLDER_MARKER = "PLACEHOLDER: no booking-system connector is attached"


def _handshake(record):
    """What the booking exchange would carry, and what it honestly is."""
    start = str(record.get("slot_start") or "")
    end = str(record.get("slot_end") or "")
    out = {
        "integration": "booking_system",
        "mode": "placeholder",
        "booking_reference": str(record.get("booking_reference") or ""),
        "school": str(record.get("school") or ""),
        "facility": str(record.get("facility") or ""),
        "slot_start": start,
        "slot_end": end,
        "sync_state": "not_implemented",
        "marker": PLACEHOLDER_MARKER,
    }
    if start and end:
        try:
            hours = formulas.closure_hours(reported_at=start, closed_at=end)
            out["slot_hours"] = hours
        except formulas.FormulaError as exc:
            out["slot_error"] = str(exc)
    return out


def _platform_side(record, unavailable):
    """The placeholder booking record and its declared honesty."""
    handshake = _handshake(record)
    return {
        "exchange": handshake,
        "implemented": False,
        "honesty": (
            "booking-system integration ships as a marked placeholder: the "
            "platform records the booking it would place and refuses to "
            "report a confirmation no connector received"
        ),
        "blocks_unavailable": sorted(unavailable),
    }


    # Every event_bus child is prepared in source: the Store workflow
    # 0-indexes children, so an unprepared step_0 fails as
    # "workflow: step_0 (event_bus): error". topic, a payload dict, a
    # message, channel=mcp and tool=event_bus are all present.
    steps = [{
        "block": "event_bus",
        "action": "publish",
        "params": {"action": "publish"},
        "input": {
            "topic": "booking_system_integration.%s" % (
                payload.get("booking_reference")
                if isinstance(payload, dict) else "booking"
            ),
            "payload": {
                "reference": (payload.get("reference")
                              if isinstance(payload, dict) else None) or "record",
                "booking_reference": (payload.get("booking_reference")
                                      if isinstance(payload, dict) else None) or "booking",
                "school": (payload.get("school")
                           if isinstance(payload, dict) else None) or "school",
                "sync_state": "not_implemented",
            },
            "message": "booking exchange recorded as a marked placeholder",
            "channel": "mcp",
            "tool": "event_bus",
        },
    }]
def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Record a marked-placeholder booking exchange and publish its event."""
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
    # Every event_bus child is prepared in source: the Store workflow
    # 0-indexes children, so an unprepared step_0 fails as
    # "workflow: step_0 (event_bus): error". topic, a payload dict, a
    # message, channel=mcp and tool=event_bus are all present.
    steps = [{
        "block": "event_bus",
        "action": "publish",
        "params": {"action": "publish"},
        "input": {
            "topic": "booking_system_integration.%s" % (
                payload.get("booking_reference")
                if isinstance(payload, dict) else "booking"
            ),
            "payload": {
                "reference": (payload.get("reference")
                              if isinstance(payload, dict) else None) or "record",
                "booking_reference": (payload.get("booking_reference")
                                      if isinstance(payload, dict) else None) or "booking",
                "school": (payload.get("school")
                           if isinstance(payload, dict) else None) or "school",
                "sync_state": "not_implemented",
            },
            "message": "booking exchange recorded as a marked placeholder",
            "channel": "mcp",
            "tool": "event_bus",
        },
    }]

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
        if block_id == 'workflow':
            data['steps'] = steps
            data['result'] = steps[0]['input']

        answer = _invoke(block_id, data)
        if block_id == 'event_bus':
            answer = _invoke('event_bus', steps[0]['input'])

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
