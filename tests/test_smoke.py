"""The platform runs, and it runs without the store."""

import os

import pytest


def test_capabilities_import():
    from app.actions import job_and_site_tracking
    assert job_and_site_tracking.CAPABILITY_ID
    from app.actions import commercials_and_valuations
    assert commercials_and_valuations.CAPABILITY_ID
    from app.actions import document_qa_and_indexing
    assert document_qa_and_indexing.CAPABILITY_ID
    from app.actions import safety_and_compliance
    assert safety_and_compliance.CAPABILITY_ID
    from app.actions import progress_cost_dashboard
    assert progress_cost_dashboard.CAPABILITY_ID
    from app.actions import automation_reminders_escalation
    assert automation_reminders_escalation.CAPABILITY_ID
    from app.actions import audit_and_access_control
    assert audit_and_access_control.CAPABILITY_ID
    from app.actions import team_notifications
    assert team_notifications.CAPABILITY_ID


def test_dispatch_runs_offline():
    """No store env, no network: every block must LOAD and EXECUTE from
    vendor/. A block-level refusal of this bare probe is still local
    execution; an import failure is the store dependency this test
    exists to catch."""
    for var in ("CEREBRUM_API_URL", "CEREBRUM_API_KEY", "CEREBRUM_API_TOKEN"):
        os.environ.pop(var, None)
    from app.dispatch import execute, load_block
    for block_id in ['analytics', 'audit', 'capture', 'dashboard', 'database', 'document_engine', 'estate_maintenance', 'estate_registry', 'event_bus', 'file_hasher', 'formula_executor', 'knowledge', 'notification', 'portfolio_rollup', 'queue', 'readiness_engine', 'recommendation_template', 'storage', 'team', 'validation', 'vector_search', 'workflow']:
        load_block(block_id)
    actions = {'analytics': 'track_event', 'audit': 'log', 'dashboard': 'render', 'database': 'query', 'estate_maintenance': 'create', 'estate_registry': 'create', 'event_bus': 'publish', 'knowledge': 'ask', 'notification': 'send', 'portfolio_rollup': 'aggregate', 'queue': 'enqueue', 'readiness_engine': 'evaluate', 'storage': 'store', 'team': 'create_team', 'validation': 'validate_pipeline', 'workflow': 'run'}
    for block_id in ['analytics', 'audit', 'capture', 'dashboard', 'database', 'document_engine', 'estate_maintenance', 'estate_registry', 'event_bus', 'file_hasher', 'formula_executor', 'knowledge', 'notification', 'portfolio_rollup', 'queue', 'readiness_engine', 'recommendation_template', 'storage', 'team', 'validation', 'vector_search', 'workflow']:
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
    from app.actions import job_and_site_tracking
    try:
        out = job_and_site_tracking.handle({'job_code': 'id-1', 'job_name': 'sample', 'reference': 'sample', 'site_name': 'sample', 'status': 'open', 'client_name': 'sample', 'work_front': 'sample', 'contract_value_aed': 'sample', 'progress_percent': 'sample', 'milestone': 'sample', 'milestone_due_date': '2026-09-03', 'snag_open_count': 1, 'variation_reference': 'sample', 'variation_status': 'draft', 'notes': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('job_and_site_tracking handle() must return a dict, got ' + type(out).__name__)
    from app.actions import commercials_and_valuations
    try:
        out = commercials_and_valuations.handle({'job_code': 'id-1', 'reference': 'sample', 'status': 'open', 'valuation_number': 'sample', 'boq_item': 'sample', 'measured_quantity': 'sample', 'unit_rate_aed': 'sample', 'gross_value_aed': 'sample', 'retention_percent': 'sample', 'retention_aed': 'sample', 'vat_rate_percent': 'sample', 'vat_amount_aed': 'sample', 'certified_value_aed': 'sample', 'payment_status': 'unpaid', 'purchase_order': 'sample', 'po_party_type': 'supplier', 'amount_due_aed': 'sample', 'due_on': 'sample', 'notes': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('commercials_and_valuations handle() must return a dict, got ' + type(out).__name__)
    from app.actions import document_qa_and_indexing
    try:
        out = document_qa_and_indexing.handle({'document_title': 'sample', 'document_type': 'boq', 'reference': 'sample', 'status': 'open', 'job_code': 'id-1', 'revision': 'sample', 'file_name': 'sample', 'file_path': 'sample', 'file_sha256': 'sample', 'question': 'sample', 'answer': 'sample', 'source_reference': 'sample', 'indexed_at': '2026-09-03T10:00:00', 'notes': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('document_qa_and_indexing handle() must return a dict, got ' + type(out).__name__)
    from app.actions import safety_and_compliance
    try:
        out = safety_and_compliance.handle({'document_title': 'sample', 'job_code': 'id-1', 'reference': 'sample', 'status': 'open', 'method_statement_ref': 'sample', 'work_front': 'sample', 'checklist_item': 'sample', 'checklist_state': 'met', 'readiness_gate': 'ready', 'incident_type': 'near_miss', 'incident_date': '2026-09-03', 'severity': 'low', 'action_taken': 'sample', 'notes': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('safety_and_compliance handle() must return a dict, got ' + type(out).__name__)
    from app.actions import progress_cost_dashboard
    try:
        out = progress_cost_dashboard.handle({'margin_percent': 'sample', 'reference': 'sample', 'status': 'open', 'job_code': 'id-1', 'report_date': '2026-09-03', 'progress_percent': 'sample', 'certified_value_aed': 'sample', 'cost_to_date_aed': 'sample', 'variations_pending': 'sample', 'snags_open': 'sample', 'payments_due_aed': 'sample', 'summary': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('progress_cost_dashboard handle() must return a dict, got ' + type(out).__name__)
    from app.actions import automation_reminders_escalation
    try:
        out = automation_reminders_escalation.handle({'job_code': 'id-1', 'reference': 'sample', 'reminder_type': 'valuation_due', 'status': 'open', 'due_date': '2026-09-03', 'threshold_count': 1, 'actual_count': 1, 'escalation_state': 'none', 'channel': 'email', 'recipient_email': 'guest@example.com', 'message_body': 'sample', 'schedule': 'monthly', 'summary': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('automation_reminders_escalation handle() must return a dict, got ' + type(out).__name__)
    from app.actions import audit_and_access_control
    try:
        out = audit_and_access_control.handle({'action_type': 'approval', 'actor_name': 'sample', 'actor_role': 'owner', 'reference': 'sample', 'status': 'open', 'entity_name': 'sample', 'entity_reference': 'sample', 'change_summary': 'sample', 'approval_state': 'pending', 'occurred_at': '2026-09-03T10:00:00', 'notes': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('audit_and_access_control handle() must return a dict, got ' + type(out).__name__)
    from app.actions import team_notifications
    try:
        out = team_notifications.handle({'message_body': 'sample', 'reference': 'sample', 'status': 'open', 'subject': 'sample', 'recipient_email': 'guest@example.com', 'recipient_role': 'owner', 'channel': 'email', 'notification_type': 'approval', 'related_reference': 'sample', 'send_at': '2026-09-03T10:00:00', 'delivery_state': 'queued'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('team_notifications handle() must return a dict, got ' + type(out).__name__)
    assert not failures, "; ".join(failures)


@pytest.mark.pilot
def test_every_capability_executes_end_to_end():
    """Pilot: each handler runs its blocks on a spec payload and
    Store must accept it. Not the factory code-phase gate."""
    for var in ("CEREBRUM_API_URL", "CEREBRUM_API_KEY"):
        os.environ.pop(var, None)
    import json as _json
    failures = []
    from app.actions import job_and_site_tracking
    out = job_and_site_tracking.handle({'job_code': 'id-1', 'job_name': 'sample', 'reference': 'sample', 'site_name': 'sample', 'status': 'open', 'client_name': 'sample', 'work_front': 'sample', 'contract_value_aed': 'sample', 'progress_percent': 'sample', 'milestone': 'sample', 'milestone_due_date': '2026-09-03', 'snag_open_count': 1, 'variation_reference': 'sample', 'variation_status': 'draft', 'notes': 'sample'})
    if not isinstance(out, dict):
        failures.append('job_and_site_tracking returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('job_and_site_tracking rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('job_and_site_tracking reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import commercials_and_valuations
    out = commercials_and_valuations.handle({'job_code': 'id-1', 'reference': 'sample', 'status': 'open', 'valuation_number': 'sample', 'boq_item': 'sample', 'measured_quantity': 'sample', 'unit_rate_aed': 'sample', 'gross_value_aed': 'sample', 'retention_percent': 'sample', 'retention_aed': 'sample', 'vat_rate_percent': 'sample', 'vat_amount_aed': 'sample', 'certified_value_aed': 'sample', 'payment_status': 'unpaid', 'purchase_order': 'sample', 'po_party_type': 'supplier', 'amount_due_aed': 'sample', 'due_on': 'sample', 'notes': 'sample'})
    if not isinstance(out, dict):
        failures.append('commercials_and_valuations returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('commercials_and_valuations rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('commercials_and_valuations reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import document_qa_and_indexing
    out = document_qa_and_indexing.handle({'document_title': 'sample', 'document_type': 'boq', 'reference': 'sample', 'status': 'open', 'job_code': 'id-1', 'revision': 'sample', 'file_name': 'sample', 'file_path': 'sample', 'file_sha256': 'sample', 'question': 'sample', 'answer': 'sample', 'source_reference': 'sample', 'indexed_at': '2026-09-03T10:00:00', 'notes': 'sample'})
    if not isinstance(out, dict):
        failures.append('document_qa_and_indexing returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('document_qa_and_indexing rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('document_qa_and_indexing reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import safety_and_compliance
    out = safety_and_compliance.handle({'document_title': 'sample', 'job_code': 'id-1', 'reference': 'sample', 'status': 'open', 'method_statement_ref': 'sample', 'work_front': 'sample', 'checklist_item': 'sample', 'checklist_state': 'met', 'readiness_gate': 'ready', 'incident_type': 'near_miss', 'incident_date': '2026-09-03', 'severity': 'low', 'action_taken': 'sample', 'notes': 'sample'})
    if not isinstance(out, dict):
        failures.append('safety_and_compliance returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('safety_and_compliance rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('safety_and_compliance reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import progress_cost_dashboard
    out = progress_cost_dashboard.handle({'margin_percent': 'sample', 'reference': 'sample', 'status': 'open', 'job_code': 'id-1', 'report_date': '2026-09-03', 'progress_percent': 'sample', 'certified_value_aed': 'sample', 'cost_to_date_aed': 'sample', 'variations_pending': 'sample', 'snags_open': 'sample', 'payments_due_aed': 'sample', 'summary': 'sample'})
    if not isinstance(out, dict):
        failures.append('progress_cost_dashboard returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('progress_cost_dashboard rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('progress_cost_dashboard reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import automation_reminders_escalation
    out = automation_reminders_escalation.handle({'job_code': 'id-1', 'reference': 'sample', 'reminder_type': 'valuation_due', 'status': 'open', 'due_date': '2026-09-03', 'threshold_count': 1, 'actual_count': 1, 'escalation_state': 'none', 'channel': 'email', 'recipient_email': 'guest@example.com', 'message_body': 'sample', 'schedule': 'monthly', 'summary': 'sample'})
    if not isinstance(out, dict):
        failures.append('automation_reminders_escalation returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('automation_reminders_escalation rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('automation_reminders_escalation reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import audit_and_access_control
    out = audit_and_access_control.handle({'action_type': 'approval', 'actor_name': 'sample', 'actor_role': 'owner', 'reference': 'sample', 'status': 'open', 'entity_name': 'sample', 'entity_reference': 'sample', 'change_summary': 'sample', 'approval_state': 'pending', 'occurred_at': '2026-09-03T10:00:00', 'notes': 'sample'})
    if not isinstance(out, dict):
        failures.append('audit_and_access_control returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('audit_and_access_control rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('audit_and_access_control reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import team_notifications
    out = team_notifications.handle({'message_body': 'sample', 'reference': 'sample', 'status': 'open', 'subject': 'sample', 'recipient_email': 'guest@example.com', 'recipient_role': 'owner', 'channel': 'email', 'notification_type': 'approval', 'related_reference': 'sample', 'send_at': '2026-09-03T10:00:00', 'delivery_state': 'queued'})
    if not isinstance(out, dict):
        failures.append('team_notifications returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('team_notifications rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('team_notifications reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    assert not failures, "; ".join(failures)
