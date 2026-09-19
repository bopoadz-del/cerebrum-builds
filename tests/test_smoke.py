"""The platform runs, and it runs without the store."""

import os

import pytest


def test_capabilities_import():
    from app.actions import stock_inventory_management
    assert stock_inventory_management.CAPABILITY_ID
    from app.actions import product_pricing
    assert product_pricing.CAPABILITY_ID
    from app.actions import delivery_dispatch_tracking
    assert delivery_dispatch_tracking.CAPABILITY_ID
    from app.actions import fleet_cost_tracking
    assert fleet_cost_tracking.CAPABILITY_ID
    from app.actions import management_reporting_dashboard
    assert management_reporting_dashboard.CAPABILITY_ID
    from app.actions import user_roles_workforce
    assert user_roles_workforce.CAPABILITY_ID
    from app.actions import document_knowledge_qa
    assert document_knowledge_qa.CAPABILITY_ID
    from app.actions import procedures_readiness_and_audit_trail
    assert procedures_readiness_and_audit_trail.CAPABILITY_ID


def test_dispatch_runs_offline():
    """No store env, no network: every block must LOAD and EXECUTE from
    vendor/. A block-level refusal of this bare probe is still local
    execution; an import failure is the store dependency this test
    exists to catch."""
    for var in ("CEREBRUM_API_URL", "CEREBRUM_API_KEY", "CEREBRUM_API_TOKEN"):
        os.environ.pop(var, None)
    from app.dispatch import execute, load_block
    for block_id in ['analytics', 'audit', 'capture', 'dashboard', 'database', 'document_engine', 'event_bus', 'evidence_verifier', 'file_hasher', 'formula_executor', 'knowledge', 'notification', 'portfolio_rollup', 'queue', 'readiness_engine', 'spec_analyzer', 'storage', 'team', 'validation', 'vector_search', 'workflow']:
        load_block(block_id)
    actions = {'analytics': 'track_event', 'audit': 'log', 'dashboard': 'render', 'database': 'query', 'event_bus': 'publish', 'knowledge': 'ask', 'notification': 'send', 'queue': 'enqueue', 'storage': 'store', 'team': 'create_team', 'validation': 'validate_pipeline', 'workflow': 'run'}
    for block_id in ['analytics', 'audit', 'capture', 'dashboard', 'database', 'document_engine', 'event_bus', 'evidence_verifier', 'file_hasher', 'formula_executor', 'knowledge', 'notification', 'portfolio_rollup', 'queue', 'readiness_engine', 'spec_analyzer', 'storage', 'team', 'validation', 'vector_search', 'workflow']:
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
    from app.actions import stock_inventory_management
    try:
        out = stock_inventory_management.handle({})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('stock_inventory_management handle() must return a dict, got ' + type(out).__name__)
    from app.actions import product_pricing
    try:
        out = product_pricing.handle({})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('product_pricing handle() must return a dict, got ' + type(out).__name__)
    from app.actions import delivery_dispatch_tracking
    try:
        out = delivery_dispatch_tracking.handle({})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('delivery_dispatch_tracking handle() must return a dict, got ' + type(out).__name__)
    from app.actions import fleet_cost_tracking
    try:
        out = fleet_cost_tracking.handle({})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('fleet_cost_tracking handle() must return a dict, got ' + type(out).__name__)
    from app.actions import management_reporting_dashboard
    try:
        out = management_reporting_dashboard.handle({})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('management_reporting_dashboard handle() must return a dict, got ' + type(out).__name__)
    from app.actions import user_roles_workforce
    try:
        out = user_roles_workforce.handle({})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('user_roles_workforce handle() must return a dict, got ' + type(out).__name__)
    from app.actions import document_knowledge_qa
    try:
        out = document_knowledge_qa.handle({})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('document_knowledge_qa handle() must return a dict, got ' + type(out).__name__)
    from app.actions import procedures_readiness_and_audit_trail
    try:
        out = procedures_readiness_and_audit_trail.handle({})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('procedures_readiness_and_audit_trail handle() must return a dict, got ' + type(out).__name__)
    assert not failures, "; ".join(failures)


@pytest.mark.pilot
def test_every_capability_executes_end_to_end():
    """Pilot: each handler runs its blocks on a spec payload and
    Store must accept it. Not the factory code-phase gate."""
    for var in ("CEREBRUM_API_URL", "CEREBRUM_API_KEY"):
        os.environ.pop(var, None)
    import json as _json
    failures = []
    from app.actions import stock_inventory_management
    out = stock_inventory_management.handle({})
    if not isinstance(out, dict):
        failures.append('stock_inventory_management returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('stock_inventory_management rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('stock_inventory_management reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import product_pricing
    out = product_pricing.handle({})
    if not isinstance(out, dict):
        failures.append('product_pricing returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('product_pricing rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('product_pricing reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import delivery_dispatch_tracking
    out = delivery_dispatch_tracking.handle({})
    if not isinstance(out, dict):
        failures.append('delivery_dispatch_tracking returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('delivery_dispatch_tracking rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('delivery_dispatch_tracking reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import fleet_cost_tracking
    out = fleet_cost_tracking.handle({})
    if not isinstance(out, dict):
        failures.append('fleet_cost_tracking returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('fleet_cost_tracking rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('fleet_cost_tracking reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import management_reporting_dashboard
    out = management_reporting_dashboard.handle({})
    if not isinstance(out, dict):
        failures.append('management_reporting_dashboard returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('management_reporting_dashboard rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('management_reporting_dashboard reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import user_roles_workforce
    out = user_roles_workforce.handle({})
    if not isinstance(out, dict):
        failures.append('user_roles_workforce returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('user_roles_workforce rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('user_roles_workforce reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import document_knowledge_qa
    out = document_knowledge_qa.handle({})
    if not isinstance(out, dict):
        failures.append('document_knowledge_qa returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('document_knowledge_qa rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('document_knowledge_qa reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import procedures_readiness_and_audit_trail
    out = procedures_readiness_and_audit_trail.handle({})
    if not isinstance(out, dict):
        failures.append('procedures_readiness_and_audit_trail returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('procedures_readiness_and_audit_trail rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('procedures_readiness_and_audit_trail reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    assert not failures, "; ".join(failures)
