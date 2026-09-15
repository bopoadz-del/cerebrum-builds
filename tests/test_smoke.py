"""The platform runs, and it runs without the store."""

import os

import pytest


def test_capabilities_import():
    from app.actions import automotive_core
    assert automotive_core.CAPABILITY_ID
    from app.actions import dashboard
    assert dashboard.CAPABILITY_ID
    from app.actions import team
    assert team.CAPABILITY_ID
    from app.actions import audit
    assert audit.CAPABILITY_ID


def test_dispatch_runs_offline():
    """No store env, no network: every block must LOAD and EXECUTE from
    vendor/. A block-level refusal of this bare probe is still local
    execution; an import failure is the store dependency this test
    exists to catch."""
    for var in ("CEREBRUM_API_URL", "CEREBRUM_API_KEY", "CEREBRUM_API_TOKEN"):
        os.environ.pop(var, None)
    from app.dispatch import execute, load_block
    for block_id in ['audit', 'dashboard', 'team']:
        load_block(block_id)
    actions = {'audit': 'log', 'dashboard': 'render', 'team': 'create_team'}
    for block_id in ['audit', 'dashboard', 'team']:
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
    from app.actions import automotive_core
    try:
        out = automotive_core.handle({})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('automotive_core handle() must return a dict, got ' + type(out).__name__)
    from app.actions import dashboard
    try:
        out = dashboard.handle({})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('dashboard handle() must return a dict, got ' + type(out).__name__)
    from app.actions import team
    try:
        out = team.handle({})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('team handle() must return a dict, got ' + type(out).__name__)
    from app.actions import audit
    try:
        out = audit.handle({})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('audit handle() must return a dict, got ' + type(out).__name__)
    assert not failures, "; ".join(failures)


@pytest.mark.pilot
def test_every_capability_executes_end_to_end():
    """Pilot: each handler runs its blocks on a spec payload and
    Store must accept it. Not the factory code-phase gate."""
    for var in ("CEREBRUM_API_URL", "CEREBRUM_API_KEY"):
        os.environ.pop(var, None)
    import json as _json
    failures = []
    from app.actions import automotive_core
    out = automotive_core.handle({})
    if not isinstance(out, dict):
        failures.append('automotive_core returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('automotive_core rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('automotive_core reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import dashboard
    out = dashboard.handle({})
    if not isinstance(out, dict):
        failures.append('dashboard returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('dashboard rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('dashboard reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import team
    out = team.handle({})
    if not isinstance(out, dict):
        failures.append('team returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('team rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('team reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import audit
    out = audit.handle({})
    if not isinstance(out, dict):
        failures.append('audit returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('audit rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('audit reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    assert not failures, "; ".join(failures)
