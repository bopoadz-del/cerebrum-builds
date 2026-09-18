"""Models must survive a round trip through sqlite."""

from app import store
from app.models import MODELS


#: Tenant the generated tests act as (the platform token's tenant).
TENANT = 'local'


def test_every_model_round_trips():
    record = {'actor': 'sample', 'reference': 'sample', 'status': 'open', 'change_type': 'create', 'subject_capability': 'sample', 'changed_at': '2026-09-03T10:00:00'}
    saved = store.save('audit_trail', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for audit_trail'
    fetched = store.get('audit_trail', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'audit_trail did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('audit_trail', tenant_id=TENANT))
    record = {'guest_name': 'sample', 'reference': 'sample', 'room_number': 'sample', 'status': 'open', 'channel': 'mcp', 'recipient': 'sample'}
    saved = store.save('checkin_notifications', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for checkin_notifications'
    fetched = store.get('checkin_notifications', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'checkin_notifications did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('checkin_notifications', tenant_id=TENANT))
    record = {'reference': 'sample', 'status': 'open', 'summary_date': '2026-09-03', 'arrivals_count': 1, 'occupancy_percent': 'sample', 'no_show_count': 1}
    saved = store.save('daily_checkin_summary', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for daily_checkin_summary'
    fetched = store.get('daily_checkin_summary', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'daily_checkin_summary did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('daily_checkin_summary', tenant_id=TENANT))
    record = {'guest_name': 'sample', 'reference': 'sample', 'status': 'open', 'room_number': 'sample', 'preference': 'sample', 'note': 'sample'}
    saved = store.save('guest_notes_and_preferences', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for guest_notes_and_preferences'
    fetched = store.get('guest_notes_and_preferences', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'guest_notes_and_preferences did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('guest_notes_and_preferences', tenant_id=TENANT))
    record = {'arrival_time': '10:00:00', 'guest_name': 'sample', 'nights': 1, 'reference': 'sample', 'room_number': 'sample', 'status': 'open', 'notes': 'sample'}
    saved = store.save('record_checkin', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for record_checkin'
    fetched = store.get('record_checkin', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'record_checkin did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('record_checkin', tenant_id=TENANT))
    record = {'check_in_date': '2026-09-03', 'check_out_date': '2026-09-03', 'reference': 'sample', 'room_number': 'sample', 'status': 'open', 'is_available': True}
    saved = store.save('room_availability_check', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for room_availability_check'
    fetched = store.get('room_availability_check', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'room_availability_check did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('room_availability_check', tenant_id=TENANT))
    record = {'arrival_date': '2026-09-03', 'guest_name': 'sample', 'reference': 'sample', 'room_number': 'sample', 'status': 'open', 'arrived': 'sample', 'arrivals_count': 1}
    saved = store.save('todays_arrivals_board', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for todays_arrivals_board'
    fetched = store.get('todays_arrivals_board', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'todays_arrivals_board did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('todays_arrivals_board', tenant_id=TENANT))


def test_models_expose_their_fields():
    assert MODELS, 'no models were generated'
    for cap_id, cls in MODELS.items():
        instance = cls.from_dict({})
        assert instance.to_dict()['id'] is None
        assert cls.FIELDS, cap_id
