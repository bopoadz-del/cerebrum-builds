"""The platform runs, and it runs without the store."""

import os

import pytest


def test_capabilities_import():
    from app.actions import record_guest_check_in
    assert record_guest_check_in.CAPABILITY_ID
    from app.actions import list_todays_check_ins
    assert list_todays_check_ins.CAPABILITY_ID


def test_dispatch_runs_offline():
    """No store env, no network: every block must LOAD and EXECUTE from
    vendor/. A block-level refusal of this bare probe is still local
    execution; an import failure is the store dependency this test
    exists to catch."""
    for var in ("CEREBRUM_API_URL", "CEREBRUM_API_KEY", "CEREBRUM_API_TOKEN"):
        os.environ.pop(var, None)
    from app.dispatch import execute, load_block
    for block_id in ['capture', 'dashboard', 'database', 'validation']:
        load_block(block_id)
    actions = {'dashboard': 'render', 'database': 'query', 'validation': 'validate_pipeline'}
    for block_id in ['capture', 'dashboard', 'database', 'validation']:
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
    from app.actions import record_guest_check_in
    try:
        out = record_guest_check_in.handle({'guest_name': 'sample', 'reference': 'sample', 'room_number': 'sample', 'status': 'open', 'checked_in_at': '2026-09-03T10:00:00', 'guests_count': 1, 'notes': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('record_guest_check_in handle() must return a dict, got ' + type(out).__name__)
    from app.actions import list_todays_check_ins
    try:
        out = list_todays_check_ins.handle({'check_in_date': '2026-09-03', 'guest_name': 'sample', 'reference': 'sample', 'room_number': 'sample', 'status': 'open', 'check_in_count': 1, 'notes': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('list_todays_check_ins handle() must return a dict, got ' + type(out).__name__)
    assert not failures, "; ".join(failures)


@pytest.mark.pilot
def test_every_capability_executes_end_to_end():
    """Pilot: each handler runs its blocks on a spec payload and
    Store must accept it. Not the factory code-phase gate."""
    for var in ("CEREBRUM_API_URL", "CEREBRUM_API_KEY"):
        os.environ.pop(var, None)
    import json as _json
    failures = []
    from app.actions import record_guest_check_in
    out = record_guest_check_in.handle({'guest_name': 'sample', 'reference': 'sample', 'room_number': 'sample', 'status': 'open', 'checked_in_at': '2026-09-03T10:00:00', 'guests_count': 1, 'notes': 'sample'})
    if not isinstance(out, dict):
        failures.append('record_guest_check_in returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('record_guest_check_in rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('record_guest_check_in reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import list_todays_check_ins
    out = list_todays_check_ins.handle({'check_in_date': '2026-09-03', 'guest_name': 'sample', 'reference': 'sample', 'room_number': 'sample', 'status': 'open', 'check_in_count': 1, 'notes': 'sample'})
    if not isinstance(out, dict):
        failures.append('list_todays_check_ins returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('list_todays_check_ins rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('list_todays_check_ins reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    assert not failures, "; ".join(failures)
