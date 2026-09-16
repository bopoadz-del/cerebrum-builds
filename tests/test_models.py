"""Models must survive a round trip through sqlite."""

from app import store
from app.models import MODELS


def test_every_model_round_trips():
    record = {'pet_name': 'sample', 'reference': 'sample', 'status': 'open', 'veterinarian': 'sample', 'owner_name': 'sample', 'appointment_date': '2026-09-03', 'appointment_time': '10:00:00', 'duration_minutes': 'sample', 'visit_reason': 'sample', 'room': 'sample', 'appointment_status': 'open'}
    saved = store.save('appointment_scheduling', record)
    assert saved['id'] is not None, 'no id assigned for appointment_scheduling'
    fetched = store.get('appointment_scheduling', saved['id'])
    assert fetched is not None, 'appointment_scheduling did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('appointment_scheduling'))
    record = {'actor': 'sample', 'event_type': 'sample', 'reference': 'sample', 'status': 'open', 'entity_name': 'sample', 'entity_id': 'id-1', 'actor_role': 'sample', 'action_taken': 'sample', 'details': 'sample', 'occurred_at': '2026-09-03T10:00:00'}
    saved = store.save('audit_trail', record)
    assert saved['id'] is not None, 'no id assigned for audit_trail'
    fetched = store.get('audit_trail', saved['id'])
    assert fetched is not None, 'audit_trail did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('audit_trail'))
    record = {'client_name': 'sample', 'invoice_number': 'sample', 'reference': 'sample', 'status': 'open', 'pet_name': 'sample', 'line_items': 'sample', 'subtotal': 'sample', 'tax_rate': 'sample', 'total_amount': 'sample', 'payment_status': 'open', 'payment_method': 'sample', 'invoice_date': '2026-09-03', 'attachment_path': 'sample'}
    saved = store.save('billing_invoicing', record)
    assert saved['id'] is not None, 'no id assigned for billing_invoicing'
    fetched = store.get('billing_invoicing', saved['id'])
    assert fetched is not None, 'billing_invoicing did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('billing_invoicing'))
    record = {'metric_name': 'sample', 'reference': 'sample', 'status': 'open', 'metric_value': 'sample', 'period': 'sample', 'period_start': 'sample', 'period_end': 'sample', 'dimension': 'sample'}
    saved = store.save('clinic_analytics', record)
    assert saved['id'] is not None, 'no id assigned for clinic_analytics'
    fetched = store.get('clinic_analytics', saved['id'])
    assert fetched is not None, 'clinic_analytics did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('clinic_analytics'))
    record = {'item_name': 'sample', 'reference': 'sample', 'sku': 'sample', 'status': 'open', 'category': 'sample', 'quantity': 1, 'reorder_level': 'sample', 'unit_cost': 'sample', 'supplier': 'sample', 'expiry_date': '2026-09-03'}
    saved = store.save('inventory_management', record)
    assert saved['id'] is not None, 'no id assigned for inventory_management'
    fetched = store.get('inventory_management', saved['id'])
    assert fetched is not None, 'inventory_management did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('inventory_management'))
    record = {'owner_name': 'sample', 'pet_name': 'sample', 'reference': 'sample', 'status': 'open', 'species': 'sample', 'breed': 'sample', 'owner_email': 'guest@example.com', 'owner_phone': 'sample', 'date_of_birth': 'sample', 'weight_kg': 'sample', 'vaccination_status': 'open', 'allergies': 'sample', 'clinical_notes': 'sample'}
    saved = store.save('patient_records', record)
    assert saved['id'] is not None, 'no id assigned for patient_records'
    fetched = store.get('patient_records', saved['id'])
    assert fetched is not None, 'patient_records did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('patient_records'))
    record = {'reference': 'sample', 'role_name': 'sample', 'status': 'open', 'display_name': 'sample', 'permissions': 'sample', 'access_level': 'sample', 'department': 'sample', 'is_active': True}
    saved = store.save('role_management', record)
    assert saved['id'] is not None, 'no id assigned for role_management'
    fetched = store.get('role_management', saved['id'])
    assert fetched is not None, 'role_management did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('role_management'))
    record = {'pet_name': 'sample', 'reference': 'sample', 'status': 'open', 'veterinarian': 'sample', 'treatment_type': 'sample', 'diagnosis': 'sample', 'procedure_notes': 'sample', 'medication': 'sample', 'dosage': 'sample', 'treatment_date': '2026-09-03', 'follow_up_date': '2026-09-03', 'attachment_path': 'sample'}
    saved = store.save('treatment_management', record)
    assert saved['id'] is not None, 'no id assigned for treatment_management'
    fetched = store.get('treatment_management', saved['id'])
    assert fetched is not None, 'treatment_management did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('treatment_management'))


def test_models_expose_their_fields():
    assert MODELS, 'no models were generated'
    for cap_id, cls in MODELS.items():
        instance = cls.from_dict({})
        assert instance.to_dict()['id'] is None
        assert cls.FIELDS, cap_id
