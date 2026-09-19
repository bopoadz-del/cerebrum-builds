"""Models must survive a round trip through sqlite."""

from app import store
from app.models import MODELS


#: Tenant the generated tests act as (the platform token's tenant).
TENANT = 'local'


def test_every_model_round_trips():
    record = {'metric_name': 'sample', 'reference': 'sample', 'report_name': 'sample', 'status': 'open', 'metric_value': 'sample', 'period_start': 'sample', 'period_end': 'sample', 'appointments_count': 1, 'revenue_total': 'sample', 'event_type': 'sample'}
    saved = store.save('analytics_and_reporting', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for analytics_and_reporting'
    fetched = store.get('analytics_and_reporting', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'analytics_and_reporting did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('analytics_and_reporting', tenant_id=TENANT))
    record = {'appointment_type': 'wellness_exam', 'owner_name': 'sample', 'patient_name': 'sample', 'reference': 'sample', 'scheduled_at': '2026-09-03T10:00:00', 'status': 'open', 'veterinarian': 'sample', 'room': 'sample', 'duration_minutes': 'sample', 'reminder_channel': 'email', 'notes': 'sample'}
    saved = store.save('appointment_scheduling', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for appointment_scheduling'
    fetched = store.get('appointment_scheduling', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'appointment_scheduling did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('appointment_scheduling', tenant_id=TENANT))
    record = {'owner_name': 'sample', 'reference': 'sample', 'service_code': 'id-1', 'status': 'open', 'invoice_total': 'sample', 'amount_paid': 'sample', 'currency': 'USD', 'issued_on': 'sample', 'due_on': 'sample', 'payment_method': 'card', 'attachment_path': 'sample'}
    saved = store.save('billing_and_invoicing', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for billing_and_invoicing'
    fetched = store.get('billing_and_invoicing', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'billing_and_invoicing did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('billing_and_invoicing', tenant_id=TENANT))
    record = {'owner_name': 'sample', 'reference': 'sample', 'reminder_type': 'appointment_reminder', 'status': 'open', 'owner_email': 'guest@example.com', 'channel': 'email', 'scheduled_for': 'sample', 'template_name': 'sample', 'message_body': 'sample'}
    saved = store.save('client_communication_and_reminders', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for client_communication_and_reminders'
    fetched = store.get('client_communication_and_reminders', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'client_communication_and_reminders did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('client_communication_and_reminders', tenant_id=TENANT))
    record = {'diagnosis': 'sample', 'patient_name': 'sample', 'reference': 'sample', 'status': 'open', 'visit_date': '2026-09-03', 'treatment_plan': 'sample', 'medication': 'sample', 'dosage_mg': 'sample', 'administration_route': 'oral', 'attachment_path': 'sample', 'prescription_notes': 'sample'}
    saved = store.save('clinical_visit_notes_and_treatment_plans', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for clinical_visit_notes_and_treatment_plans'
    fetched = store.get('clinical_visit_notes_and_treatment_plans', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'clinical_visit_notes_and_treatment_plans did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('clinical_visit_notes_and_treatment_plans', tenant_id=TENANT))
    record = {'content': 'sample', 'record_type': 'clinical_note', 'reference': 'sample', 'status': 'open', 'subject_ref': 'sample', 'content_hash': 'sample', 'reviewer': 'sample', 'reviewed_on': 'sample', 'retention_until': 'sample'}
    saved = store.save('compliance_and_audit_trail', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for compliance_and_audit_trail'
    fetched = store.get('compliance_and_audit_trail', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'compliance_and_audit_trail did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('compliance_and_audit_trail', tenant_id=TENANT))
    record = {'owner_name': 'sample', 'patient_name': 'sample', 'reference': 'sample', 'species': 'dog', 'status': 'open', 'breed': 'sample', 'sex': 'male', 'age_years': 'sample', 'weight_kg': 'sample', 'microchip_id': 'id-1', 'owner_email': 'guest@example.com', 'owner_phone': 'sample', 'clinical_history': 'sample'}
    saved = store.save('patient_and_owner_records', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for patient_and_owner_records'
    fetched = store.get('patient_and_owner_records', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'patient_and_owner_records did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('patient_and_owner_records', tenant_id=TENANT))
    record = {'patient_name': 'sample', 'reference': 'sample', 'status': 'open', 'vaccine_type': 'rabies', 'administered_on': 'sample', 'next_due_on': 'sample', 'lot_number': 'sample', 'administered_by': 'sample', 'reminder_channel': 'email'}
    saved = store.save('vaccination_tracking', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for vaccination_tracking'
    fetched = store.get('vaccination_tracking', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'vaccination_tracking did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('vaccination_tracking', tenant_id=TENANT))


def test_models_expose_their_fields():
    assert MODELS, 'no models were generated'
    for cap_id, cls in MODELS.items():
        instance = cls.from_dict({})
        assert instance.to_dict()['id'] is None
        assert cls.FIELDS, cap_id
