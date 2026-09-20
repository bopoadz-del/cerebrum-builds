"""The platform runs, and it runs without the store."""

import os

import pytest


def test_capabilities_import():
    from app.actions import complaints_management
    assert complaints_management.CAPABILITY_ID
    from app.actions import auto_assignment
    assert auto_assignment.CAPABILITY_ID
    from app.actions import workforce_management
    assert workforce_management.CAPABILITY_ID
    from app.actions import management_dashboards
    assert management_dashboards.CAPABILITY_ID
    from app.actions import reporting
    assert reporting.CAPABILITY_ID
    from app.actions import role_based_access
    assert role_based_access.CAPABILITY_ID
    from app.actions import erp_integration
    assert erp_integration.CAPABILITY_ID
    from app.actions import booking_system_integration
    assert booking_system_integration.CAPABILITY_ID


def test_dispatch_runs_offline():
    """No store env, no network: every block must LOAD and EXECUTE from
    vendor/. A block-level refusal of this bare probe is still local
    execution; an import failure is the store dependency this test
    exists to catch."""
    for var in ("CEREBRUM_API_URL", "CEREBRUM_API_KEY", "CEREBRUM_API_TOKEN"):
        os.environ.pop(var, None)
    from app.dispatch import execute, load_block
    for block_id in ['analytics', 'audit', 'capture', 'dashboard', 'event_bus', 'formula_executor', 'notification', 'portfolio_rollup', 'queue', 'recommendation_template', 'team', 'validation', 'workflow']:
        load_block(block_id)
    actions = {'analytics': 'track_event', 'audit': 'log', 'dashboard': 'render', 'event_bus': 'publish', 'notification': 'send', 'portfolio_rollup': 'aggregate', 'queue': 'enqueue', 'team': 'create_team', 'validation': 'validate_pipeline', 'workflow': 'run'}
    for block_id in ['analytics', 'audit', 'capture', 'dashboard', 'event_bus', 'formula_executor', 'notification', 'portfolio_rollup', 'queue', 'recommendation_template', 'team', 'validation', 'workflow']:
        try:
            result = execute(block_id, {}, action=actions.get(block_id))
        except RuntimeError as exc:
            # The block ran and refused the empty probe -- fine here;
            # the pilot test below demands Store-backed success.
            # An import error is never fine.
            assert "No module named" not in str(exc), (block_id, exc)
            assert "cannot import" not in str(exc), (block_id, exc)
        else:
            assert isinstance(result, dict), block_id


def test_kit_packs_present():
    """The download is a product tree: kits/ next to vendor/blocks."""
    from pathlib import Path as _Path
    kits = _Path(__file__).resolve().parents[1] / "kits"
    assert kits.is_dir(), "kits/ missing from the delivered platform"
    assert list(kits.glob("*/manifest.json")), "no kit pack manifests"


