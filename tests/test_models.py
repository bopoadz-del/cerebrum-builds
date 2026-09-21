"""Models must survive a round trip through sqlite."""

from app import store
from app.models import MODELS


#: Tenant the generated tests act as (the platform token's tenant).
TENANT = 'local'


def test_every_model_round_trips():
    record = {'reference': 'sample', 'status': 'open', 'title': 'sample', 'document_kind': 'manual', 'question': 'sample', 'document_text': 'sample', 'attachment_path': 'sample', 'answer': 'sample', 'source_document': 'sample', 'authority_label': 'certified', 'notes': 'sample'}
    saved = store.save('document_and_knowledge_answers', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for document_and_knowledge_answers'
    fetched = store.get('document_and_knowledge_answers', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'document_and_knowledge_answers did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('document_and_knowledge_answers', tenant_id=TENANT))
    record = {'reference': 'sample', 'status': 'open', 'system': 'opera', 'resource': 'sample', 'direction': 'inbound', 'payload_format': 'json', 'endpoint_url': 'sample', 'records_seen': 1, 'notes': 'sample'}
    saved = store.save('external_integration_adapter', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for external_integration_adapter'
    fetched = store.get('external_integration_adapter', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'external_integration_adapter did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('external_integration_adapter', tenant_id=TENANT))
    record = {'reference': 'sample', 'status': 'open', 'guest_name': 'sample', 'room_number': 'sample', 'arrival_date': '2026-09-03', 'departure_date': '2026-09-03', 'guests_count': 1, 'stay_status': 'reserved', 'folio_currency': 'sample', 'notes': 'sample'}
    saved = store.save('front_desk_and_guest_stay', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for front_desk_and_guest_stay'
    fetched = store.get('front_desk_and_guest_stay', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'front_desk_and_guest_stay did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('front_desk_and_guest_stay', tenant_id=TENANT))
    record = {'reference': 'sample', 'status': 'open', 'guest_name': 'sample', 'recency_days': 1, 'frequency': 1, 'monetary': 1, 'segment': 'champion', 'delivery_channel': 'mcp', 'offer_code': 'id-1', 'notes': 'sample'}
    saved = store.save('guest_engagement_and_segmentation', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for guest_engagement_and_segmentation'
    fetched = store.get('guest_engagement_and_segmentation', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'guest_engagement_and_segmentation did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('guest_engagement_and_segmentation', tenant_id=TENANT))
    record = {'reference': 'sample', 'status': 'open', 'title': 'sample', 'work_type': 'housekeeping', 'room_number': 'sample', 'priority': 'low', 'due_date': '2026-09-03', 'assigned_to': 'sample', 'work_status': 'open', 'notes': 'sample'}
    saved = store.save('housekeeping_and_maintenance', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for housekeeping_and_maintenance'
    fetched = store.get('housekeeping_and_maintenance', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'housekeeping_and_maintenance did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('housekeeping_and_maintenance', tenant_id=TENANT))
    record = {'setting': 'sample', 'reference': 'sample', 'status': 'open', 'folio_reference': 'sample', 'charge_type': 'room', 'amount': 1, 'currency': 'sample', 'tax_rate_percent': 1, 'total_amount': 1, 'notes': 'sample'}
    saved = store.save('operations_billing', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for operations_billing'
    fetched = store.get('operations_billing', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'operations_billing did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('operations_billing', tenant_id=TENANT))
    record = {'reference': 'sample', 'status': 'open', 'dashboard_name': 'sample', 'widget': 'occupancy', 'window_days': 1, 'operator_role': 'operator', 'occupancy_percent': 1, 'open_work_orders': 1, 'notes': 'sample'}
    saved = store.save('operations_oversight_dashboard', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for operations_oversight_dashboard'
    fetched = store.get('operations_oversight_dashboard', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'operations_oversight_dashboard did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('operations_oversight_dashboard', tenant_id=TENANT))
    record = {'reference': 'sample', 'status': 'open', 'property_name': 'sample', 'building': 'sample', 'floor': 1, 'room_number': 'sample', 'room_type': 'standard', 'capacity': 1, 'room_status': 'available', 'notes': 'sample'}
    saved = store.save('property_and_room_registry', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for property_and_room_registry'
    fetched = store.get('property_and_room_registry', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'property_and_room_registry did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('property_and_room_registry', tenant_id=TENANT))


def test_models_expose_their_fields():
    assert MODELS, 'no models were generated'
    for cap_id, cls in MODELS.items():
        instance = cls.from_dict({})
        assert instance.to_dict()['id'] is None
        assert cls.FIELDS, cap_id
