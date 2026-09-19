"""Models must survive a round trip through sqlite."""

from app import store
from app.models import MODELS


#: Tenant the generated tests act as (the platform token's tenant).
TENANT = 'local'


def test_every_model_round_trips():
    record = {'approver': 'sample', 'department': 'sample', 'reference': 'sample', 'request_type': 'invoice', 'status': 'open', 'approver_email': 'guest@example.com', 'amount': 'sample', 'threshold': 'sample', 'priority': 'low', 'submitted_at': '2026-09-03T10:00:00', 'notes': 'sample'}
    saved = store.save('approval_workflow', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for approval_workflow'
    fetched = store.get('approval_workflow', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'approval_workflow did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('approval_workflow', tenant_id=TENANT))
    record = {'department': 'sample', 'record_reference': 'sample', 'record_type': 'invoice', 'reference': 'sample', 'status': 'open', 'evidence_hash': 'sample', 'verified': 'sample', 'checked_at': '2026-09-03T10:00:00', 'notes': 'sample'}
    saved = store.save('audit_evidence_validation', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for audit_evidence_validation'
    fetched = store.get('audit_evidence_validation', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'audit_evidence_validation did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('audit_evidence_validation', tenant_id=TENANT))
    record = {'budget_owner': 'sample', 'department': 'sample', 'reference': 'sample', 'status': 'open', 'cost_centre': 'sample', 'period': 'sample', 'planned_amount': 'sample', 'actual_amount': 'sample', 'currency': 'sample', 'notes': 'sample'}
    saved = store.save('budget_planning_tracking', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for budget_planning_tracking'
    fetched = store.get('budget_planning_tracking', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'budget_planning_tracking did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('budget_planning_tracking', tenant_id=TENANT))
    record = {'department': 'sample', 'reference': 'sample', 'role_view': 'cfo', 'status': 'open', 'view_scope': 'sample', 'period': 'sample', 'spend_total': 'sample', 'commitment_total': 'sample', 'forecast_total': 'sample', 'risk_level': 'low', 'notes': 'sample'}
    saved = store.save('dashboard_portfolio_rollup', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for dashboard_portfolio_rollup'
    fetched = store.get('dashboard_portfolio_rollup', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'dashboard_portfolio_rollup did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('dashboard_portfolio_rollup', tenant_id=TENANT))
    record = {'department': 'sample', 'document_type': 'invoice', 'question': 'sample', 'reference': 'sample', 'status': 'open', 'answer': 'sample', 'citations': 'sample', 'confidence': 'sample', 'document_path': 'sample'}
    saved = store.save('finance_document_knowledge', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for finance_document_knowledge'
    fetched = store.get('finance_document_knowledge', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'finance_document_knowledge did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('finance_document_knowledge', tenant_id=TENANT))
    record = {'department': 'sample', 'direction': 'inbound', 'integration': 'google_drive', 'reference': 'sample', 'status': 'open', 'detail': 'sample', 'external_reference': 'sample', 'last_sync_at': '2026-09-03T10:00:00', 'notes': 'sample'}
    saved = store.save('integrations_placeholders', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for integrations_placeholders'
    fetched = store.get('integrations_placeholders', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'integrations_placeholders did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('integrations_placeholders', tenant_id=TENANT))
    record = {'category': 'software', 'department': 'sample', 'reference': 'sample', 'status': 'open', 'supplier': 'sample', 'amount': 'sample', 'currency': 'sample', 'invoice_date': '2026-09-03', 'invoice_number': 'sample', 'document_path': 'sample', 'notes': 'sample'}
    saved = store.save('spend_capture_categorisation', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for spend_capture_categorisation'
    fetched = store.get('spend_capture_categorisation', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'spend_capture_categorisation did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('spend_capture_categorisation', tenant_id=TENANT))
    record = {'department': 'sample', 'reference': 'sample', 'status': 'open', 'category': 'sample', 'period': 'sample', 'budget_amount': 'sample', 'actual_amount': 'sample', 'formula': 'sample', 'notes': 'sample'}
    saved = store.save('variance_analytics', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for variance_analytics'
    fetched = store.get('variance_analytics', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'variance_analytics did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('variance_analytics', tenant_id=TENANT))


def test_models_expose_their_fields():
    assert MODELS, 'no models were generated'
    for cap_id, cls in MODELS.items():
        instance = cls.from_dict({})
        assert instance.to_dict()['id'] is None
        assert cls.FIELDS, cap_id
