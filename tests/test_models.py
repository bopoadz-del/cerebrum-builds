"""Models must survive a round trip through sqlite."""

from app import store
from app.models import MODELS


def test_every_model_round_trips():
    record = {'client_name': 'sample', 'reference': 'sample', 'status': 'open', 'client_email': 'guest@example.com', 'client_phone': 'sample', 'matter_type': 'sample', 'referral_source': 'sample', 'conflict_check': 'sample', 'risk_score': 'sample', 'estimated_fee': 'sample', 'retainer_amount': 'sample', 'document_path': 'sample', 'intake_date': '2026-09-03'}
    saved = store.save('client_intake', record)
    assert saved['id'] is not None, 'no id assigned for client_intake'
    fetched = store.get('client_intake', saved['id'])
    assert fetched is not None, 'client_intake did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('client_intake'))
    record = {'client_name': 'sample', 'reference': 'sample', 'status': 'open', 'client_email': 'guest@example.com', 'matter_number': 'sample', 'portal_access_level': 'sample', 'unread_messages': 'sample', 'shared_documents': 'sample', 'message_subject': 'sample', 'message_body': 'sample', 'last_login_at': '2026-09-03T10:00:00', 'document_path': 'sample'}
    saved = store.save('client_portal', record)
    assert saved['id'] is not None, 'no id assigned for client_portal'
    fetched = store.get('client_portal', saved['id'])
    assert fetched is not None, 'client_portal did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('client_portal'))
    record = {'action_taken': 'sample', 'actor': 'sample', 'control_id': 'id-1', 'reference': 'sample', 'status': 'open', 'framework': 'sample', 'regulation': 'sample', 'event_type': 'sample', 'actor_role': 'sample', 'evidence_ref': 'sample', 'findings': 'sample', 'occurred_at': '2026-09-03T10:00:00'}
    saved = store.save('compliance_audit', record)
    assert saved['id'] is not None, 'no id assigned for compliance_audit'
    fetched = store.get('compliance_audit', saved['id'])
    assert fetched is not None, 'compliance_audit did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('compliance_audit'))
    record = {'document_title': 'sample', 'reference': 'sample', 'status': 'open', 'document_type': 'sample', 'matter_number': 'sample', 'version': 'sample', 'file_path': 'sample', 'content_hash': 'sample', 'confidentiality': 'sample', 'document_owner': 'sample', 'tags': 'sample', 'uploaded_by': 'sample', 'uploaded_at': '2026-09-03T10:00:00'}
    saved = store.save('document_management', record)
    assert saved['id'] is not None, 'no id assigned for document_management'
    fetched = store.get('document_management', saved['id'])
    assert fetched is not None, 'document_management did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('document_management'))
    record = {'metric_name': 'sample', 'reference': 'sample', 'status': 'open', 'metric_value': 'sample', 'benchmark_value': 'sample', 'practice_area': 'sample', 'dimension': 'sample', 'period_start': 'sample', 'period_end': 'sample', 'source_matter': 'sample'}
    saved = store.save('legal_analytics', record)
    assert saved['id'] is not None, 'no id assigned for legal_analytics'
    fetched = store.get('legal_analytics', saved['id'])
    assert fetched is not None, 'legal_analytics did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('legal_analytics'))
    record = {'client_name': 'sample', 'matter_number': 'sample', 'matter_title': 'sample', 'reference': 'sample', 'status': 'open', 'client_email': 'guest@example.com', 'practice_area': 'sample', 'responsible_attorney': 'sample', 'matter_stage': 'sample', 'priority': 'sample', 'opened_date': '2026-09-03', 'deadline_date': '2026-09-03', 'billing_type': 'sample', 'document_path': 'sample'}
    saved = store.save('matter_management', record)
    assert saved['id'] is not None, 'no id assigned for matter_management'
    fetched = store.get('matter_management', saved['id'])
    assert fetched is not None, 'matter_management did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('matter_management'))
    record = {'matter_number': 'sample', 'reference': 'sample', 'status': 'open', 'timekeeper': 'sample', 'client_name': 'sample', 'client_email': 'guest@example.com', 'activity_date': '2026-09-03', 'hours': 'sample', 'hourly_rate': 'sample', 'billable_amount': 'sample', 'invoice_number': 'sample', 'payment_status': 'open', 'narrative': 'sample'}
    saved = store.save('time_and_billing', record)
    assert saved['id'] is not None, 'no id assigned for time_and_billing'
    fetched = store.get('time_and_billing', saved['id'])
    assert fetched is not None, 'time_and_billing did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('time_and_billing'))


def test_models_expose_their_fields():
    assert MODELS, 'no models were generated'
    for cap_id, cls in MODELS.items():
        instance = cls.from_dict({})
        assert instance.to_dict()['id'] is None
        assert cls.FIELDS, cap_id