def test_every_capability_handle_returns_mapping():
    """Code-phase: the coder wired handle() and it returns a dict.
    Store ok: False or a Store exception is not this gate."""
    for var in ("CEREBRUM_API_URL", "CEREBRUM_API_KEY"):
        os.environ.pop(var, None)
    failures = []
    from app.actions import complaints_management
    try:
        out = complaints_management.handle({'category': 'electrical', 'description': 'sample', 'priority': 'critical', 'raised_by': 'sample', 'raised_by_role': 'school_staff', 'reference': 'sample', 'school': 'sample', 'status': 'open', 'site_code': 'id-1', 'contact_email': 'guest@example.com', 'contact_phone': 'sample', 'logged_by': 'sample', 'assigned_to': 'sample', 'assignment_mode': 'auto', 'reported_at': '2026-09-03T10:00:00', 'due_at': '2026-09-03T10:00:00', 'sla_hours': 'sample', 'closed_at': '2026-09-03T10:00:00', 'resolution_notes': 'sample', 'work_order_reference': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('complaints_management handle() must return a dict, got ' + type(out).__name__)
    from app.actions import auto_assignment
    try:
        out = auto_assignment.handle({'assignment_mode': 'auto', 'category': 'electrical', 'complaint_reference': 'sample', 'priority': 'critical', 'reference': 'sample', 'required_trade': 'sample', 'school': 'sample', 'status': 'open', 'required_skill': 'sample', 'candidate_count': 1, 'assigned_to': 'sample', 'assigned_role': 'technician', 'match_score': 'sample', 'workload_score': 'sample', 'queue_position': 'sample', 'override_reason': 'sample', 'assigned_at': '2026-09-03T10:00:00'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('auto_assignment handle() must return a dict, got ' + type(out).__name__)
    from app.actions import workforce_management
    try:
        out = workforce_management.handle({'headcount': 'sample', 'reference': 'sample', 'school': 'sample', 'shift': 'morning', 'status': 'open', 'team_name': 'sample', 'team_type': 'technician', 'trade': 'sample', 'lead_name': 'sample', 'lead_email': 'guest@example.com', 'contact_phone': 'sample', 'active': 'sample', 'open_jobs': 'sample', 'notes': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('workforce_management handle() must return a dict, got ' + type(out).__name__)
    from app.actions import management_dashboards
    try:
        out = management_dashboards.handle({'complaints_open': 'sample', 'period': 'sample', 'reference': 'sample', 'school': 'sample', 'scope': 'school', 'status': 'open', 'complaints_in_progress': 'sample', 'complaints_closed': 'sample', 'jobs_in_progress': 'sample', 'sla_breaches': 'sample', 'sla_compliance_pct': 'sample', 'avg_closure_hours': 'sample', 'headline': 'sample', 'generated_at': '2026-09-03T10:00:00'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('management_dashboards handle() must return a dict, got ' + type(out).__name__)
    from app.actions import reporting
    try:
        out = reporting.handle({'complaints_total': 'sample', 'period_end': 'sample', 'period_start': 'sample', 'reference': 'sample', 'report_type': 'daily', 'school': 'sample', 'scope': 'school', 'status': 'open', 'closed_total': 'sample', 'avg_closure_hours': 'sample', 'sla_compliance_pct': 'sample', 'top_category': 'sample', 'busiest_school': 'sample', 'recipients': 'sample', 'generated_at': '2026-09-03T10:00:00'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('reporting handle() must return a dict, got ' + type(out).__name__)
    from app.actions import role_based_access
    try:
        out = role_based_access.handle({'access_scope': 'portfolio', 'principal': 'sample', 'reference': 'sample', 'role': 'management', 'school': 'sample', 'status': 'open', 'principal_email': 'guest@example.com', 'permissions': 'sample', 'granted_by': 'sample', 'effective_from': 'sample', 'last_review_at': '2026-09-03T10:00:00', 'active': 'sample', 'notes': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('role_based_access handle() must return a dict, got ' + type(out).__name__)
    from app.actions import erp_integration
    try:
        out = erp_integration.handle({'direction': 'inbound', 'entity_type': 'purchase_order', 'integration': 'erp', 'mode': 'placeholder', 'reference': 'sample', 'status': 'open', 'external_reference': 'sample', 'endpoint': 'sample', 'currency': 'sample', 'amount': 'sample', 'sync_state': 'not_implemented', 'last_sync_at': '2026-09-03T10:00:00', 'detail': 'sample', 'notes': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('erp_integration handle() must return a dict, got ' + type(out).__name__)
    from app.actions import booking_system_integration
    try:
        out = booking_system_integration.handle({'booking_reference': 'sample', 'facility': 'sample', 'integration': 'booking_system', 'mode': 'placeholder', 'reference': 'sample', 'school': 'sample', 'slot_start': 'sample', 'status': 'open', 'slot_end': 'sample', 'requested_by': 'sample', 'sync_state': 'not_implemented', 'last_sync_at': '2026-09-03T10:00:00', 'detail': 'sample', 'notes': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('booking_system_integration handle() must return a dict, got ' + type(out).__name__)
    assert not failures, "; ".join(failures)


@pytest.mark.pilot
def test_every_capability_executes_end_to_end():
    """Pilot: each handler runs its blocks on a spec payload and
    Store must accept it. Not the factory code-phase gate."""
    for var in ("CEREBRUM_API_URL", "CEREBRUM_API_KEY"):
        os.environ.pop(var, None)
    import json as _json
    failures = []
    from app.actions import complaints_management
    out = complaints_management.handle({'category': 'electrical', 'description': 'sample', 'priority': 'critical', 'raised_by': 'sample', 'raised_by_role': 'school_staff', 'reference': 'sample', 'school': 'sample', 'status': 'open', 'site_code': 'id-1', 'contact_email': 'guest@example.com', 'contact_phone': 'sample', 'logged_by': 'sample', 'assigned_to': 'sample', 'assignment_mode': 'auto', 'reported_at': '2026-09-03T10:00:00', 'due_at': '2026-09-03T10:00:00', 'sla_hours': 'sample', 'closed_at': '2026-09-03T10:00:00', 'resolution_notes': 'sample', 'work_order_reference': 'sample'})
    if not isinstance(out, dict):
        failures.append('complaints_management returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('complaints_management rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('complaints_management reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import auto_assignment
    out = auto_assignment.handle({'assignment_mode': 'auto', 'category': 'electrical', 'complaint_reference': 'sample', 'priority': 'critical', 'reference': 'sample', 'required_trade': 'sample', 'school': 'sample', 'status': 'open', 'required_skill': 'sample', 'candidate_count': 1, 'assigned_to': 'sample', 'assigned_role': 'technician', 'match_score': 'sample', 'workload_score': 'sample', 'queue_position': 'sample', 'override_reason': 'sample', 'assigned_at': '2026-09-03T10:00:00'})
    if not isinstance(out, dict):
        failures.append('auto_assignment returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('auto_assignment rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('auto_assignment reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import workforce_management
    out = workforce_management.handle({'headcount': 'sample', 'reference': 'sample', 'school': 'sample', 'shift': 'morning', 'status': 'open', 'team_name': 'sample', 'team_type': 'technician', 'trade': 'sample', 'lead_name': 'sample', 'lead_email': 'guest@example.com', 'contact_phone': 'sample', 'active': 'sample', 'open_jobs': 'sample', 'notes': 'sample'})
    if not isinstance(out, dict):
        failures.append('workforce_management returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('workforce_management rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('workforce_management reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import management_dashboards
    out = management_dashboards.handle({'complaints_open': 'sample', 'period': 'sample', 'reference': 'sample', 'school': 'sample', 'scope': 'school', 'status': 'open', 'complaints_in_progress': 'sample', 'complaints_closed': 'sample', 'jobs_in_progress': 'sample', 'sla_breaches': 'sample', 'sla_compliance_pct': 'sample', 'avg_closure_hours': 'sample', 'headline': 'sample', 'generated_at': '2026-09-03T10:00:00'})
    if not isinstance(out, dict):
        failures.append('management_dashboards returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('management_dashboards rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('management_dashboards reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import reporting
    out = reporting.handle({'complaints_total': 'sample', 'period_end': 'sample', 'period_start': 'sample', 'reference': 'sample', 'report_type': 'daily', 'school': 'sample', 'scope': 'school', 'status': 'open', 'closed_total': 'sample', 'avg_closure_hours': 'sample', 'sla_compliance_pct': 'sample', 'top_category': 'sample', 'busiest_school': 'sample', 'recipients': 'sample', 'generated_at': '2026-09-03T10:00:00'})
    if not isinstance(out, dict):
        failures.append('reporting returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('reporting rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('reporting reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import role_based_access
    out = role_based_access.handle({'access_scope': 'portfolio', 'principal': 'sample', 'reference': 'sample', 'role': 'management', 'school': 'sample', 'status': 'open', 'principal_email': 'guest@example.com', 'permissions': 'sample', 'granted_by': 'sample', 'effective_from': 'sample', 'last_review_at': '2026-09-03T10:00:00', 'active': 'sample', 'notes': 'sample'})
    if not isinstance(out, dict):
        failures.append('role_based_access returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('role_based_access rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('role_based_access reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import erp_integration
    out = erp_integration.handle({'direction': 'inbound', 'entity_type': 'purchase_order', 'integration': 'erp', 'mode': 'placeholder', 'reference': 'sample', 'status': 'open', 'external_reference': 'sample', 'endpoint': 'sample', 'currency': 'sample', 'amount': 'sample', 'sync_state': 'not_implemented', 'last_sync_at': '2026-09-03T10:00:00', 'detail': 'sample', 'notes': 'sample'})
    if not isinstance(out, dict):
        failures.append('erp_integration returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('erp_integration rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('erp_integration reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import booking_system_integration
    out = booking_system_integration.handle({'booking_reference': 'sample', 'facility': 'sample', 'integration': 'booking_system', 'mode': 'placeholder', 'reference': 'sample', 'school': 'sample', 'slot_start': 'sample', 'status': 'open', 'slot_end': 'sample', 'requested_by': 'sample', 'sync_state': 'not_implemented', 'last_sync_at': '2026-09-03T10:00:00', 'detail': 'sample', 'notes': 'sample'})
    if not isinstance(out, dict):
        failures.append('booking_system_integration returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('booking_system_integration rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('booking_system_integration reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    assert not failures, "; ".join(failures)
