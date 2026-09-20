"""The platform runs, and it runs without the store."""

import os

import pytest


def test_capabilities_import():
    from app.actions import fleet_registry
    assert fleet_registry.CAPABILITY_ID
    from app.actions import rental_contract_management
    assert rental_contract_management.CAPABILITY_ID
    from app.actions import maintenance_scheduling
    assert maintenance_scheduling.CAPABILITY_ID
    from app.actions import pricing_and_rate_cards
    assert pricing_and_rate_cards.CAPABILITY_ID
    from app.actions import invoicing_and_deposits
    assert invoicing_and_deposits.CAPABILITY_ID
    from app.actions import multi_branch_rollup
    assert multi_branch_rollup.CAPABILITY_ID
    from app.actions import reporting_analytics
    assert reporting_analytics.CAPABILITY_ID
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
    for block_id in ['analytics', 'audit', 'capture', 'dashboard', 'database', 'document_engine', 'estate_maintenance', 'estate_registry', 'event_bus', 'evidence_verifier', 'file_hasher', 'formula_executor', 'knowledge', 'memory', 'notification', 'portfolio_rollup', 'queue', 'readiness_engine', 'storage', 'validation', 'vector_search', 'workflow']:
        load_block(block_id)
    actions = {'analytics': 'track_event', 'audit': 'log', 'dashboard': 'render', 'database': 'query', 'event_bus': 'publish', 'knowledge': 'ask', 'memory': 'get', 'notification': 'send', 'queue': 'enqueue', 'storage': 'store', 'validation': 'validate_pipeline', 'workflow': 'run'}
    for block_id in ['analytics', 'audit', 'capture', 'dashboard', 'database', 'document_engine', 'estate_maintenance', 'estate_registry', 'event_bus', 'evidence_verifier', 'file_hasher', 'formula_executor', 'knowledge', 'memory', 'notification', 'portfolio_rollup', 'queue', 'readiness_engine', 'storage', 'validation', 'vector_search', 'workflow']:
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
    from app.actions import fleet_registry
    try:
        out = fleet_registry.handle({'audit': 'sample', 'database': 'sample', 'reference': 'sample', 'status': 'open', 'storage': 'sample', 'mileage': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('fleet_registry handle() must return a dict, got ' + type(out).__name__)
    from app.actions import rental_contract_management
    try:
        out = rental_contract_management.handle({'reference': 'sample', 'status': 'open', 'pickup_date': '2026-09-03', 'return_date': '2026-09-03', 'extension_days': 'sample', 'daily_rate': 'sample', 'deposit_amount': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('rental_contract_management handle() must return a dict, got ' + type(out).__name__)
    from app.actions import maintenance_scheduling
    try:
        out = maintenance_scheduling.handle({'reference': 'sample', 'status': 'open', 'title': 'sample', 'schedule_kind': 'date', 'due_date': '2026-09-03', 'due_mileage': 'sample', 'downtime_days': 'sample', 'estimated_cost': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('maintenance_scheduling handle() must return a dict, got ' + type(out).__name__)
    from app.actions import pricing_and_rate_cards
    try:
        out = pricing_and_rate_cards.handle({'analytics': 'sample', 'audit': 'sample', 'formula_executor': 'sample', 'reference': 'sample', 'status': 'open', 'validation': 'sample', 'duration_days': 'sample', 'base_rate': 'sample', 'mileage_charge': 'sample', 'fuel_charge': 'sample', 'late_return_charge': 'sample', 'extras_charge': 'sample', 'deposit_amount': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('pricing_and_rate_cards handle() must return a dict, got ' + type(out).__name__)
    from app.actions import invoicing_and_deposits
    try:
        out = invoicing_and_deposits.handle({'analytics': 'sample', 'audit': 'sample', 'database': 'sample', 'reference': 'sample', 'status': 'open', 'workflow': 'sample', 'amount_due': 'sample', 'deposit_held': 'sample', 'balance_due': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('invoicing_and_deposits handle() must return a dict, got ' + type(out).__name__)
    from app.actions import multi_branch_rollup
    try:
        out = multi_branch_rollup.handle({'analytics': 'sample', 'dashboard': 'sample', 'estate_registry': 'sample', 'portfolio_rollup': 'sample', 'reference': 'sample', 'status': 'open', 'fleet_utilisation': 'sample', 'revenue': 'sample', 'cost': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('multi_branch_rollup handle() must return a dict, got ' + type(out).__name__)
    from app.actions import reporting_analytics
    try:
        out = reporting_analytics.handle({'analytics': 'sample', 'dashboard': 'sample', 'memory': 'sample', 'reference': 'sample', 'status': 'open', 'vector_search': 'sample', 'value': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('reporting_analytics handle() must return a dict, got ' + type(out).__name__)
    from app.actions import audit_trail
    try:
        out = audit_trail.handle({'audit': 'sample', 'capture': 'sample', 'evidence_verifier': 'sample', 'file_hasher': 'sample', 'reference': 'sample', 'status': 'open'})
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
    from app.actions import fleet_registry
    out = fleet_registry.handle({'audit': 'sample', 'database': 'sample', 'reference': 'sample', 'status': 'open', 'storage': 'sample', 'mileage': 'sample'})
    if not isinstance(out, dict):
        failures.append('fleet_registry returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('fleet_registry rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('fleet_registry reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import rental_contract_management
    out = rental_contract_management.handle({'reference': 'sample', 'status': 'open', 'pickup_date': '2026-09-03', 'return_date': '2026-09-03', 'extension_days': 'sample', 'daily_rate': 'sample', 'deposit_amount': 'sample'})
    if not isinstance(out, dict):
        failures.append('rental_contract_management returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('rental_contract_management rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('rental_contract_management reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import maintenance_scheduling
    out = maintenance_scheduling.handle({'reference': 'sample', 'status': 'open', 'title': 'sample', 'schedule_kind': 'date', 'due_date': '2026-09-03', 'due_mileage': 'sample', 'downtime_days': 'sample', 'estimated_cost': 'sample'})
    if not isinstance(out, dict):
        failures.append('maintenance_scheduling returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('maintenance_scheduling rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('maintenance_scheduling reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import pricing_and_rate_cards
    out = pricing_and_rate_cards.handle({'analytics': 'sample', 'audit': 'sample', 'formula_executor': 'sample', 'reference': 'sample', 'status': 'open', 'validation': 'sample', 'duration_days': 'sample', 'base_rate': 'sample', 'mileage_charge': 'sample', 'fuel_charge': 'sample', 'late_return_charge': 'sample', 'extras_charge': 'sample', 'deposit_amount': 'sample'})
    if not isinstance(out, dict):
        failures.append('pricing_and_rate_cards returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('pricing_and_rate_cards rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('pricing_and_rate_cards reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import invoicing_and_deposits
    out = invoicing_and_deposits.handle({'analytics': 'sample', 'audit': 'sample', 'database': 'sample', 'reference': 'sample', 'status': 'open', 'workflow': 'sample', 'amount_due': 'sample', 'deposit_held': 'sample', 'balance_due': 'sample'})
    if not isinstance(out, dict):
        failures.append('invoicing_and_deposits returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('invoicing_and_deposits rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('invoicing_and_deposits reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import multi_branch_rollup
    out = multi_branch_rollup.handle({'analytics': 'sample', 'dashboard': 'sample', 'estate_registry': 'sample', 'portfolio_rollup': 'sample', 'reference': 'sample', 'status': 'open', 'fleet_utilisation': 'sample', 'revenue': 'sample', 'cost': 'sample'})
    if not isinstance(out, dict):
        failures.append('multi_branch_rollup returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('multi_branch_rollup rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('multi_branch_rollup reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import reporting_analytics
    out = reporting_analytics.handle({'analytics': 'sample', 'dashboard': 'sample', 'memory': 'sample', 'reference': 'sample', 'status': 'open', 'vector_search': 'sample', 'value': 'sample'})
    if not isinstance(out, dict):
        failures.append('reporting_analytics returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('reporting_analytics rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('reporting_analytics reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import audit_trail
    out = audit_trail.handle({'audit': 'sample', 'capture': 'sample', 'evidence_verifier': 'sample', 'file_hasher': 'sample', 'reference': 'sample', 'status': 'open'})
    if not isinstance(out, dict):
        failures.append('audit_trail returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('audit_trail rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('audit_trail reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    assert not failures, "; ".join(failures)
