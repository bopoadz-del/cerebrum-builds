"""Handler for capability erp_integration.

Written by the factory WRITER role (codewhale exec)
Authored by the coding agent (codewhale exec) under the factory WRITER role.

The customer's existing ERP is named but no connector is attachable
today, so this capability ships as a marked placeholder: it records
what would be exchanged, publishes the exchange event on the local
event bus, and refuses to report a sync that never happened. The
workflow's event_bus child is prepared in source. Persistence is
route-scoped: the tenant-scoped save in app/routes.py writes the
request after SUCCESS.

Scope
  READS   the exchange record handed in by the route, app.formulas (amounts
          and the AED currency the brief names), and the vendored
          workflow, event_bus and validation blocks.
  WRITES  its own result envelope only (app/routes.py persists).
  NEVER   the tenant store, the network, or another capability's state.

Honesty rule: this integration is NOT implemented. Every answer
carries mode=placeholder and sync_state=not_implemented, and the
platform never claims an ERP exchange it did not perform.
"""

from __future__ import annotations

from typing import Any, Dict

from app import formulas
from app.dispatch import execute

PRODUCT_NAME = "Facility Management Platform for Schools"
CAPABILITY_ID = "erp_integration"
ENTITY = "erp_integration"
BLOCK_IDS = ['workflow', 'event_bus', 'validation']
#: Each block's declared default action (block.json / Store registry map).
#: Blocks are action-dispatched; execute() with action=None is answered
#: "Unknown action: None". Passed as a keyword, never inside the payload.
BLOCK_DEFAULT_ACTIONS = {'workflow': 'run', 'event_bus': 'publish', 'validation': 'validate_pipeline'}
#: This capability's own domain columns. The kernel strips trust-scope keys
#: from caller arguments, so the domain columns are declared here.
CAPABILITY_FIELDS = ['reference', 'status', 'integration', 'mode', 'entity_type', 'direction', 'external_reference', 'endpoint', 'currency', 'amount', 'sync_state', 'last_sync_at', 'detail', 'notes']

_REQUIRED_FIELDS = ['reference', 'status', 'integration', 'mode', 'entity_type', 'direction']


#: ERP surfaces this platform would exchange with the customer's ERP. No
#: connector is attachable today, so every one of them is a marked
#: placeholder: the platform records the intent and says so, and never
#: claims a sync that did not happen.
ERP_ENTITIES = (
    "purchase_order",
    "invoice",
    "vendor",
    "staff_roster",
    "asset",
)

PLACEHOLDER_MARKER = "PLACEHOLDER: no ERP connector is attached"


def _handshake(record):
    """What the ERP exchange would carry, and what it honestly is."""
    entity_type = str(record.get("entity_type") or "purchase_order")
    direction = str(record.get("direction") or "outbound")
    out = {
        "integration": "erp",
        "mode": "placeholder",
        "entity_type": entity_type,
        "direction": direction,
        "known_entity": entity_type in ERP_ENTITIES,
        "endpoint": str(record.get("endpoint") or ""),
        "external_reference": str(record.get("external_reference") or ""),
        "sync_state": "not_implemented",
        "marker": PLACEHOLDER_MARKER,
    }
    amount = record.get("amount")
    if amount not in (None, ""):
        try:
            out["amount"] = formulas.to_number(amount, "amount")
            out["currency"] = str(record.get("currency") or formulas.CURRENCY)
        except formulas.FormulaError as exc:
            out["amount_error"] = str(exc)
    if not out["known_entity"]:
        out["refused"] = "unknown ERP entity: %s" % entity_type
    return out


def _platform_side(record, unavailable):
    """The placeholder exchange record and its declared honesty."""
    handshake = _handshake(record)
    return {
        "exchange": handshake,
        "implemented": False,
        "honesty": (
            "ERP integration ships as a marked placeholder: the platform "
            "records what would be exchanged and refuses to report a sync "
            "that no connector performed"
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
            "topic": "erp_integration.%s" % (
                payload.get("reference") if isinstance(payload, dict) else "record"
            ),
            "payload": {
                "reference": (payload.get("reference")
                              if isinstance(payload, dict) else None) or "record",
                "entity_type": (payload.get("entity_type")
                                if isinstance(payload, dict) else None) or "purchase_order",
                "direction": (payload.get("direction")
                              if isinstance(payload, dict) else None) or "outbound",
                "sync_state": "not_implemented",
            },
            "message": "erp_integration exchange recorded as a marked placeholder",
            "channel": "mcp",
            "tool": "event_bus",
        },
    }]
def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Record a marked-placeholder ERP exchange and publish its event."""
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
            "topic": "erp_integration.%s" % (
                payload.get("reference") if isinstance(payload, dict) else "record"
            ),
            "payload": {
                "reference": (payload.get("reference")
                              if isinstance(payload, dict) else None) or "record",
                "entity_type": (payload.get("entity_type")
                                if isinstance(payload, dict) else None) or "purchase_order",
                "direction": (payload.get("direction")
                              if isinstance(payload, dict) else None) or "outbound",
                "sync_state": "not_implemented",
            },
            "message": "erp_integration exchange recorded as a marked placeholder",
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
