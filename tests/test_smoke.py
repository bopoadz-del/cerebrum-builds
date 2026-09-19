"""The platform runs, and it runs without the store."""

import os

import pytest


def test_capabilities_import():
    from app.actions import patient_visit_records
    assert patient_visit_records.CAPABILITY_ID
    from app.actions import appointment_scheduling
    assert appointment_scheduling.CAPABILITY_ID
    from app.actions import todays_appointment_list
    assert todays_appointment_list.CAPABILITY_ID
    from app.actions import day_before_email_reminders
    assert day_before_email_reminders.CAPABILITY_ID
    from app.actions import patient_directory
    assert patient_directory.CAPABILITY_ID
    from app.actions import clinical_history_search
    assert clinical_history_search.CAPABILITY_ID
    from app.actions import role_based_access
    assert role_based_access.CAPABILITY_ID


def test_dispatch_runs_offline():
    """No store env, no network: every block must LOAD and EXECUTE from
    vendor/. A block-level refusal of this bare probe is still local
    execution; an import failure is the store dependency this test
    exists to catch."""
    for var in ("CEREBRUM_API_URL", "CEREBRUM_API_KEY", "CEREBRUM_API_TOKEN"):
        os.environ.pop(var, None)
    from app.dispatch import execute, load_block
    for block_id in ['analytics', 'audit', 'capture', 'dashboard', 'database', 'event_bus', 'notification', 'queue', 'team', 'validation', 'workflow']:
        load_block(block_id)
    actions = {'analytics': 'track_event', 'audit': 'log', 'dashboard': 'render', 'database': 'query', 'event_bus': 'publish', 'notification': 'send', 'queue': 'enqueue', 'team': 'create_team', 'validation': 'validate_pipeline', 'workflow': 'run'}
    for block_id in ['analytics', 'audit', 'capture', 'dashboard', 'database', 'event_bus', 'notification', 'queue', 'team', 'validation', 'workflow']:
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
    from app.actions import patient_visit_records
    try:
        out = patient_visit_records.handle({'patient_name': 'sample', 'procedure': 'sample', 'reference': 'sample', 'status': 'open', 'tooth': 'sample', 'fee': 'sample', 'visit_date': '2026-09-03', 'provider': 'sample', 'clinical_notes': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('patient_visit_records handle() must return a dict, got ' + type(out).__name__)
    from app.actions import appointment_scheduling
    try:
        out = appointment_scheduling.handle({'appointment_type': 'exam', 'patient_name': 'sample', 'reference': 'sample', 'scheduled_at': '2026-09-03T10:00:00', 'status': 'open', 'patient_email': 'guest@example.com', 'provider': 'sample', 'chair_room': 'sample', 'duration_minutes': 'sample', 'reminder_channel': 'email', 'notes': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('appointment_scheduling handle() must return a dict, got ' + type(out).__name__)
    from app.actions import todays_appointment_list
    try:
        out = todays_appointment_list.handle({'list_date': '2026-09-03', 'patient_name': 'sample', 'reference': 'sample', 'status': 'open', 'provider': 'sample', 'procedure': 'sample', 'appointment_time': '10:00:00', 'appointment_status': 'scheduled', 'chair_room': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('todays_appointment_list handle() must return a dict, got ' + type(out).__name__)
    from app.actions import day_before_email_reminders
    try:
        out = day_before_email_reminders.handle({'patient_email': 'guest@example.com', 'patient_name': 'sample', 'reference': 'sample', 'reminder_date': '2026-09-03', 'status': 'open', 'appointment_at': '2026-09-03T10:00:00', 'reminder_channel': 'email', 'message_body': 'sample', 'delivery_state': 'queued'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('day_before_email_reminders handle() must return a dict, got ' + type(out).__name__)
    from app.actions import patient_directory
    try:
        out = patient_directory.handle({'patient_name': 'sample', 'reference': 'sample', 'status': 'open', 'patient_email': 'guest@example.com', 'patient_phone': 'sample', 'date_of_birth': 'sample', 'primary_provider': 'sample', 'notes': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('patient_directory handle() must return a dict, got ' + type(out).__name__)
    from app.actions import clinical_history_search
    try:
        out = clinical_history_search.handle({'patient_name': 'sample', 'reference': 'sample', 'status': 'open', 'tooth': 'sample', 'procedure': 'sample', 'provider': 'sample', 'visit_date': '2026-09-03', 'date_from': 'sample', 'date_to': 'sample', 'search_notes': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('clinical_history_search handle() must return a dict, got ' + type(out).__name__)
    from app.actions import role_based_access
    try:
        out = role_based_access.handle({'reference': 'sample', 'staff_name': 'sample', 'staff_role': 'dentist', 'status': 'open', 'staff_email': 'guest@example.com', 'permission_scope': 'sample', 'active_from': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('role_based_access handle() must return a dict, got ' + type(out).__name__)
    assert not failures, "; ".join(failures)


@pytest.mark.pilot
def test_every_capability_executes_end_to_end():
    """Pilot: each handler runs its blocks on a spec payload and
    Store must accept it. Not the factory code-phase gate."""
    for var in ("CEREBRUM_API_URL", "CEREBRUM_API_KEY"):
        os.environ.pop(var, None)
    import json as _json
    failures = []
    from app.actions import patient_visit_records
    out = patient_visit_records.handle({'patient_name': 'sample', 'procedure': 'sample', 'reference': 'sample', 'status': 'open', 'tooth': 'sample', 'fee': 'sample', 'visit_date': '2026-09-03', 'provider': 'sample', 'clinical_notes': 'sample'})
    if not isinstance(out, dict):
        failures.append('patient_visit_records returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('patient_visit_records rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('patient_visit_records reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import appointment_scheduling
    out = appointment_scheduling.handle({'appointment_type': 'exam', 'patient_name': 'sample', 'reference': 'sample', 'scheduled_at': '2026-09-03T10:00:00', 'status': 'open', 'patient_email': 'guest@example.com', 'provider': 'sample', 'chair_room': 'sample', 'duration_minutes': 'sample', 'reminder_channel': 'email', 'notes': 'sample'})
    if not isinstance(out, dict):
        failures.append('appointment_scheduling returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('appointment_scheduling rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('appointment_scheduling reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import todays_appointment_list
    out = todays_appointment_list.handle({'list_date': '2026-09-03', 'patient_name': 'sample', 'reference': 'sample', 'status': 'open', 'provider': 'sample', 'procedure': 'sample', 'appointment_time': '10:00:00', 'appointment_status': 'scheduled', 'chair_room': 'sample'})
    if not isinstance(out, dict):
        failures.append('todays_appointment_list returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('todays_appointment_list rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('todays_appointment_list reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import day_before_email_reminders
    out = day_before_email_reminders.handle({'patient_email': 'guest@example.com', 'patient_name': 'sample', 'reference': 'sample', 'reminder_date': '2026-09-03', 'status': 'open', 'appointment_at': '2026-09-03T10:00:00', 'reminder_channel': 'email', 'message_body': 'sample', 'delivery_state': 'queued'})
    if not isinstance(out, dict):
        failures.append('day_before_email_reminders returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('day_before_email_reminders rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('day_before_email_reminders reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import patient_directory
    out = patient_directory.handle({'patient_name': 'sample', 'reference': 'sample', 'status': 'open', 'patient_email': 'guest@example.com', 'patient_phone': 'sample', 'date_of_birth': 'sample', 'primary_provider': 'sample', 'notes': 'sample'})
    if not isinstance(out, dict):
        failures.append('patient_directory returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('patient_directory rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('patient_directory reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import clinical_history_search
    out = clinical_history_search.handle({'patient_name': 'sample', 'reference': 'sample', 'status': 'open', 'tooth': 'sample', 'procedure': 'sample', 'provider': 'sample', 'visit_date': '2026-09-03', 'date_from': 'sample', 'date_to': 'sample', 'search_notes': 'sample'})
    if not isinstance(out, dict):
        failures.append('clinical_history_search returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('clinical_history_search rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('clinical_history_search reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import role_based_access
    out = role_based_access.handle({'reference': 'sample', 'staff_name': 'sample', 'staff_role': 'dentist', 'status': 'open', 'staff_email': 'guest@example.com', 'permission_scope': 'sample', 'active_from': 'sample'})
    if not isinstance(out, dict):
        failures.append('role_based_access returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('role_based_access rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('role_based_access reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    assert not failures, "; ".join(failures)
