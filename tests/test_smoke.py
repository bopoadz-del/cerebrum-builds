"""The platform runs, and it runs without the store."""

import os

import pytest


def test_capabilities_import():
    from app.actions import branch_and_consolidated_operations
    assert branch_and_consolidated_operations.CAPABILITY_ID
    from app.actions import inventory_and_replenishment
    assert inventory_and_replenishment.CAPABILITY_ID
    from app.actions import branch_books_and_accounting
    assert branch_books_and_accounting.CAPABILITY_ID
    from app.actions import delivery_and_dispatch
    assert delivery_and_dispatch.CAPABILITY_ID
    from app.actions import order_follow_up
    assert order_follow_up.CAPABILITY_ID
    from app.actions import events_supply
    assert events_supply.CAPABILITY_ID
    from app.actions import document_grounded_knowledge
    assert document_grounded_knowledge.CAPABILITY_ID
    from app.actions import outlook_branch_messaging_integration
    assert outlook_branch_messaging_integration.CAPABILITY_ID


def test_dispatch_runs_offline():
    """No store env, no network: every block must LOAD and EXECUTE from
    vendor/. A block-level refusal of this bare probe is still local
    execution; an import failure is the store dependency this test
    exists to catch."""
    for var in ("CEREBRUM_API_URL", "CEREBRUM_API_KEY", "CEREBRUM_API_TOKEN"):
        os.environ.pop(var, None)
    from app.dispatch import execute, load_block
    for block_id in ['analytics', 'audit', 'capture', 'dashboard', 'database', 'document_engine', 'estate_maintenance', 'estate_registry', 'event_bus', 'formula_executor', 'knowledge', 'memory', 'notification', 'portfolio_rollup', 'queue', 'readiness_engine', 'recommendation_template', 'spec_analyzer', 'storage', 'team', 'validation', 'vector_search', 'workflow']:
        load_block(block_id)
    actions = {'analytics': 'track_event', 'audit': 'log', 'dashboard': 'render', 'database': 'query', 'estate_maintenance': 'create', 'estate_registry': 'create', 'event_bus': 'publish', 'knowledge': 'ask', 'memory': 'get', 'notification': 'send', 'portfolio_rollup': 'aggregate', 'queue': 'enqueue', 'readiness_engine': 'evaluate', 'storage': 'store', 'team': 'create_team', 'validation': 'validate_pipeline', 'workflow': 'run'}
    for block_id in ['analytics', 'audit', 'capture', 'dashboard', 'database', 'document_engine', 'estate_maintenance', 'estate_registry', 'event_bus', 'formula_executor', 'knowledge', 'memory', 'notification', 'portfolio_rollup', 'queue', 'readiness_engine', 'recommendation_template', 'spec_analyzer', 'storage', 'team', 'validation', 'vector_search', 'workflow']:
        try:
            result = execute(block_id, {}, action=actions.get(block_id))
        except RuntimeError as exc:
            # The block ran and refused the empty probe -- fine here;
            # the pilot test below demands Store-backed success.
            # An import error is never fine.
            assert "No module named" not in str(exc), (block_id, exc)
            assert "cannot import" not in str(exc), (block_id, exc)
        else:
            assert isinstance(result, dict), block_id


def test_kit_packs_present():
    """The download is a product tree: kits/ next to vendor/blocks."""
    from pathlib import Path as _Path
    kits = _Path(__file__).resolve().parents[1] / "kits"
    assert kits.is_dir(), "kits/ missing from the delivered platform"
    assert list(kits.glob("*/manifest.json")), "no kit pack manifests"


