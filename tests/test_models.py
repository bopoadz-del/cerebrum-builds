"""Models must survive a round trip through sqlite."""

from app import store
from app.models import MODELS


#: Tenant the generated tests act as (the platform token's tenant).
TENANT = 'local'


def test_every_model_round_trips():
    record = {'assignment_mode': 'auto', 'category': 'electrical', 'complaint_reference': 'sample', 'priority': 'critical', 'reference': 'sample', 'required_trade': 'sample', 'school': 'sample', 'status': 'open', 'required_skill': 'sample', 'candidate_count': 1, 'assigned_to': 'sample', 'assigned_role': 'technician', 'match_score': 'sample', 'workload_score': 'sample', 'queue_position': 'sample', 'override_reason': 'sample', 'assigned_at': '2026-09-03T10:00:00'}
    saved = store.save('auto_assignment', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for auto_assignment'
    fetched = store.get('auto_assignment', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'auto_assignment did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('auto_assignment', tenant_id=TENANT))
    record = {'booking_reference': 'sample', 'facility': 'sample', 'integration': 'booking_system', 'mode': 'placeholder', 'reference': 'sample', 'school': 'sample', 'slot_start': 'sample', 'status': 'open', 'slot_end': 'sample', 'requested_by': 'sample', 'sync_state': 'not_implemented', 'last_sync_at': '2026-09-03T10:00:00', 'detail': 'sample', 'notes': 'sample'}
    saved = store.save('booking_system_integration', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for booking_system_integration'
    fetched = store.get('booking_system_integration', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'booking_system_integration did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('booking_system_integration', tenant_id=TENANT))
    record = {'category': 'electrical', 'description': 'sample', 'priority': 'critical', 'raised_by': 'sample', 'raised_by_role': 'school_staff', 'reference': 'sample', 'school': 'sample', 'status': 'open', 'site_code': 'id-1', 'contact_email': 'guest@example.com', 'contact_phone': 'sample', 'logged_by': 'sample', 'assigned_to': 'sample', 'assignment_mode': 'auto', 'reported_at': '2026-09-03T10:00:00', 'due_at': '2026-09-03T10:00:00', 'sla_hours': 'sample', 'closed_at': '2026-09-03T10:00:00', 'resolution_notes': 'sample', 'work_order_reference': 'sample'}
    saved = store.save('complaints_management', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for complaints_management'
    fetched = store.get('complaints_management', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'complaints_management did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('complaints_management', tenant_id=TENANT))
    record = {'direction': 'inbound', 'entity_type': 'purchase_order', 'integration': 'erp', 'mode': 'placeholder', 'reference': 'sample', 'status': 'open', 'external_reference': 'sample', 'endpoint': 'sample', 'currency': 'sample', 'amount': 'sample', 'sync_state': 'not_implemented', 'last_sync_at': '2026-09-03T10:00:00', 'detail': 'sample', 'notes': 'sample'}
    saved = store.save('erp_integration', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for erp_integration'
    fetched = store.get('erp_integration', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'erp_integration did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('erp_integration', tenant_id=TENANT))
    record = {'complaints_open': 'sample', 'period': 'sample', 'reference': 'sample', 'school': 'sample', 'scope': 'school', 'status': 'open', 'complaints_in_progress': 'sample', 'complaints_closed': 'sample', 'jobs_in_progress': 'sample', 'sla_breaches': 'sample', 'sla_compliance_pct': 'sample', 'avg_closure_hours': 'sample', 'headline': 'sample', 'generated_at': '2026-09-03T10:00:00'}
    saved = store.save('management_dashboards', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for management_dashboards'
    fetched = store.get('management_dashboards', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'management_dashboards did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('management_dashboards', tenant_id=TENANT))
    record = {'complaints_total': 'sample', 'period_end': 'sample', 'period_start': 'sample', 'reference': 'sample', 'report_type': 'daily', 'school': 'sample', 'scope': 'school', 'status': 'open', 'closed_total': 'sample', 'avg_closure_hours': 'sample', 'sla_compliance_pct': 'sample', 'top_category': 'sample', 'busiest_school': 'sample', 'recipients': 'sample', 'generated_at': '2026-09-03T10:00:00'}
    saved = store.save('reporting', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for reporting'
    fetched = store.get('reporting', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'reporting did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('reporting', tenant_id=TENANT))
    record = {'access_scope': 'portfolio', 'principal': 'sample', 'reference': 'sample', 'role': 'management', 'school': 'sample', 'status': 'open', 'principal_email': 'guest@example.com', 'permissions': 'sample', 'granted_by': 'sample', 'effective_from': 'sample', 'last_review_at': '2026-09-03T10:00:00', 'active': 'sample', 'notes': 'sample'}
    saved = store.save('role_based_access', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for role_based_access'
    fetched = store.get('role_based_access', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'role_based_access did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('role_based_access', tenant_id=TENANT))
    record = {'headcount': 'sample', 'reference': 'sample', 'school': 'sample', 'shift': 'morning', 'status': 'open', 'team_name': 'sample', 'team_type': 'technician', 'trade': 'sample', 'lead_name': 'sample', 'lead_email': 'guest@example.com', 'contact_phone': 'sample', 'active': 'sample', 'open_jobs': 'sample', 'notes': 'sample'}
    saved = store.save('workforce_management', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for workforce_management'
    fetched = store.get('workforce_management', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'workforce_management did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('workforce_management', tenant_id=TENANT))


def test_models_expose_their_fields():
    assert MODELS, 'no models were generated'
    for cap_id, cls in MODELS.items():
        instance = cls.from_dict({})
        assert instance.to_dict()['id'] is None
        assert cls.FIELDS, cap_id
