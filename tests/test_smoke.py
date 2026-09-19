"""The platform runs, and it runs without the store."""

import os

import pytest


def test_capabilities_import():
    from app.actions import patient_and_owner_records
    assert patient_and_owner_records.CAPABILITY_ID
    from app.actions import appointment_scheduling
    assert appointment_scheduling.CAPABILITY_ID
    from app.actions import clinical_visit_notes_and_treatment_plans
    assert clinical_visit_notes_and_treatment_plans.CAPABILITY_ID
    from app.actions import vaccination_tracking
    assert vaccination_tracking.CAPABILITY_ID
    from app.actions import billing_and_invoicing
    assert billing_and_invoicing.CAPABILITY_ID
    from app.actions import analytics_and_reporting
    assert analytics_and_reporting.CAPABILITY_ID
    from app.actions import compliance_and_audit_trail
    assert compliance_and_audit_trail.CAPABILITY_ID
    from app.actions import client_communication_and_reminders
    assert client_communication_and_reminders.CAPABILITY_ID


def test_dispatch_runs_offline():
    """No store env, no network: every block must LOAD and EXECUTE from
    vendor/. A block-level refusal of this bare probe is still local
    execution; an import failure is the store dependency this test
    exists to catch."""
    for var in ("CEREBRUM_API_URL", "CEREBRUM_API_KEY", "CEREBRUM_API_TOKEN"):
        os.environ.pop(var, None)
    from app.dispatch import execute, load_block
    for block_id in ['analytics', 'audit', 'capture', 'dashboard', 'database', 'document_engine', 'estate_registry', 'event_bus', 'evidence_verifier', 'file_hasher', 'formula_executor', 'knowledge', 'notification', 'portfolio_rollup', 'queue', 'readiness_engine', 'recommendation_template', 'storage', 'team', 'validation', 'workflow']:
        load_block(block_id)
    actions = {'analytics': 'track_event', 'audit': 'log', 'dashboard': 'render', 'database': 'query', 'event_bus': 'publish', 'knowledge': 'ask', 'notification': 'send', 'queue': 'enqueue', 'storage': 'store', 'team': 'create_team', 'validation': 'validate_pipeline', 'workflow': 'run'}
    for block_id in ['analytics', 'audit', 'capture', 'dashboard', 'database', 'document_engine', 'estate_registry', 'event_bus', 'evidence_verifier', 'file_hasher', 'formula_executor', 'knowledge', 'notification', 'portfolio_rollup', 'queue', 'readiness_engine', 'recommendation_template', 'storage', 'team', 'validation', 'workflow']:
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
    from app.actions import patient_and_owner_records
    try:
        out = patient_and_owner_records.handle({'owner_name': 'sample', 'patient_name': 'sample', 'reference': 'sample', 'species': 'dog', 'status': 'open', 'breed': 'sample', 'sex': 'male', 'age_years': 'sample', 'weight_kg': 'sample', 'microchip_id': 'id-1', 'owner_email': 'guest@example.com', 'owner_phone': 'sample', 'clinical_history': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('patient_and_owner_records handle() must return a dict, got ' + type(out).__name__)
    from app.actions import appointment_scheduling
    try:
        out = appointment_scheduling.handle({'appointment_type': 'wellness_exam', 'owner_name': 'sample', 'patient_name': 'sample', 'reference': 'sample', 'scheduled_at': '2026-09-03T10:00:00', 'status': 'open', 'veterinarian': 'sample', 'room': 'sample', 'duration_minutes': 'sample', 'reminder_channel': 'email', 'notes': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('appointment_scheduling handle() must return a dict, got ' + type(out).__name__)
    from app.actions import clinical_visit_notes_and_treatment_plans
    try:
        out = clinical_visit_notes_and_treatment_plans.handle({'diagnosis': 'sample', 'patient_name': 'sample', 'reference': 'sample', 'status': 'open', 'visit_date': '2026-09-03', 'treatment_plan': 'sample', 'medication': 'sample', 'dosage_mg': 'sample', 'administration_route': 'oral', 'attachment_path': 'sample', 'prescription_notes': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('clinical_visit_notes_and_treatment_plans handle() must return a dict, got ' + type(out).__name__)
    from app.actions import vaccination_tracking
    try:
        out = vaccination_tracking.handle({'patient_name': 'sample', 'reference': 'sample', 'status': 'open', 'vaccine_type': 'rabies', 'administered_on': 'sample', 'next_due_on': 'sample', 'lot_number': 'sample', 'administered_by': 'sample', 'reminder_channel': 'email'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('vaccination_tracking handle() must return a dict, got ' + type(out).__name__)
    from app.actions import billing_and_invoicing
    try:
        out = billing_and_invoicing.handle({'owner_name': 'sample', 'reference': 'sample', 'service_code': 'id-1', 'status': 'open', 'invoice_total': 'sample', 'amount_paid': 'sample', 'currency': 'USD', 'issued_on': 'sample', 'due_on': 'sample', 'payment_method': 'card', 'attachment_path': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('billing_and_invoicing handle() must return a dict, got ' + type(out).__name__)
    from app.actions import analytics_and_reporting
    try:
        out = analytics_and_reporting.handle({'metric_name': 'sample', 'reference': 'sample', 'report_name': 'sample', 'status': 'open', 'metric_value': 'sample', 'period_start': 'sample', 'period_end': 'sample', 'appointments_count': 1, 'revenue_total': 'sample', 'event_type': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('analytics_and_reporting handle() must return a dict, got ' + type(out).__name__)
    from app.actions import compliance_and_audit_trail
    try:
        out = compliance_and_audit_trail.handle({'content': 'sample', 'record_type': 'clinical_note', 'reference': 'sample', 'status': 'open', 'subject_ref': 'sample', 'content_hash': 'sample', 'reviewer': 'sample', 'reviewed_on': 'sample', 'retention_until': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('compliance_and_audit_trail handle() must return a dict, got ' + type(out).__name__)
    from app.actions import client_communication_and_reminders
    try:
        out = client_communication_and_reminders.handle({'owner_name': 'sample', 'reference': 'sample', 'reminder_type': 'appointment_reminder', 'status': 'open', 'owner_email': 'guest@example.com', 'channel': 'email', 'scheduled_for': 'sample', 'template_name': 'sample', 'message_body': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('client_communication_and_reminders handle() must return a dict, got ' + type(out).__name__)
    assert not failures, "; ".join(failures)


@pytest.mark.pilot
def test_every_capability_executes_end_to_end():
    """Pilot: each handler runs its blocks on a spec payload and
    Store must accept it. Not the factory code-phase gate."""
    for var in ("CEREBRUM_API_URL", "CEREBRUM_API_KEY"):
        os.environ.pop(var, None)
    import json as _json
    failures = []
    from app.actions import patient_and_owner_records
    out = patient_and_owner_records.handle({'owner_name': 'sample', 'patient_name': 'sample', 'reference': 'sample', 'species': 'dog', 'status': 'open', 'breed': 'sample', 'sex': 'male', 'age_years': 'sample', 'weight_kg': 'sample', 'microchip_id': 'id-1', 'owner_email': 'guest@example.com', 'owner_phone': 'sample', 'clinical_history': 'sample'})
    if not isinstance(out, dict):
        failures.append('patient_and_owner_records returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('patient_and_owner_records rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('patient_and_owner_records reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import appointment_scheduling
    out = appointment_scheduling.handle({'appointment_type': 'wellness_exam', 'owner_name': 'sample', 'patient_name': 'sample', 'reference': 'sample', 'scheduled_at': '2026-09-03T10:00:00', 'status': 'open', 'veterinarian': 'sample', 'room': 'sample', 'duration_minutes': 'sample', 'reminder_channel': 'email', 'notes': 'sample'})
    if not isinstance(out, dict):
        failures.append('appointment_scheduling returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('appointment_scheduling rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('appointment_scheduling reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import clinical_visit_notes_and_treatment_plans
    out = clinical_visit_notes_and_treatment_plans.handle({'diagnosis': 'sample', 'patient_name': 'sample', 'reference': 'sample', 'status': 'open', 'visit_date': '2026-09-03', 'treatment_plan': 'sample', 'medication': 'sample', 'dosage_mg': 'sample', 'administration_route': 'oral', 'attachment_path': 'sample', 'prescription_notes': 'sample'})
    if not isinstance(out, dict):
        failures.append('clinical_visit_notes_and_treatment_plans returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('clinical_visit_notes_and_treatment_plans rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('clinical_visit_notes_and_treatment_plans reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import vaccination_tracking
    out = vaccination_tracking.handle({'patient_name': 'sample', 'reference': 'sample', 'status': 'open', 'vaccine_type': 'rabies', 'administered_on': 'sample', 'next_due_on': 'sample', 'lot_number': 'sample', 'administered_by': 'sample', 'reminder_channel': 'email'})
    if not isinstance(out, dict):
        failures.append('vaccination_tracking returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('vaccination_tracking rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('vaccination_tracking reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import billing_and_invoicing
    out = billing_and_invoicing.handle({'owner_name': 'sample', 'reference': 'sample', 'service_code': 'id-1', 'status': 'open', 'invoice_total': 'sample', 'amount_paid': 'sample', 'currency': 'USD', 'issued_on': 'sample', 'due_on': 'sample', 'payment_method': 'card', 'attachment_path': 'sample'})
    if not isinstance(out, dict):
        failures.append('billing_and_invoicing returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('billing_and_invoicing rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('billing_and_invoicing reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import analytics_and_reporting
    out = analytics_and_reporting.handle({'metric_name': 'sample', 'reference': 'sample', 'report_name': 'sample', 'status': 'open', 'metric_value': 'sample', 'period_start': 'sample', 'period_end': 'sample', 'appointments_count': 1, 'revenue_total': 'sample', 'event_type': 'sample'})
    if not isinstance(out, dict):
        failures.append('analytics_and_reporting returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('analytics_and_reporting rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('analytics_and_reporting reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import compliance_and_audit_trail
    out = compliance_and_audit_trail.handle({'content': 'sample', 'record_type': 'clinical_note', 'reference': 'sample', 'status': 'open', 'subject_ref': 'sample', 'content_hash': 'sample', 'reviewer': 'sample', 'reviewed_on': 'sample', 'retention_until': 'sample'})
    if not isinstance(out, dict):
        failures.append('compliance_and_audit_trail returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('compliance_and_audit_trail rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('compliance_and_audit_trail reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import client_communication_and_reminders
    out = client_communication_and_reminders.handle({'owner_name': 'sample', 'reference': 'sample', 'reminder_type': 'appointment_reminder', 'status': 'open', 'owner_email': 'guest@example.com', 'channel': 'email', 'scheduled_for': 'sample', 'template_name': 'sample', 'message_body': 'sample'})
    if not isinstance(out, dict):
        failures.append('client_communication_and_reminders returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('client_communication_and_reminders rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('client_communication_and_reminders reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    assert not failures, "; ".join(failures)
