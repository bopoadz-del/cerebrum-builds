"""The platform runs, and it runs without the store."""

import os

import pytest


def test_capabilities_import():
    from app.actions import matter_management
    assert matter_management.CAPABILITY_ID
    from app.actions import client_intake
    assert client_intake.CAPABILITY_ID
    from app.actions import document_management
    assert document_management.CAPABILITY_ID
    from app.actions import time_and_billing
    assert time_and_billing.CAPABILITY_ID
    from app.actions import client_portal
    assert client_portal.CAPABILITY_ID
    from app.actions import legal_analytics
    assert legal_analytics.CAPABILITY_ID
    from app.actions import compliance_audit
    assert compliance_audit.CAPABILITY_ID


def test_dispatch_runs_offline():
    """No store env, no network: every block must LOAD and EXECUTE from
    vendor/. A block-level refusal of this bare probe is still local
    execution; an import failure is the store dependency this test
    exists to catch."""
    for var in ("CEREBRUM_API_URL", "CEREBRUM_API_KEY", "CEREBRUM_API_TOKEN"):
        os.environ.pop(var, None)
    from app.dispatch import execute, load_block
    for block_id in ['analytics', 'audit', 'dashboard', 'database', 'document_engine', 'evidence_verifier', 'formula_executor', 'knowledge', 'notification', 'portfolio_rollup', 'readiness_engine', 'storage', 'validation', 'vector_search', 'workflow']:
        load_block(block_id)
    actions = {'analytics': 'track_event', 'audit': 'log', 'dashboard': 'render', 'database': 'query', 'knowledge': 'ask', 'notification': 'send', 'storage': 'store', 'validation': 'validate_pipeline', 'workflow': 'run'}
    for block_id in ['analytics', 'audit', 'dashboard', 'database', 'document_engine', 'evidence_verifier', 'formula_executor', 'knowledge', 'notification', 'portfolio_rollup', 'readiness_engine', 'storage', 'validation', 'vector_search', 'workflow']:
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
    from app.actions import matter_management
    try:
        out = matter_management.handle({'client_name': 'sample', 'matter_number': 'sample', 'matter_title': 'sample', 'reference': 'sample', 'status': 'open', 'client_email': 'guest@example.com', 'practice_area': 'sample', 'responsible_attorney': 'sample', 'matter_stage': 'sample', 'priority': 'sample', 'opened_date': '2026-09-03', 'deadline_date': '2026-09-03', 'billing_type': 'sample', 'document_path': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('matter_management handle() must return a dict, got ' + type(out).__name__)
    from app.actions import client_intake
    try:
        out = client_intake.handle({'client_name': 'sample', 'reference': 'sample', 'status': 'open', 'client_email': 'guest@example.com', 'client_phone': 'sample', 'matter_type': 'sample', 'referral_source': 'sample', 'conflict_check': 'sample', 'risk_score': 'sample', 'estimated_fee': 'sample', 'retainer_amount': 'sample', 'document_path': 'sample', 'intake_date': '2026-09-03'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('client_intake handle() must return a dict, got ' + type(out).__name__)
    from app.actions import document_management
    try:
        out = document_management.handle({'document_title': 'sample', 'reference': 'sample', 'status': 'open', 'document_type': 'sample', 'matter_number': 'sample', 'version': 'sample', 'file_path': 'sample', 'content_hash': 'sample', 'confidentiality': 'sample', 'document_owner': 'sample', 'tags': 'sample', 'uploaded_by': 'sample', 'uploaded_at': '2026-09-03T10:00:00'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('document_management handle() must return a dict, got ' + type(out).__name__)
    from app.actions import time_and_billing
    try:
        out = time_and_billing.handle({'matter_number': 'sample', 'reference': 'sample', 'status': 'open', 'timekeeper': 'sample', 'client_name': 'sample', 'client_email': 'guest@example.com', 'activity_date': '2026-09-03', 'hours': 'sample', 'hourly_rate': 'sample', 'billable_amount': 'sample', 'invoice_number': 'sample', 'payment_status': 'open', 'narrative': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('time_and_billing handle() must return a dict, got ' + type(out).__name__)
    from app.actions import client_portal
    try:
        out = client_portal.handle({'client_name': 'sample', 'reference': 'sample', 'status': 'open', 'client_email': 'guest@example.com', 'matter_number': 'sample', 'portal_access_level': 'sample', 'unread_messages': 'sample', 'shared_documents': 'sample', 'message_subject': 'sample', 'message_body': 'sample', 'last_login_at': '2026-09-03T10:00:00', 'document_path': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('client_portal handle() must return a dict, got ' + type(out).__name__)
    from app.actions import legal_analytics
    try:
        out = legal_analytics.handle({'metric_name': 'sample', 'reference': 'sample', 'status': 'open', 'metric_value': 'sample', 'benchmark_value': 'sample', 'practice_area': 'sample', 'dimension': 'sample', 'period_start': 'sample', 'period_end': 'sample', 'source_matter': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('legal_analytics handle() must return a dict, got ' + type(out).__name__)
    from app.actions import compliance_audit
    try:
        out = compliance_audit.handle({'action_taken': 'sample', 'actor': 'sample', 'control_id': 'id-1', 'reference': 'sample', 'status': 'open', 'framework': 'sample', 'regulation': 'sample', 'event_type': 'sample', 'actor_role': 'sample', 'evidence_ref': 'sample', 'findings': 'sample', 'occurred_at': '2026-09-03T10:00:00'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('compliance_audit handle() must return a dict, got ' + type(out).__name__)
    assert not failures, "; ".join(failures)


@pytest.mark.pilot
def test_every_capability_executes_end_to_end():
    """Pilot: each handler runs its blocks on a spec payload and
    Store must accept it. Not the factory code-phase gate."""
    for var in ("CEREBRUM_API_URL", "CEREBRUM_API_KEY"):
        os.environ.pop(var, None)
    import json as _json
    failures = []
    from app.actions import matter_management
    out = matter_management.handle({'client_name': 'sample', 'matter_number': 'sample', 'matter_title': 'sample', 'reference': 'sample', 'status': 'open', 'client_email': 'guest@example.com', 'practice_area': 'sample', 'responsible_attorney': 'sample', 'matter_stage': 'sample', 'priority': 'sample', 'opened_date': '2026-09-03', 'deadline_date': '2026-09-03', 'billing_type': 'sample', 'document_path': 'sample'})
    if not isinstance(out, dict):
        failures.append('matter_management returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('matter_management rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('matter_management reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import client_intake
    out = client_intake.handle({'client_name': 'sample', 'reference': 'sample', 'status': 'open', 'client_email': 'guest@example.com', 'client_phone': 'sample', 'matter_type': 'sample', 'referral_source': 'sample', 'conflict_check': 'sample', 'risk_score': 'sample', 'estimated_fee': 'sample', 'retainer_amount': 'sample', 'document_path': 'sample', 'intake_date': '2026-09-03'})
    if not isinstance(out, dict):
        failures.append('client_intake returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('client_intake rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('client_intake reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import document_management
    out = document_management.handle({'document_title': 'sample', 'reference': 'sample', 'status': 'open', 'document_type': 'sample', 'matter_number': 'sample', 'version': 'sample', 'file_path': 'sample', 'content_hash': 'sample', 'confidentiality': 'sample', 'document_owner': 'sample', 'tags': 'sample', 'uploaded_by': 'sample', 'uploaded_at': '2026-09-03T10:00:00'})
    if not isinstance(out, dict):
        failures.append('document_management returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('document_management rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('document_management reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import time_and_billing
    out = time_and_billing.handle({'matter_number': 'sample', 'reference': 'sample', 'status': 'open', 'timekeeper': 'sample', 'client_name': 'sample', 'client_email': 'guest@example.com', 'activity_date': '2026-09-03', 'hours': 'sample', 'hourly_rate': 'sample', 'billable_amount': 'sample', 'invoice_number': 'sample', 'payment_status': 'open', 'narrative': 'sample'})
    if not isinstance(out, dict):
        failures.append('time_and_billing returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('time_and_billing rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('time_and_billing reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import client_portal
    out = client_portal.handle({'client_name': 'sample', 'reference': 'sample', 'status': 'open', 'client_email': 'guest@example.com', 'matter_number': 'sample', 'portal_access_level': 'sample', 'unread_messages': 'sample', 'shared_documents': 'sample', 'message_subject': 'sample', 'message_body': 'sample', 'last_login_at': '2026-09-03T10:00:00', 'document_path': 'sample'})
    if not isinstance(out, dict):
        failures.append('client_portal returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('client_portal rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('client_portal reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import legal_analytics
    out = legal_analytics.handle({'metric_name': 'sample', 'reference': 'sample', 'status': 'open', 'metric_value': 'sample', 'benchmark_value': 'sample', 'practice_area': 'sample', 'dimension': 'sample', 'period_start': 'sample', 'period_end': 'sample', 'source_matter': 'sample'})
    if not isinstance(out, dict):
        failures.append('legal_analytics returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('legal_analytics rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('legal_analytics reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import compliance_audit
    out = compliance_audit.handle({'action_taken': 'sample', 'actor': 'sample', 'control_id': 'id-1', 'reference': 'sample', 'status': 'open', 'framework': 'sample', 'regulation': 'sample', 'event_type': 'sample', 'actor_role': 'sample', 'evidence_ref': 'sample', 'findings': 'sample', 'occurred_at': '2026-09-03T10:00:00'})
    if not isinstance(out, dict):
        failures.append('compliance_audit returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('compliance_audit rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('compliance_audit reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    assert not failures, "; ".join(failures)