def test_every_capability_handle_returns_mapping():
    """Code-phase: the coder wired handle() and it returns a dict.
    Store ok: False or a Store exception is not this gate."""
    for var in ("CEREBRUM_API_URL", "CEREBRUM_API_KEY"):
        os.environ.pop(var, None)
    failures = []
    from app.actions import branch_and_consolidated_operations
    try:
        out = branch_and_consolidated_operations.handle({'branch': 'sample', 'reference': 'sample', 'role_view': 'sample', 'status': 'open', 'view_scope': 'sample', 'period': 'sample', 'metrics_summary': 'sample', 'notes': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('branch_and_consolidated_operations handle() must return a dict, got ' + type(out).__name__)
    from app.actions import inventory_and_replenishment
    try:
        out = inventory_and_replenishment.handle({'branch': 'sample', 'item_name': 'sample', 'item_type': 'ingredient', 'reference': 'sample', 'status': 'open', 'quantity_on_hand': 'sample', 'reorder_threshold': 'sample', 'unit': 'sample', 'supplier': 'sample', 'transfer_to_branch': 'sample', 'low_stock': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('inventory_and_replenishment handle() must return a dict, got ' + type(out).__name__)
    from app.actions import branch_books_and_accounting
    try:
        out = branch_books_and_accounting.handle({'branch': 'sample', 'entry_type': 'sale', 'reference': 'sample', 'status': 'open', 'entry_date': '2026-09-03', 'amount': 'sample', 'margin_percent': 'sample', 'ingredient': 'sample', 'notes': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('branch_books_and_accounting handle() must return a dict, got ' + type(out).__name__)
    from app.actions import delivery_and_dispatch
    try:
        out = delivery_and_dispatch.handle({'branch': 'sample', 'driver': 'sample', 'reference': 'sample', 'status': 'open', 'vehicle_type': 'car', 'vehicle_code': 'id-1', 'delivery_zone': 'sample', 'route': 'sample', 'order_reference': 'sample', 'proof_of_delivery': 'sample', 'scheduled_at': '2026-09-03T10:00:00'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('delivery_and_dispatch handle() must return a dict, got ' + type(out).__name__)
    from app.actions import order_follow_up
    try:
        out = order_follow_up.handle({'branch': 'sample', 'channel': 'email', 'customer_name': 'sample', 'reference': 'sample', 'status': 'open', 'order_status': 'open', 'payment_status': 'unpaid', 'confirmed': 'sample', 'due_at': '2026-09-03T10:00:00', 'follow_up_note': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('order_follow_up handle() must return a dict, got ' + type(out).__name__)
    from app.actions import events_supply
    try:
        out = events_supply.handle({'branch': 'sample', 'event_name': 'sample', 'reference': 'sample', 'status': 'open', 'event_date': '2026-09-03', 'guest_count': 1, 'deposit_amount': 'sample', 'delivery_time': '10:00:00', 'venue': 'sample', 'contact_email': 'guest@example.com'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('events_supply handle() must return a dict, got ' + type(out).__name__)
    from app.actions import document_grounded_knowledge
    try:
        out = document_grounded_knowledge.handle({'branch': 'sample', 'document_type': 'price_list', 'question': 'sample', 'reference': 'sample', 'status': 'open', 'answer': 'sample', 'citations': 'sample', 'confidence': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('document_grounded_knowledge handle() must return a dict, got ' + type(out).__name__)
    from app.actions import outlook_branch_messaging_integration
    try:
        out = outlook_branch_messaging_integration.handle({'branch': 'sample', 'direction': 'inbound', 'mailbox': 'sample', 'reference': 'sample', 'status': 'open', 'subject': 'sample', 'body': 'sample', 'message_reference': 'sample', 'received_at': '2026-09-03T10:00:00'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('outlook_branch_messaging_integration handle() must return a dict, got ' + type(out).__name__)
    assert not failures, "; ".join(failures)


@pytest.mark.pilot
def test_every_capability_executes_end_to_end():
    """Pilot: each handler runs its blocks on a spec payload and
    Store must accept it. Not the factory code-phase gate."""
    for var in ("CEREBRUM_API_URL", "CEREBRUM_API_KEY"):
        os.environ.pop(var, None)
    import json as _json
    failures = []
    from app.actions import branch_and_consolidated_operations
    out = branch_and_consolidated_operations.handle({'branch': 'sample', 'reference': 'sample', 'role_view': 'sample', 'status': 'open', 'view_scope': 'sample', 'period': 'sample', 'metrics_summary': 'sample', 'notes': 'sample'})
    if not isinstance(out, dict):
        failures.append('branch_and_consolidated_operations returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('branch_and_consolidated_operations rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('branch_and_consolidated_operations reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import inventory_and_replenishment
    out = inventory_and_replenishment.handle({'branch': 'sample', 'item_name': 'sample', 'item_type': 'ingredient', 'reference': 'sample', 'status': 'open', 'quantity_on_hand': 'sample', 'reorder_threshold': 'sample', 'unit': 'sample', 'supplier': 'sample', 'transfer_to_branch': 'sample', 'low_stock': 'sample'})
    if not isinstance(out, dict):
        failures.append('inventory_and_replenishment returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('inventory_and_replenishment rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('inventory_and_replenishment reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import branch_books_and_accounting
    out = branch_books_and_accounting.handle({'branch': 'sample', 'entry_type': 'sale', 'reference': 'sample', 'status': 'open', 'entry_date': '2026-09-03', 'amount': 'sample', 'margin_percent': 'sample', 'ingredient': 'sample', 'notes': 'sample'})
    if not isinstance(out, dict):
        failures.append('branch_books_and_accounting returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('branch_books_and_accounting rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('branch_books_and_accounting reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import delivery_and_dispatch
    out = delivery_and_dispatch.handle({'branch': 'sample', 'driver': 'sample', 'reference': 'sample', 'status': 'open', 'vehicle_type': 'car', 'vehicle_code': 'id-1', 'delivery_zone': 'sample', 'route': 'sample', 'order_reference': 'sample', 'proof_of_delivery': 'sample', 'scheduled_at': '2026-09-03T10:00:00'})
    if not isinstance(out, dict):
        failures.append('delivery_and_dispatch returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('delivery_and_dispatch rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('delivery_and_dispatch reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import order_follow_up
    out = order_follow_up.handle({'branch': 'sample', 'channel': 'email', 'customer_name': 'sample', 'reference': 'sample', 'status': 'open', 'order_status': 'open', 'payment_status': 'unpaid', 'confirmed': 'sample', 'due_at': '2026-09-03T10:00:00', 'follow_up_note': 'sample'})
    if not isinstance(out, dict):
        failures.append('order_follow_up returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('order_follow_up rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('order_follow_up reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import events_supply
    out = events_supply.handle({'branch': 'sample', 'event_name': 'sample', 'reference': 'sample', 'status': 'open', 'event_date': '2026-09-03', 'guest_count': 1, 'deposit_amount': 'sample', 'delivery_time': '10:00:00', 'venue': 'sample', 'contact_email': 'guest@example.com'})
    if not isinstance(out, dict):
        failures.append('events_supply returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('events_supply rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('events_supply reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import document_grounded_knowledge
    out = document_grounded_knowledge.handle({'branch': 'sample', 'document_type': 'price_list', 'question': 'sample', 'reference': 'sample', 'status': 'open', 'answer': 'sample', 'citations': 'sample', 'confidence': 'sample'})
    if not isinstance(out, dict):
        failures.append('document_grounded_knowledge returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('document_grounded_knowledge rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('document_grounded_knowledge reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import outlook_branch_messaging_integration
    out = outlook_branch_messaging_integration.handle({'branch': 'sample', 'direction': 'inbound', 'mailbox': 'sample', 'reference': 'sample', 'status': 'open', 'subject': 'sample', 'body': 'sample', 'message_reference': 'sample', 'received_at': '2026-09-03T10:00:00'})
    if not isinstance(out, dict):
        failures.append('outlook_branch_messaging_integration returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('outlook_branch_messaging_integration rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('outlook_branch_messaging_integration reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    assert not failures, "; ".join(failures)
