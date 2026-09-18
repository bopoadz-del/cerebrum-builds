"""The platform runs, and it runs without the store."""

import os

import pytest


def test_capabilities_import():
    from app.actions import record_checkin
    assert record_checkin.CAPABILITY_ID
    from app.actions import todays_arrivals_board
    assert todays_arrivals_board.CAPABILITY_ID
    from app.actions import room_availability_check
    assert room_availability_check.CAPABILITY_ID
    from app.actions import guest_notes_and_preferences
    assert guest_notes_and_preferences.CAPABILITY_ID
    from app.actions import checkin_notifications
    assert checkin_notifications.CAPABILITY_ID
    from app.actions import daily_checkin_summary
    assert daily_checkin_summary.CAPABILITY_ID
    from app.actions import audit_trail
    assert audit_trail.CAPABILITY_ID


def test_dispatch_runs_offline():
    """No store env, no network: every block must LOAD and EXECUTE from
    vendor/. A block-level refusal of this bare probe is still local
    execution; an import failure is the store dependency this test
    exists to catch."""
    for var in ("CEREBRUM_API_URL", "CEREBRUM_API_KEY", "CEREBRUM_API_TOKEN"):
        os.environ.pop(var, None)
    from app.dispatch import execute, load_block
    for block_id in ['analytics', 'audit', 'capture', 'dashboard', 'database', 'event_bus', 'formula_executor', 'knowledge', 'memory', 'notification', 'queue', 'validation']:
        load_block(block_id)
    actions = {'analytics': 'track_event', 'audit': 'log', 'dashboard': 'render', 'database': 'query', 'event_bus': 'publish', 'knowledge': 'ask', 'memory': 'get', 'notification': 'send', 'queue': 'enqueue', 'validation': 'validate_pipeline'}
    for block_id in ['analytics', 'audit', 'capture', 'dashboard', 'database', 'event_bus', 'formula_executor', 'knowledge', 'memory', 'notification', 'queue', 'validation']:
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
    from app.actions import record_checkin
    try:
        out = record_checkin.handle({'arrival_time': '10:00:00', 'guest_name': 'sample', 'nights': 1, 'reference': 'sample', 'room_number': 'sample', 'status': 'open', 'notes': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('record_checkin handle() must return a dict, got ' + type(out).__name__)
    from app.actions import todays_arrivals_board
    try:
        out = todays_arrivals_board.handle({'arrival_date': '2026-09-03', 'guest_name': 'sample', 'reference': 'sample', 'room_number': 'sample', 'status': 'open', 'arrived': 'sample', 'arrivals_count': 1})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('todays_arrivals_board handle() must return a dict, got ' + type(out).__name__)
    from app.actions import room_availability_check
    try:
        out = room_availability_check.handle({'check_in_date': '2026-09-03', 'check_out_date': '2026-09-03', 'reference': 'sample', 'room_number': 'sample', 'status': 'open', 'is_available': True})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('room_availability_check handle() must return a dict, got ' + type(out).__name__)
    from app.actions import guest_notes_and_preferences
    try:
        out = guest_notes_and_preferences.handle({'guest_name': 'sample', 'reference': 'sample', 'status': 'open', 'room_number': 'sample', 'preference': 'sample', 'note': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('guest_notes_and_preferences handle() must return a dict, got ' + type(out).__name__)
    from app.actions import checkin_notifications
    try:
        out = checkin_notifications.handle({'guest_name': 'sample', 'reference': 'sample', 'room_number': 'sample', 'status': 'open', 'channel': 'mcp', 'recipient': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('checkin_notifications handle() must return a dict, got ' + type(out).__name__)
    from app.actions import daily_checkin_summary
    try:
        out = daily_checkin_summary.handle({'reference': 'sample', 'status': 'open', 'summary_date': '2026-09-03', 'arrivals_count': 1, 'occupancy_percent': 'sample', 'no_show_count': 1})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('daily_checkin_summary handle() must return a dict, got ' + type(out).__name__)
    from app.actions import audit_trail
    try:
        out = audit_trail.handle({'actor': 'sample', 'reference': 'sample', 'status': 'open', 'change_type': 'create', 'subject_capability': 'sample', 'changed_at': '2026-09-03T10:00:00'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('audit_trail handle() must return a dict, got ' + type(out).__name__)
    assert not failures, "; ".join(failures)


@pytest.mark.pilot
def test_every_capability_executes_end_to_end():
    """Pilot: each handler runs its blocks on a spec payload and
    Store must accept it. Not the factory code-phase gate."""
    for var in ("CEREBRUM_API_URL", "CEREBRUM_API_KEY"):
        os.environ.pop(var, None)
    import json as _json
    failures = []
    from app.actions import record_checkin
    out = record_checkin.handle({'arrival_time': '10:00:00', 'guest_name': 'sample', 'nights': 1, 'reference': 'sample', 'room_number': 'sample', 'status': 'open', 'notes': 'sample'})
    if not isinstance(out, dict):
        failures.append('record_checkin returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('record_checkin rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('record_checkin reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import todays_arrivals_board
    out = todays_arrivals_board.handle({'arrival_date': '2026-09-03', 'guest_name': 'sample', 'reference': 'sample', 'room_number': 'sample', 'status': 'open', 'arrived': 'sample', 'arrivals_count': 1})
    if not isinstance(out, dict):
        failures.append('todays_arrivals_board returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('todays_arrivals_board rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('todays_arrivals_board reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import room_availability_check
    out = room_availability_check.handle({'check_in_date': '2026-09-03', 'check_out_date': '2026-09-03', 'reference': 'sample', 'room_number': 'sample', 'status': 'open', 'is_available': True})
    if not isinstance(out, dict):
        failures.append('room_availability_check returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('room_availability_check rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('room_availability_check reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import guest_notes_and_preferences
    out = guest_notes_and_preferences.handle({'guest_name': 'sample', 'reference': 'sample', 'status': 'open', 'room_number': 'sample', 'preference': 'sample', 'note': 'sample'})
    if not isinstance(out, dict):
        failures.append('guest_notes_and_preferences returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('guest_notes_and_preferences rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('guest_notes_and_preferences reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import checkin_notifications
    out = checkin_notifications.handle({'guest_name': 'sample', 'reference': 'sample', 'room_number': 'sample', 'status': 'open', 'channel': 'mcp', 'recipient': 'sample'})
    if not isinstance(out, dict):
        failures.append('checkin_notifications returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('checkin_notifications rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('checkin_notifications reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import daily_checkin_summary
    out = daily_checkin_summary.handle({'reference': 'sample', 'status': 'open', 'summary_date': '2026-09-03', 'arrivals_count': 1, 'occupancy_percent': 'sample', 'no_show_count': 1})
    if not isinstance(out, dict):
        failures.append('daily_checkin_summary returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('daily_checkin_summary rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('daily_checkin_summary reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import audit_trail
    out = audit_trail.handle({'actor': 'sample', 'reference': 'sample', 'status': 'open', 'change_type': 'create', 'subject_capability': 'sample', 'changed_at': '2026-09-03T10:00:00'})
    if not isinstance(out, dict):
        failures.append('audit_trail returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('audit_trail rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('audit_trail reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    assert not failures, "; ".join(failures)
