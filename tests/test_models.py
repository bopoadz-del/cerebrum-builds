"""Models must survive a round trip through sqlite."""

from app import store
from app.models import MODELS


#: Tenant the generated tests act as (the platform token's tenant).
TENANT = 'local'


def test_every_model_round_trips():
    record = {'action_type': 'approval', 'actor_name': 'sample', 'actor_role': 'owner', 'reference': 'sample', 'status': 'open', 'entity_name': 'sample', 'entity_reference': 'sample', 'change_summary': 'sample', 'approval_state': 'pending', 'occurred_at': '2026-09-03T10:00:00', 'notes': 'sample'}
    saved = store.save('audit_and_access_control', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for audit_and_access_control'
    fetched = store.get('audit_and_access_control', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'audit_and_access_control did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('audit_and_access_control', tenant_id=TENANT))
    record = {'job_code': 'id-1', 'reference': 'sample', 'reminder_type': 'valuation_due', 'status': 'open', 'due_date': '2026-09-03', 'threshold_count': 1, 'actual_count': 1, 'escalation_state': 'none', 'channel': 'email', 'recipient_email': 'guest@example.com', 'message_body': 'sample', 'schedule': 'monthly', 'summary': 'sample'}
    saved = store.save('automation_reminders_escalation', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for automation_reminders_escalation'
    fetched = store.get('automation_reminders_escalation', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'automation_reminders_escalation did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('automation_reminders_escalation', tenant_id=TENANT))
    record = {'job_code': 'id-1', 'reference': 'sample', 'status': 'open', 'valuation_number': 'sample', 'boq_item': 'sample', 'measured_quantity': 'sample', 'unit_rate_aed': 'sample', 'gross_value_aed': 'sample', 'retention_percent': 'sample', 'retention_aed': 'sample', 'vat_rate_percent': 'sample', 'vat_amount_aed': 'sample', 'certified_value_aed': 'sample', 'payment_status': 'unpaid', 'purchase_order': 'sample', 'po_party_type': 'supplier', 'amount_due_aed': 'sample', 'due_on': 'sample', 'notes': 'sample'}
    saved = store.save('commercials_and_valuations', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for commercials_and_valuations'
    fetched = store.get('commercials_and_valuations', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'commercials_and_valuations did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('commercials_and_valuations', tenant_id=TENANT))
    record = {'document_title': 'sample', 'document_type': 'boq', 'reference': 'sample', 'status': 'open', 'job_code': 'id-1', 'revision': 'sample', 'file_name': 'sample', 'file_path': 'sample', 'file_sha256': 'sample', 'question': 'sample', 'answer': 'sample', 'source_reference': 'sample', 'indexed_at': '2026-09-03T10:00:00', 'notes': 'sample'}
    saved = store.save('document_qa_and_indexing', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for document_qa_and_indexing'
    fetched = store.get('document_qa_and_indexing', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'document_qa_and_indexing did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('document_qa_and_indexing', tenant_id=TENANT))
    record = {'job_code': 'id-1', 'job_name': 'sample', 'reference': 'sample', 'site_name': 'sample', 'status': 'open', 'client_name': 'sample', 'work_front': 'sample', 'contract_value_aed': 'sample', 'progress_percent': 'sample', 'milestone': 'sample', 'milestone_due_date': '2026-09-03', 'snag_open_count': 1, 'variation_reference': 'sample', 'variation_status': 'draft', 'notes': 'sample'}
    saved = store.save('job_and_site_tracking', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for job_and_site_tracking'
    fetched = store.get('job_and_site_tracking', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'job_and_site_tracking did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('job_and_site_tracking', tenant_id=TENANT))
    record = {'margin_percent': 'sample', 'reference': 'sample', 'status': 'open', 'job_code': 'id-1', 'report_date': '2026-09-03', 'progress_percent': 'sample', 'certified_value_aed': 'sample', 'cost_to_date_aed': 'sample', 'variations_pending': 'sample', 'snags_open': 'sample', 'payments_due_aed': 'sample', 'summary': 'sample'}
    saved = store.save('progress_cost_dashboard', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for progress_cost_dashboard'
    fetched = store.get('progress_cost_dashboard', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'progress_cost_dashboard did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('progress_cost_dashboard', tenant_id=TENANT))
    record = {'document_title': 'sample', 'job_code': 'id-1', 'reference': 'sample', 'status': 'open', 'method_statement_ref': 'sample', 'work_front': 'sample', 'checklist_item': 'sample', 'checklist_state': 'met', 'readiness_gate': 'ready', 'incident_type': 'near_miss', 'incident_date': '2026-09-03', 'severity': 'low', 'action_taken': 'sample', 'notes': 'sample'}
    saved = store.save('safety_and_compliance', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for safety_and_compliance'
    fetched = store.get('safety_and_compliance', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'safety_and_compliance did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('safety_and_compliance', tenant_id=TENANT))
    record = {'message_body': 'sample', 'reference': 'sample', 'status': 'open', 'subject': 'sample', 'recipient_email': 'guest@example.com', 'recipient_role': 'owner', 'channel': 'email', 'notification_type': 'approval', 'related_reference': 'sample', 'send_at': '2026-09-03T10:00:00', 'delivery_state': 'queued'}
    saved = store.save('team_notifications', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for team_notifications'
    fetched = store.get('team_notifications', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'team_notifications did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('team_notifications', tenant_id=TENANT))


def test_models_expose_their_fields():
    assert MODELS, 'no models were generated'
    for cap_id, cls in MODELS.items():
        instance = cls.from_dict({})
        assert instance.to_dict()['id'] is None
        assert cls.FIELDS, cap_id
