"""Models must survive a round trip through sqlite."""

from app import store
from app.models import MODELS


#: Tenant the generated tests act as (the platform token's tenant).
TENANT = 'local'


def test_every_model_round_trips():
    record = {'patient_name': 'sample', 'reference': 'sample', 'status': 'open'}
    saved = store.save('appointment_scheduling', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for appointment_scheduling'
    fetched = store.get('appointment_scheduling', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'appointment_scheduling did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('appointment_scheduling', tenant_id=TENANT))
    record = {'reference': 'sample', 'status': 'open'}
    saved = store.save('clinic_dashboard', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for clinic_dashboard'
    fetched = store.get('clinic_dashboard', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'clinic_dashboard did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('clinic_dashboard', tenant_id=TENANT))
    record = {'patient_name': 'sample', 'reference': 'sample', 'status': 'open'}
    saved = store.save('invoicing', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for invoicing'
    fetched = store.get('invoicing', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'invoicing did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('invoicing', tenant_id=TENANT))
    record = {'patient_name': 'sample', 'reference': 'sample', 'status': 'open'}
    saved = store.save('patient_records', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for patient_records'
    fetched = store.get('patient_records', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'patient_records did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('patient_records', tenant_id=TENANT))
    record = {'patient_name': 'sample', 'reference': 'sample', 'status': 'open'}
    saved = store.save('recall_reminders', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for recall_reminders'
    fetched = store.get('recall_reminders', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'recall_reminders did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('recall_reminders', tenant_id=TENANT))
    record = {'staff_name': 'sample', 'staff_namestaff_role': 'sample', 'staff_role': 'sample', 'reference': 'sample', 'status': 'open'}
    saved = store.save('staff_roles_permissions', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for staff_roles_permissions'
    fetched = store.get('staff_roles_permissions', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'staff_roles_permissions did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('staff_roles_permissions', tenant_id=TENANT))
    record = {'patient_name': 'sample', 'patient_nameprocedure': 'sample', 'reference': 'sample', 'status': 'open'}
    saved = store.save('treatment_records', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for treatment_records'
    fetched = store.get('treatment_records', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'treatment_records did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('treatment_records', tenant_id=TENANT))


def test_models_expose_their_fields():
    assert MODELS, 'no models were generated'
    for cap_id, cls in MODELS.items():
        instance = cls.from_dict({})
        assert instance.to_dict()['id'] is None
        assert cls.FIELDS, cap_id
