"""Models must survive a round trip through sqlite."""

from app import store
from app.models import MODELS


#: Tenant the generated tests act as (the platform token's tenant).
TENANT = 'local'


def test_every_model_round_trips():
    record = {'branch': 'sample', 'reference': 'sample', 'role_view': 'sample', 'status': 'open', 'view_scope': 'sample', 'period': 'sample', 'metrics_summary': 'sample', 'notes': 'sample'}
    saved = store.save('branch_and_consolidated_operations', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for branch_and_consolidated_operations'
    fetched = store.get('branch_and_consolidated_operations', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'branch_and_consolidated_operations did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('branch_and_consolidated_operations', tenant_id=TENANT))
    record = {'branch': 'sample', 'entry_type': 'sale', 'reference': 'sample', 'status': 'open', 'entry_date': '2026-09-03', 'amount': 'sample', 'margin_percent': 'sample', 'ingredient': 'sample', 'notes': 'sample'}
    saved = store.save('branch_books_and_accounting', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for branch_books_and_accounting'
    fetched = store.get('branch_books_and_accounting', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'branch_books_and_accounting did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('branch_books_and_accounting', tenant_id=TENANT))
    record = {'branch': 'sample', 'driver': 'sample', 'reference': 'sample', 'status': 'open', 'vehicle_type': 'car', 'vehicle_code': 'id-1', 'delivery_zone': 'sample', 'route': 'sample', 'order_reference': 'sample', 'proof_of_delivery': 'sample', 'scheduled_at': '2026-09-03T10:00:00'}
    saved = store.save('delivery_and_dispatch', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for delivery_and_dispatch'
    fetched = store.get('delivery_and_dispatch', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'delivery_and_dispatch did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('delivery_and_dispatch', tenant_id=TENANT))
    record = {'branch': 'sample', 'document_type': 'price_list', 'question': 'sample', 'reference': 'sample', 'status': 'open', 'answer': 'sample', 'citations': 'sample', 'confidence': 'sample'}
    saved = store.save('document_grounded_knowledge', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for document_grounded_knowledge'
    fetched = store.get('document_grounded_knowledge', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'document_grounded_knowledge did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('document_grounded_knowledge', tenant_id=TENANT))
    record = {'branch': 'sample', 'event_name': 'sample', 'reference': 'sample', 'status': 'open', 'event_date': '2026-09-03', 'guest_count': 1, 'deposit_amount': 'sample', 'delivery_time': '10:00:00', 'venue': 'sample', 'contact_email': 'guest@example.com'}
    saved = store.save('events_supply', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for events_supply'
    fetched = store.get('events_supply', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'events_supply did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('events_supply', tenant_id=TENANT))
    record = {'branch': 'sample', 'item_name': 'sample', 'item_type': 'ingredient', 'reference': 'sample', 'status': 'open', 'quantity_on_hand': 'sample', 'reorder_threshold': 'sample', 'unit': 'sample', 'supplier': 'sample', 'transfer_to_branch': 'sample', 'low_stock': 'sample'}
    saved = store.save('inventory_and_replenishment', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for inventory_and_replenishment'
    fetched = store.get('inventory_and_replenishment', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'inventory_and_replenishment did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('inventory_and_replenishment', tenant_id=TENANT))
    record = {'branch': 'sample', 'channel': 'email', 'customer_name': 'sample', 'reference': 'sample', 'status': 'open', 'order_status': 'open', 'payment_status': 'unpaid', 'confirmed': 'sample', 'due_at': '2026-09-03T10:00:00', 'follow_up_note': 'sample'}
    saved = store.save('order_follow_up', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for order_follow_up'
    fetched = store.get('order_follow_up', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'order_follow_up did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('order_follow_up', tenant_id=TENANT))
    record = {'branch': 'sample', 'direction': 'inbound', 'mailbox': 'sample', 'reference': 'sample', 'status': 'open', 'subject': 'sample', 'body': 'sample', 'message_reference': 'sample', 'received_at': '2026-09-03T10:00:00'}
    saved = store.save('outlook_branch_messaging_integration', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for outlook_branch_messaging_integration'
    fetched = store.get('outlook_branch_messaging_integration', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'outlook_branch_messaging_integration did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('outlook_branch_messaging_integration', tenant_id=TENANT))


def test_models_expose_their_fields():
    assert MODELS, 'no models were generated'
    for cap_id, cls in MODELS.items():
        instance = cls.from_dict({})
        assert instance.to_dict()['id'] is None
        assert cls.FIELDS, cap_id
