"""The platform runs, and it runs without the store."""

import os

import pytest


def test_capabilities_import():
    from app.actions import patient_records
    assert patient_records.CAPABILITY_ID
    from app.actions import appointment_scheduling
    assert appointment_scheduling.CAPABILITY_ID
    from app.actions import treatment_records
    assert treatment_records.CAPABILITY_ID
    from app.actions import invoicing
    assert invoicing.CAPABILITY_ID
    from app.actions import recall_reminders
    assert recall_reminders.CAPABILITY_ID
    from app.actions import staff_roles_permissions
    assert staff_roles_permissions.CAPABILITY_ID
    from app.actions import clinic_dashboard
    assert clinic_dashboard.CAPABILITY_ID


def test_dispatch_runs_offline():
    """No store env, no network: every block must LOAD and EXECUTE from
    vendor/. A block-level refusal of this bare probe is still local
    execution; an import failure is the store dependency this test
    exists to catch."""
    for var in ("CEREBRUM_API_URL", "CEREBRUM_API_KEY", "CEREBRUM_API_TOKEN"):
        os.environ.pop(var, None)
    from app.dispatch import execute, load_block
    for block_id in ['analytics', 'audit', 'dashboard', 'database', 'document_engine', 'formula_executor', 'notification', 'queue', 'storage', 'team', 'validation', 'workflow']:
        load_block(block_id)
    actions = {'analytics': 'track_event', 'audit': 'log', 'dashboard': 'render', 'database': 'query', 'notification': 'send', 'queue': 'enqueue', 'storage': 'store', 'team': 'create_team', 'validation': 'validate_pipeline', 'workflow': 'run'}
    for block_id in ['analytics', 'audit', 'dashboard', 'database', 'document_engine', 'formula_executor', 'notification', 'queue', 'storage', 'team', 'validation', 'workflow']:
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
    from app.actions import patient_records
    try:
        out = patient_records.handle({'patient_name': 'sample', 'reference': 'sample', 'status': 'open'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('patient_records handle() must return a dict, got ' + type(out).__name__)
    from app.actions import appointment_scheduling
    try:
        out = appointment_scheduling.handle({'patient_name': 'sample', 'reference': 'sample', 'status': 'open'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('appointment_scheduling handle() must return a dict, got ' + type(out).__name__)
    from app.actions import treatment_records
    try:
        out = treatment_records.handle({'patient_name': 'sample', 'patient_nameprocedure': 'sample', 'reference': 'sample', 'status': 'open'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('treatment_records handle() must return a dict, got ' + type(out).__name__)
    from app.actions import invoicing
    try:
        out = invoicing.handle({'patient_name': 'sample', 'reference': 'sample', 'status': 'open'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('invoicing handle() must return a dict, got ' + type(out).__name__)
    from app.actions import recall_reminders
    try:
        out = recall_reminders.handle({'patient_name': 'sample', 'reference': 'sample', 'status': 'open'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('recall_reminders handle() must return a dict, got ' + type(out).__name__)
    from app.actions import staff_roles_permissions
    try:
        out = staff_roles_permissions.handle({'staff_name': 'sample', 'staff_namestaff_role': 'sample', 'staff_role': 'sample', 'reference': 'sample', 'status': 'open'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('staff_roles_permissions handle() must return a dict, got ' + type(out).__name__)
    from app.actions import clinic_dashboard
    try:
        out = clinic_dashboard.handle({'reference': 'sample', 'status': 'open'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('clinic_dashboard handle() must return a dict, got ' + type(out).__name__)
    assert not failures, "; ".join(failures)


@pytest.mark.pilot
def test_every_capability_executes_end_to_end():
    """Pilot: each handler runs its blocks on a spec payload and
    Store must accept it. Not the factory code-phase gate."""
    for var in ("CEREBRUM_API_URL", "CEREBRUM_API_KEY"):
        os.environ.pop(var, None)
    import json as _json
    failures = []
    from app.actions import patient_records
    out = patient_records.handle({'patient_name': 'sample', 'reference': 'sample', 'status': 'open'})
    if not isinstance(out, dict):
        failures.append('patient_records returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('patient_records rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('patient_records reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import appointment_scheduling
    out = appointment_scheduling.handle({'patient_name': 'sample', 'reference': 'sample', 'status': 'open'})
    if not isinstance(out, dict):
        failures.append('appointment_scheduling returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('appointment_scheduling rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('appointment_scheduling reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import treatment_records
    out = treatment_records.handle({'patient_name': 'sample', 'patient_nameprocedure': 'sample', 'reference': 'sample', 'status': 'open'})
    if not isinstance(out, dict):
        failures.append('treatment_records returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('treatment_records rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('treatment_records reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import invoicing
    out = invoicing.handle({'patient_name': 'sample', 'reference': 'sample', 'status': 'open'})
    if not isinstance(out, dict):
        failures.append('invoicing returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('invoicing rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('invoicing reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import recall_reminders
    out = recall_reminders.handle({'patient_name': 'sample', 'reference': 'sample', 'status': 'open'})
    if not isinstance(out, dict):
        failures.append('recall_reminders returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('recall_reminders rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('recall_reminders reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import staff_roles_permissions
    out = staff_roles_permissions.handle({'staff_name': 'sample', 'staff_namestaff_role': 'sample', 'staff_role': 'sample', 'reference': 'sample', 'status': 'open'})
    if not isinstance(out, dict):
        failures.append('staff_roles_permissions returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('staff_roles_permissions rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('staff_roles_permissions reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import clinic_dashboard
    out = clinic_dashboard.handle({'reference': 'sample', 'status': 'open'})
    if not isinstance(out, dict):
        failures.append('clinic_dashboard returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('clinic_dashboard rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('clinic_dashboard reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    assert not failures, "; ".join(failures)
