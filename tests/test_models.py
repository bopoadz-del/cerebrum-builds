"""Models must survive a round trip through sqlite."""

from app import store
from app.models import MODELS


def test_every_model_round_trips():
    record = {'check_in_date': '2026-09-03', 'guest_name': 'sample', 'reference': 'sample', 'room_number': 'sample', 'status': 'open', 'check_in_count': 1, 'notes': 'sample'}
    saved = store.save('list_todays_check_ins', record)
    assert saved['id'] is not None, 'no id assigned for list_todays_check_ins'
    fetched = store.get('list_todays_check_ins', saved['id'])
    assert fetched is not None, 'list_todays_check_ins did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('list_todays_check_ins'))
    record = {'guest_name': 'sample', 'reference': 'sample', 'room_number': 'sample', 'status': 'open', 'checked_in_at': '2026-09-03T10:00:00', 'guests_count': 1, 'notes': 'sample'}
    saved = store.save('record_check_in', record)
    assert saved['id'] is not None, 'no id assigned for record_check_in'
    fetched = store.get('record_check_in', saved['id'])
    assert fetched is not None, 'record_check_in did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('record_check_in'))


def test_models_expose_their_fields():
    assert MODELS, 'no models were generated'
    for cap_id, cls in MODELS.items():
        instance = cls.from_dict({})
        assert instance.to_dict()['id'] is None
        assert cls.FIELDS, cap_id
