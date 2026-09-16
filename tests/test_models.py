"""Models must survive a round trip through sqlite."""

from app import store
from app.models import MODELS


def test_every_model_round_trips():
    record = {'dashboard_name': 'sample', 'metric_name': 'sample', 'reference': 'sample', 'status': 'open', 'metric_value': 'sample', 'period_start': 'sample', 'period_end': 'sample', 'store_location': 'sample', 'widget_type': 'sample', 'report_format': 'sample', 'owner': 'sample', 'generated_at': '2026-09-03T10:00:00'}
    saved = store.save('analytics_dashboard', record)
    assert saved['id'] is not None, 'no id assigned for analytics_dashboard'
    fetched = store.get('analytics_dashboard', saved['id'])
    assert fetched is not None, 'analytics_dashboard did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('analytics_dashboard'))
    record = {'action_taken': 'sample', 'actor': 'sample', 'control_id': 'id-1', 'reference': 'sample', 'status': 'open', 'regulation': 'sample', 'event_type': 'sample', 'evidence_ref': 'sample', 'file_path': 'sample', 'findings': 'sample', 'occurred_at': '2026-09-03T10:00:00', 'severity': 'sample'}
    saved = store.save('compliance_and_audit', record)
    assert saved['id'] is not None, 'no id assigned for compliance_and_audit'
    fetched = store.get('compliance_and_audit', saved['id'])
    assert fetched is not None, 'compliance_and_audit did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('compliance_and_audit'))
    record = {'customer_name': 'sample', 'reference': 'sample', 'status': 'open', 'customer_email': 'guest@example.com', 'segment': 'sample', 'lifetime_value': 'sample', 'orders_count': 1, 'last_purchase_date': '2026-09-03', 'loyalty_tier': 'sample', 'preferred_channel': 'email', 'insight_summary': 'sample', 'tags': 'sample'}
    saved = store.save('customer_insights', record)
    assert saved['id'] is not None, 'no id assigned for customer_insights'
    fetched = store.get('customer_insights', saved['id'])
    assert fetched is not None, 'customer_insights did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('customer_insights'))
    record = {'product_name': 'sample', 'quantity_on_hand': 'sample', 'reference': 'sample', 'sku': 'sample', 'status': 'open', 'location': 'sample', 'reorder_point': 'sample', 'unit_cost': 'sample', 'supplier_name': 'sample', 'category': 'sample', 'movement_type': 'sample', 'last_counted_date': '2026-09-03'}
    saved = store.save('inventory_management', record)
    assert saved['id'] is not None, 'no id assigned for inventory_management'
    fetched = store.get('inventory_management', saved['id'])
    assert fetched is not None, 'inventory_management did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('inventory_management'))
    record = {'integration_name': 'sample', 'reference': 'sample', 'status': 'open', 'channel': 'email', 'external_order_id': 'id-1', 'sync_direction': 'sample', 'sync_status': 'open', 'sku': 'sample', 'quantity': 1, 'sync_at': '2026-09-03T10:00:00', 'marketplace': 'sample', 'notes': 'sample'}
    saved = store.save('omnichannel_integration', record)
    assert saved['id'] is not None, 'no id assigned for omnichannel_integration'
    fetched = store.get('omnichannel_integration', saved['id'])
    assert fetched is not None, 'omnichannel_integration did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('omnichannel_integration'))
    record = {'customer_name': 'sample', 'order_number': 'sample', 'reference': 'sample', 'status': 'open', 'customer_email': 'guest@example.com', 'channel': 'email', 'order_total': 'sample', 'item_count': 1, 'payment_status': 'open', 'fulfilment_status': 'open', 'order_date': '2026-09-03', 'notes': 'sample'}
    saved = store.save('sales_and_orders', record)
    assert saved['id'] is not None, 'no id assigned for sales_and_orders'
    fetched = store.get('sales_and_orders', saved['id'])
    assert fetched is not None, 'sales_and_orders did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('sales_and_orders'))
    record = {'purchase_order_number': 'sample', 'reference': 'sample', 'status': 'open', 'supplier_name': 'sample', 'supplier_email': 'guest@example.com', 'sku': 'sample', 'quantity_ordered': 'sample', 'unit_cost': 'sample', 'lead_time_days': 'sample', 'order_date': '2026-09-03', 'expected_date': '2026-09-03', 'payment_terms': 'sample'}
    saved = store.save('supplier_and_purchasing', record)
    assert saved['id'] is not None, 'no id assigned for supplier_and_purchasing'
    fetched = store.get('supplier_and_purchasing', saved['id'])
    assert fetched is not None, 'supplier_and_purchasing did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('supplier_and_purchasing'))


def test_models_expose_their_fields():
    assert MODELS, 'no models were generated'
    for cap_id, cls in MODELS.items():
        instance = cls.from_dict({})
        assert instance.to_dict()['id'] is None
        assert cls.FIELDS, cap_id
