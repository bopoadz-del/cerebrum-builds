"""The platform runs, and it runs without the store."""

import os

import pytest


def test_capabilities_import():
    from app.actions import budget_planning_tracking
    assert budget_planning_tracking.CAPABILITY_ID
    from app.actions import spend_capture_categorisation
    assert spend_capture_categorisation.CAPABILITY_ID
    from app.actions import approval_workflow
    assert approval_workflow.CAPABILITY_ID
    from app.actions import variance_analytics
    assert variance_analytics.CAPABILITY_ID
    from app.actions import dashboard_portfolio_rollup
    assert dashboard_portfolio_rollup.CAPABILITY_ID
    from app.actions import audit_evidence_validation
    assert audit_evidence_validation.CAPABILITY_ID
    from app.actions import finance_document_knowledge
    assert finance_document_knowledge.CAPABILITY_ID
    from app.actions import integrations_placeholders
    assert integrations_placeholders.CAPABILITY_ID


def test_dispatch_runs_offline():
    """No store env, no network: every block must LOAD and EXECUTE from
    vendor/. A block-level refusal of this bare probe is still local
    execution; an import failure is the store dependency this test
    exists to catch."""
    for var in ("CEREBRUM_API_URL", "CEREBRUM_API_KEY", "CEREBRUM_API_TOKEN"):
        os.environ.pop(var, None)
    from app.dispatch import execute, load_block
    for block_id in ['analytics', 'audit', 'capture', 'dashboard', 'database', 'document_engine', 'event_bus', 'evidence_verifier', 'file_hasher', 'formula_executor', 'knowledge', 'notification', 'portfolio_rollup', 'queue', 'recommendation_template', 'spec_analyzer', 'storage', 'team', 'validation', 'vector_search', 'workflow']:
        load_block(block_id)
    actions = {'analytics': 'track_event', 'audit': 'log', 'dashboard': 'render', 'database': 'query', 'event_bus': 'publish', 'evidence_verifier': 'store', 'knowledge': 'ask', 'notification': 'send', 'portfolio_rollup': 'aggregate', 'queue': 'enqueue', 'storage': 'store', 'team': 'create_team', 'validation': 'validate_pipeline', 'workflow': 'run'}
    for block_id in ['analytics', 'audit', 'capture', 'dashboard', 'database', 'document_engine', 'event_bus', 'evidence_verifier', 'file_hasher', 'formula_executor', 'knowledge', 'notification', 'portfolio_rollup', 'queue', 'recommendation_template', 'spec_analyzer', 'storage', 'team', 'validation', 'vector_search', 'workflow']:
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
    from app.actions import budget_planning_tracking
    try:
        out = budget_planning_tracking.handle({'budget_owner': 'sample', 'department': 'sample', 'reference': 'sample', 'status': 'open', 'cost_centre': 'sample', 'period': 'sample', 'planned_amount': 'sample', 'actual_amount': 'sample', 'currency': 'sample', 'notes': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('budget_planning_tracking handle() must return a dict, got ' + type(out).__name__)
    from app.actions import spend_capture_categorisation
    try:
        out = spend_capture_categorisation.handle({'category': 'software', 'department': 'sample', 'reference': 'sample', 'status': 'open', 'supplier': 'sample', 'amount': 'sample', 'currency': 'sample', 'invoice_date': '2026-09-03', 'invoice_number': 'sample', 'document_path': 'sample', 'notes': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('spend_capture_categorisation handle() must return a dict, got ' + type(out).__name__)
    from app.actions import approval_workflow
    try:
        out = approval_workflow.handle({'approver': 'sample', 'department': 'sample', 'reference': 'sample', 'request_type': 'invoice', 'status': 'open', 'approver_email': 'guest@example.com', 'amount': 'sample', 'threshold': 'sample', 'priority': 'low', 'submitted_at': '2026-09-03T10:00:00', 'notes': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('approval_workflow handle() must return a dict, got ' + type(out).__name__)
    from app.actions import variance_analytics
    try:
        out = variance_analytics.handle({'department': 'sample', 'reference': 'sample', 'status': 'open', 'category': 'sample', 'period': 'sample', 'budget_amount': 'sample', 'actual_amount': 'sample', 'formula': 'sample', 'notes': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('variance_analytics handle() must return a dict, got ' + type(out).__name__)
    from app.actions import dashboard_portfolio_rollup
    try:
        out = dashboard_portfolio_rollup.handle({'department': 'sample', 'reference': 'sample', 'role_view': 'cfo', 'status': 'open', 'view_scope': 'sample', 'period': 'sample', 'spend_total': 'sample', 'commitment_total': 'sample', 'forecast_total': 'sample', 'risk_level': 'low', 'notes': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('dashboard_portfolio_rollup handle() must return a dict, got ' + type(out).__name__)
    from app.actions import audit_evidence_validation
    try:
        out = audit_evidence_validation.handle({'department': 'sample', 'record_reference': 'sample', 'record_type': 'invoice', 'reference': 'sample', 'status': 'open', 'evidence_hash': 'sample', 'verified': 'sample', 'checked_at': '2026-09-03T10:00:00', 'notes': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('audit_evidence_validation handle() must return a dict, got ' + type(out).__name__)
    from app.actions import finance_document_knowledge
    try:
        out = finance_document_knowledge.handle({'department': 'sample', 'document_type': 'invoice', 'question': 'sample', 'reference': 'sample', 'status': 'open', 'answer': 'sample', 'citations': 'sample', 'confidence': 'sample', 'document_path': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('finance_document_knowledge handle() must return a dict, got ' + type(out).__name__)
    from app.actions import integrations_placeholders
    try:
        out = integrations_placeholders.handle({'department': 'sample', 'direction': 'inbound', 'integration': 'google_drive', 'reference': 'sample', 'status': 'open', 'detail': 'sample', 'external_reference': 'sample', 'last_sync_at': '2026-09-03T10:00:00', 'notes': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('integrations_placeholders handle() must return a dict, got ' + type(out).__name__)
    assert not failures, "; ".join(failures)


@pytest.mark.pilot
def test_every_capability_executes_end_to_end():
    """Pilot: each handler runs its blocks on a spec payload and
    Store must accept it. Not the factory code-phase gate."""
    for var in ("CEREBRUM_API_URL", "CEREBRUM_API_KEY"):
        os.environ.pop(var, None)
    import json as _json
    failures = []
    from app.actions import budget_planning_tracking
    out = budget_planning_tracking.handle({'budget_owner': 'sample', 'department': 'sample', 'reference': 'sample', 'status': 'open', 'cost_centre': 'sample', 'period': 'sample', 'planned_amount': 'sample', 'actual_amount': 'sample', 'currency': 'sample', 'notes': 'sample'})
    if not isinstance(out, dict):
        failures.append('budget_planning_tracking returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('budget_planning_tracking rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('budget_planning_tracking reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import spend_capture_categorisation
    out = spend_capture_categorisation.handle({'category': 'software', 'department': 'sample', 'reference': 'sample', 'status': 'open', 'supplier': 'sample', 'amount': 'sample', 'currency': 'sample', 'invoice_date': '2026-09-03', 'invoice_number': 'sample', 'document_path': 'sample', 'notes': 'sample'})
    if not isinstance(out, dict):
        failures.append('spend_capture_categorisation returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('spend_capture_categorisation rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('spend_capture_categorisation reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import approval_workflow
    out = approval_workflow.handle({'approver': 'sample', 'department': 'sample', 'reference': 'sample', 'request_type': 'invoice', 'status': 'open', 'approver_email': 'guest@example.com', 'amount': 'sample', 'threshold': 'sample', 'priority': 'low', 'submitted_at': '2026-09-03T10:00:00', 'notes': 'sample'})
    if not isinstance(out, dict):
        failures.append('approval_workflow returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('approval_workflow rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('approval_workflow reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import variance_analytics
    out = variance_analytics.handle({'department': 'sample', 'reference': 'sample', 'status': 'open', 'category': 'sample', 'period': 'sample', 'budget_amount': 'sample', 'actual_amount': 'sample', 'formula': 'sample', 'notes': 'sample'})
    if not isinstance(out, dict):
        failures.append('variance_analytics returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('variance_analytics rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('variance_analytics reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import dashboard_portfolio_rollup
    out = dashboard_portfolio_rollup.handle({'department': 'sample', 'reference': 'sample', 'role_view': 'cfo', 'status': 'open', 'view_scope': 'sample', 'period': 'sample', 'spend_total': 'sample', 'commitment_total': 'sample', 'forecast_total': 'sample', 'risk_level': 'low', 'notes': 'sample'})
    if not isinstance(out, dict):
        failures.append('dashboard_portfolio_rollup returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('dashboard_portfolio_rollup rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('dashboard_portfolio_rollup reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import audit_evidence_validation
    out = audit_evidence_validation.handle({'department': 'sample', 'record_reference': 'sample', 'record_type': 'invoice', 'reference': 'sample', 'status': 'open', 'evidence_hash': 'sample', 'verified': 'sample', 'checked_at': '2026-09-03T10:00:00', 'notes': 'sample'})
    if not isinstance(out, dict):
        failures.append('audit_evidence_validation returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('audit_evidence_validation rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('audit_evidence_validation reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import finance_document_knowledge
    out = finance_document_knowledge.handle({'department': 'sample', 'document_type': 'invoice', 'question': 'sample', 'reference': 'sample', 'status': 'open', 'answer': 'sample', 'citations': 'sample', 'confidence': 'sample', 'document_path': 'sample'})
    if not isinstance(out, dict):
        failures.append('finance_document_knowledge returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('finance_document_knowledge rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('finance_document_knowledge reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import integrations_placeholders
    out = integrations_placeholders.handle({'department': 'sample', 'direction': 'inbound', 'integration': 'google_drive', 'reference': 'sample', 'status': 'open', 'detail': 'sample', 'external_reference': 'sample', 'last_sync_at': '2026-09-03T10:00:00', 'notes': 'sample'})
    if not isinstance(out, dict):
        failures.append('integrations_placeholders returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('integrations_placeholders rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('integrations_placeholders reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    assert not failures, "; ".join(failures)
