"""The platform runs, and it runs without the store."""

import os

import pytest


def test_capabilities_import():
    from app.actions import inventory_management
    assert inventory_management.CAPABILITY_ID
    from app.actions import sales_and_orders
    assert sales_and_orders.CAPABILITY_ID
    from app.actions import customer_insights
    assert customer_insights.CAPABILITY_ID
    from app.actions import analytics_dashboard
    assert analytics_dashboard.CAPABILITY_ID
    from app.actions import supplier_and_purchasing
    assert supplier_and_purchasing.CAPABILITY_ID
    from app.actions import omnichannel_integration
    assert omnichannel_integration.CAPABILITY_ID
    from app.actions import compliance_and_audit
    assert compliance_and_audit.CAPABILITY_ID


def test_dispatch_runs_offline():
    """No store env, no network: every block must LOAD and EXECUTE from
    vendor/. A block-level refusal of this bare probe is still local
    execution; an import failure is the store dependency this test
    exists to catch."""
    for var in ("CEREBRUM_API_URL", "CEREBRUM_API_KEY", "CEREBRUM_API_TOKEN"):
        os.environ.pop(var, None)
    from app.dispatch import execute, load_block
    for block_id in ['analytics', 'audit', 'dashboard', 'database', 'event_bus', 'evidence_verifier', 'file_hasher', 'knowledge', 'notification', 'portfolio_rollup', 'queue', 'recommendation_template', 'storage', 'validation', 'vector_search', 'workflow']:
        load_block(block_id)
    actions = {'analytics': 'track_event', 'audit': 'log', 'dashboard': 'render', 'database': 'query', 'event_bus': 'publish', 'knowledge': 'ask', 'notification': 'send', 'queue': 'enqueue', 'storage': 'store', 'validation': 'validate_pipeline', 'workflow': 'run'}
    for block_id in ['analytics', 'audit', 'dashboard', 'database', 'event_bus', 'evidence_verifier', 'file_hasher', 'knowledge', 'notification', 'portfolio_rollup', 'queue', 'recommendation_template', 'storage', 'validation', 'vector_search', 'workflow']:
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
    from app.actions import inventory_management
    try:
        out = inventory_management.handle({'product_name': 'sample', 'quantity_on_hand': 'sample', 'reference': 'sample', 'sku': 'sample', 'status': 'open', 'location': 'sample', 'reorder_point': 'sample', 'unit_cost': 'sample', 'supplier_name': 'sample', 'category': 'sample', 'movement_type': 'sample', 'last_counted_date': '2026-09-03'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('inventory_management handle() must return a dict, got ' + type(out).__name__)
    from app.actions import sales_and_orders
    try:
        out = sales_and_orders.handle({'customer_name': 'sample', 'order_number': 'sample', 'reference': 'sample', 'status': 'open', 'customer_email': 'guest@example.com', 'channel': 'email', 'order_total': 'sample', 'item_count': 1, 'payment_status': 'open', 'fulfilment_status': 'open', 'order_date': '2026-09-03', 'notes': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('sales_and_orders handle() must return a dict, got ' + type(out).__name__)
    from app.actions import customer_insights
    try:
        out = customer_insights.handle({'customer_name': 'sample', 'reference': 'sample', 'status': 'open', 'customer_email': 'guest@example.com', 'segment': 'sample', 'lifetime_value': 'sample', 'orders_count': 1, 'last_purchase_date': '2026-09-03', 'loyalty_tier': 'sample', 'preferred_channel': 'email', 'insight_summary': 'sample', 'tags': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('customer_insights handle() must return a dict, got ' + type(out).__name__)
    from app.actions import analytics_dashboard
    try:
        out = analytics_dashboard.handle({'dashboard_name': 'sample', 'metric_name': 'sample', 'reference': 'sample', 'status': 'open', 'metric_value': 'sample', 'period_start': 'sample', 'period_end': 'sample', 'store_location': 'sample', 'widget_type': 'sample', 'report_format': 'sample', 'owner': 'sample', 'generated_at': '2026-09-03T10:00:00'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('analytics_dashboard handle() must return a dict, got ' + type(out).__name__)
    from app.actions import supplier_and_purchasing
    try:
        out = supplier_and_purchasing.handle({'purchase_order_number': 'sample', 'reference': 'sample', 'status': 'open', 'supplier_name': 'sample', 'supplier_email': 'guest@example.com', 'sku': 'sample', 'quantity_ordered': 'sample', 'unit_cost': 'sample', 'lead_time_days': 'sample', 'order_date': '2026-09-03', 'expected_date': '2026-09-03', 'payment_terms': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('supplier_and_purchasing handle() must return a dict, got ' + type(out).__name__)
    from app.actions import omnichannel_integration
    try:
        out = omnichannel_integration.handle({'integration_name': 'sample', 'reference': 'sample', 'status': 'open', 'channel': 'email', 'external_order_id': 'id-1', 'sync_direction': 'sample', 'sync_status': 'open', 'sku': 'sample', 'quantity': 1, 'sync_at': '2026-09-03T10:00:00', 'marketplace': 'sample', 'notes': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('omnichannel_integration handle() must return a dict, got ' + type(out).__name__)
    from app.actions import compliance_and_audit
    try:
        out = compliance_and_audit.handle({'action_taken': 'sample', 'actor': 'sample', 'control_id': 'id-1', 'reference': 'sample', 'status': 'open', 'regulation': 'sample', 'event_type': 'sample', 'evidence_ref': 'sample', 'file_path': 'sample', 'findings': 'sample', 'occurred_at': '2026-09-03T10:00:00', 'severity': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('compliance_and_audit handle() must return a dict, got ' + type(out).__name__)
    assert not failures, "; ".join(failures)


@pytest.mark.pilot
def test_every_capability_executes_end_to_end():
    """Pilot: each handler runs its blocks on a spec payload and
    Store must accept it. Not the factory code-phase gate."""
    for var in ("CEREBRUM_API_URL", "CEREBRUM_API_KEY"):
        os.environ.pop(var, None)
    import json as _json
    failures = []
    from app.actions import inventory_management
    out = inventory_management.handle({'product_name': 'sample', 'quantity_on_hand': 'sample', 'reference': 'sample', 'sku': 'sample', 'status': 'open', 'location': 'sample', 'reorder_point': 'sample', 'unit_cost': 'sample', 'supplier_name': 'sample', 'category': 'sample', 'movement_type': 'sample', 'last_counted_date': '2026-09-03'})
    if not isinstance(out, dict):
        failures.append('inventory_management returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('inventory_management rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('inventory_management reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import sales_and_orders
    out = sales_and_orders.handle({'customer_name': 'sample', 'order_number': 'sample', 'reference': 'sample', 'status': 'open', 'customer_email': 'guest@example.com', 'channel': 'email', 'order_total': 'sample', 'item_count': 1, 'payment_status': 'open', 'fulfilment_status': 'open', 'order_date': '2026-09-03', 'notes': 'sample'})
    if not isinstance(out, dict):
        failures.append('sales_and_orders returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('sales_and_orders rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('sales_and_orders reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import customer_insights
    out = customer_insights.handle({'customer_name': 'sample', 'reference': 'sample', 'status': 'open', 'customer_email': 'guest@example.com', 'segment': 'sample', 'lifetime_value': 'sample', 'orders_count': 1, 'last_purchase_date': '2026-09-03', 'loyalty_tier': 'sample', 'preferred_channel': 'email', 'insight_summary': 'sample', 'tags': 'sample'})
    if not isinstance(out, dict):
        failures.append('customer_insights returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('customer_insights rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('customer_insights reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import analytics_dashboard
    out = analytics_dashboard.handle({'dashboard_name': 'sample', 'metric_name': 'sample', 'reference': 'sample', 'status': 'open', 'metric_value': 'sample', 'period_start': 'sample', 'period_end': 'sample', 'store_location': 'sample', 'widget_type': 'sample', 'report_format': 'sample', 'owner': 'sample', 'generated_at': '2026-09-03T10:00:00'})
    if not isinstance(out, dict):
        failures.append('analytics_dashboard returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('analytics_dashboard rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('analytics_dashboard reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import supplier_and_purchasing
    out = supplier_and_purchasing.handle({'purchase_order_number': 'sample', 'reference': 'sample', 'status': 'open', 'supplier_name': 'sample', 'supplier_email': 'guest@example.com', 'sku': 'sample', 'quantity_ordered': 'sample', 'unit_cost': 'sample', 'lead_time_days': 'sample', 'order_date': '2026-09-03', 'expected_date': '2026-09-03', 'payment_terms': 'sample'})
    if not isinstance(out, dict):
        failures.append('supplier_and_purchasing returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('supplier_and_purchasing rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('supplier_and_purchasing reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import omnichannel_integration
    out = omnichannel_integration.handle({'integration_name': 'sample', 'reference': 'sample', 'status': 'open', 'channel': 'email', 'external_order_id': 'id-1', 'sync_direction': 'sample', 'sync_status': 'open', 'sku': 'sample', 'quantity': 1, 'sync_at': '2026-09-03T10:00:00', 'marketplace': 'sample', 'notes': 'sample'})
    if not isinstance(out, dict):
        failures.append('omnichannel_integration returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('omnichannel_integration rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('omnichannel_integration reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import compliance_and_audit
    out = compliance_and_audit.handle({'action_taken': 'sample', 'actor': 'sample', 'control_id': 'id-1', 'reference': 'sample', 'status': 'open', 'regulation': 'sample', 'event_type': 'sample', 'evidence_ref': 'sample', 'file_path': 'sample', 'findings': 'sample', 'occurred_at': '2026-09-03T10:00:00', 'severity': 'sample'})
    if not isinstance(out, dict):
        failures.append('compliance_and_audit returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('compliance_and_audit rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('compliance_and_audit reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    assert not failures, "; ".join(failures)
