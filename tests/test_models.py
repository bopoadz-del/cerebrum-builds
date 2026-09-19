"""Models must survive a round trip through sqlite."""

from app import store
from app.models import MODELS


#: Tenant the generated tests act as (the platform token's tenant).
TENANT = 'local'


def test_every_model_round_trips():
    record = {'appointment_type': 'exam', 'patient_name': 'sample', 'reference': 'sample', 'scheduled_at': '2026-09-03T10:00:00', 'status': 'open', 'patient_email': 'guest@example.com', 'provider': 'sample', 'chair_room': 'sample', 'duration_minutes': 'sample', 'reminder_channel': 'email', 'notes': 'sample'}
    saved = store.save('appointment_scheduling', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for appointment_scheduling'
    fetched = store.get('appointment_scheduling', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'appointment_scheduling did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('appointment_scheduling', tenant_id=TENANT))
    record = {'patient_name': 'sample', 'reference': 'sample', 'status': 'open', 'tooth': 'sample', 'procedure': 'sample', 'provider': 'sample', 'visit_date': '2026-09-03', 'date_from': 'sample', 'date_to': 'sample', 'search_notes': 'sample'}
    saved = store.save('clinical_history_search', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for clinical_history_search'
    fetched = store.get('clinical_history_search', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'clinical_history_search did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('clinical_history_search', tenant_id=TENANT))
    record = {'patient_email': 'guest@example.com', 'patient_name': 'sample', 'reference': 'sample', 'reminder_date': '2026-09-03', 'status': 'open', 'appointment_at': '2026-09-03T10:00:00', 'reminder_channel': 'email', 'message_body': 'sample', 'delivery_state': 'queued'}
    saved = store.save('day_before_email_reminders', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for day_before_email_reminders'
    fetched = store.get('day_before_email_reminders', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'day_before_email_reminders did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('day_before_email_reminders', tenant_id=TENANT))
    record = {'patient_name': 'sample', 'reference': 'sample', 'status': 'open', 'patient_email': 'guest@example.com', 'patient_phone': 'sample', 'date_of_birth': 'sample', 'primary_provider': 'sample', 'notes': 'sample'}
    saved = store.save('patient_directory', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for patient_directory'
    fetched = store.get('patient_directory', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'patient_directory did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('patient_directory', tenant_id=TENANT))
    record = {'patient_name': 'sample', 'procedure': 'sample', 'reference': 'sample', 'status': 'open', 'tooth': 'sample', 'fee': 'sample', 'visit_date': '2026-09-03', 'provider': 'sample', 'clinical_notes': 'sample'}
    saved = store.save('patient_visit_records', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for patient_visit_records'
    fetched = store.get('patient_visit_records', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'patient_visit_records did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('patient_visit_records', tenant_id=TENANT))
    record = {'reference': 'sample', 'staff_name': 'sample', 'staff_role': 'dentist', 'status': 'open', 'staff_email': 'guest@example.com', 'permission_scope': 'sample', 'active_from': 'sample'}
    saved = store.save('role_based_access', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for role_based_access'
    fetched = store.get('role_based_access', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'role_based_access did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('role_based_access', tenant_id=TENANT))
    record = {'list_date': '2026-09-03', 'patient_name': 'sample', 'reference': 'sample', 'status': 'open', 'provider': 'sample', 'procedure': 'sample', 'appointment_time': '10:00:00', 'appointment_status': 'scheduled', 'chair_room': 'sample'}
    saved = store.save('todays_appointment_list', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for todays_appointment_list'
    fetched = store.get('todays_appointment_list', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'todays_appointment_list did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('todays_appointment_list', tenant_id=TENANT))


def test_models_expose_their_fields():
    assert MODELS, 'no models were generated'
    for cap_id, cls in MODELS.items():
        instance = cls.from_dict({})
        assert instance.to_dict()['id'] is None
        assert cls.FIELDS, cap_id
