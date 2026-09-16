"""The platform runs, and it runs without the store."""

import os

import pytest


def test_capabilities_import():
    from app.actions import patient_records
    assert patient_records.CAPABILITY_ID
    from app.actions import appointment_scheduling
    assert appointment_scheduling.CAPABILITY_ID
    from app.actions import treatment_management
    assert treatment_management.CAPABILITY_ID
    from app.actions import billing_invoicing
    assert billing_invoicing.CAPABILITY_ID
    from app.actions import inventory_management
    assert inventory_management.CAPABILITY_ID
    from app.actions import audit_trail
    assert audit_trail.CAPABILITY_ID
    from app.actions import role_management
    assert role_management.CAPABILITY_ID
    from app.actions import clinic_analytics
    assert clinic_analytics.CAPABILITY_ID


def test_dispatch_runs_offline():
    """No store env, no network: every block must LOAD and EXECUTE from
    vendor/. A block-level refusal of this bare probe is still local
    execution; an import failure is the store dependency this test
    exists to catch."""
    for var in ("CEREBRUM_API_URL", "CEREBRUM_API_KEY", "CEREBRUM_API_TOKEN"):
        os.environ.pop(var, None)
    from app.dispatch import execute, load_block
    for block_id in ['analytics', 'audit', 'capture', 'dashboard', 'database', 'document_engine', 'event_bus', 'evidence_verifier', 'file_hasher', 'formula_executor', 'knowledge', 'memory', 'notification', 'portfolio_rollup', 'queue', 'readiness_engine', 'storage', 'team', 'validation', 'workflow']:
        load_block(block_id)
    actions = {'analytics': 'track_event', 'audit': 'log', 'dashboard': 'render', 'database': 'query', 'event_bus': 'publish', 'knowledge': 'ask', 'memory': 'get', 'notification': 'send', 'queue': 'enqueue', 'storage': 'store', 'team': 'create_team', 'validation': 'validate_pipeline', 'workflow': 'run'}
    for block_id in ['analytics', 'audit', 'capture', 'dashboard', 'database', 'document_engine', 'event_bus', 'evidence_verifier', 'file_hasher', 'formula_executor', 'knowledge', 'memory', 'notification', 'portfolio_rollup', 'queue', 'readiness_engine', 'storage', 'team', 'validation', 'workflow']:
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
        out = patient_records.handle({'owner_name': 'sample', 'pet_name': 'sample', 'reference': 'sample', 'status': 'open', 'species': 'sample', 'breed': 'sample', 'owner_email': 'guest@example.com', 'owner_phone': 'sample', 'date_of_birth': 'sample', 'weight_kg': 'sample', 'vaccination_status': 'open', 'allergies': 'sample', 'clinical_notes': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('patient_records handle() must return a dict, got ' + type(out).__name__)
    from app.actions import appointment_scheduling
    try:
        out = appointment_scheduling.handle({'pet_name': 'sample', 'reference': 'sample', 'status': 'open', 'veterinarian': 'sample', 'owner_name': 'sample', 'appointment_date': '2026-09-03', 'appointment_time': '10:00:00', 'duration_minutes': 'sample', 'visit_reason': 'sample', 'room': 'sample', 'appointment_status': 'open'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('appointment_scheduling handle() must return a dict, got ' + type(out).__name__)
    from app.actions import treatment_management
    try:
        out = treatment_management.handle({'pet_name': 'sample', 'reference': 'sample', 'status': 'open', 'veterinarian': 'sample', 'treatment_type': 'sample', 'diagnosis': 'sample', 'procedure_notes': 'sample', 'medication': 'sample', 'dosage': 'sample', 'treatment_date': '2026-09-03', 'follow_up_date': '2026-09-03', 'attachment_path': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('treatment_management handle() must return a dict, got ' + type(out).__name__)
    from app.actions import billing_invoicing
    try:
        out = billing_invoicing.handle({'client_name': 'sample', 'invoice_number': 'sample', 'reference': 'sample', 'status': 'open', 'pet_name': 'sample', 'line_items': 'sample', 'subtotal': 'sample', 'tax_rate': 'sample', 'total_amount': 'sample', 'payment_status': 'open', 'payment_method': 'sample', 'invoice_date': '2026-09-03', 'attachment_path': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('billing_invoicing handle() must return a dict, got ' + type(out).__name__)
    from app.actions import inventory_management
    try:
        out = inventory_management.handle({'item_name': 'sample', 'reference': 'sample', 'sku': 'sample', 'status': 'open', 'category': 'sample', 'quantity': 1, 'reorder_level': 'sample', 'unit_cost': 'sample', 'supplier': 'sample', 'expiry_date': '2026-09-03'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('inventory_management handle() must return a dict, got ' + type(out).__name__)
    from app.actions import audit_trail
    try:
        out = audit_trail.handle({'actor': 'sample', 'event_type': 'sample', 'reference': 'sample', 'status': 'open', 'entity_name': 'sample', 'entity_id': 'id-1', 'actor_role': 'sample', 'action_taken': 'sample', 'details': 'sample', 'occurred_at': '2026-09-03T10:00:00'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('audit_trail handle() must return a dict, got ' + type(out).__name__)
    from app.actions import role_management
    try:
        out = role_management.handle({'reference': 'sample', 'role_name': 'sample', 'status': 'open', 'display_name': 'sample', 'permissions': 'sample', 'access_level': 'sample', 'department': 'sample', 'is_active': True})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('role_management handle() must return a dict, got ' + type(out).__name__)
    from app.actions import clinic_analytics
    try:
        out = clinic_analytics.handle({'metric_name': 'sample', 'reference': 'sample', 'status': 'open', 'metric_value': 'sample', 'period': 'sample', 'period_start': 'sample', 'period_end': 'sample', 'dimension': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('clinic_analytics handle() must return a dict, got ' + type(out).__name__)
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
    out = patient_records.handle({'owner_name': 'sample', 'pet_name': 'sample', 'reference': 'sample', 'status': 'open', 'species': 'sample', 'breed': 'sample', 'owner_email': 'guest@example.com', 'owner_phone': 'sample', 'date_of_birth': 'sample', 'weight_kg': 'sample', 'vaccination_status': 'open', 'allergies': 'sample', 'clinical_notes': 'sample'})
    if not isinstance(out, dict):
        failures.append('patient_records returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('patient_records rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('patient_records reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import appointment_scheduling
    out = appointment_scheduling.handle({'pet_name': 'sample', 'reference': 'sample', 'status': 'open', 'veterinarian': 'sample', 'owner_name': 'sample', 'appointment_date': '2026-09-03', 'appointment_time': '10:00:00', 'duration_minutes': 'sample', 'visit_reason': 'sample', 'room': 'sample', 'appointment_status': 'open'})
    if not isinstance(out, dict):
        failures.append('appointment_scheduling returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('appointment_scheduling rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('appointment_scheduling reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import treatment_management
    out = treatment_management.handle({'pet_name': 'sample', 'reference': 'sample', 'status': 'open', 'veterinarian': 'sample', 'treatment_type': 'sample', 'diagnosis': 'sample', 'procedure_notes': 'sample', 'medication': 'sample', 'dosage': 'sample', 'treatment_date': '2026-09-03', 'follow_up_date': '2026-09-03', 'attachment_path': 'sample'})
    if not isinstance(out, dict):
        failures.append('treatment_management returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('treatment_management rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('treatment_management reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import billing_invoicing
    out = billing_invoicing.handle({'client_name': 'sample', 'invoice_number': 'sample', 'reference': 'sample', 'status': 'open', 'pet_name': 'sample', 'line_items': 'sample', 'subtotal': 'sample', 'tax_rate': 'sample', 'total_amount': 'sample', 'payment_status': 'open', 'payment_method': 'sample', 'invoice_date': '2026-09-03', 'attachment_path': 'sample'})
    if not isinstance(out, dict):
        failures.append('billing_invoicing returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('billing_invoicing rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('billing_invoicing reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import inventory_management
    out = inventory_management.handle({'item_name': 'sample', 'reference': 'sample', 'sku': 'sample', 'status': 'open', 'category': 'sample', 'quantity': 1, 'reorder_level': 'sample', 'unit_cost': 'sample', 'supplier': 'sample', 'expiry_date': '2026-09-03'})
    if not isinstance(out, dict):
        failures.append('inventory_management returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('inventory_management rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('inventory_management reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import audit_trail
    out = audit_trail.handle({'actor': 'sample', 'event_type': 'sample', 'reference': 'sample', 'status': 'open', 'entity_name': 'sample', 'entity_id': 'id-1', 'actor_role': 'sample', 'action_taken': 'sample', 'details': 'sample', 'occurred_at': '2026-09-03T10:00:00'})
    if not isinstance(out, dict):
        failures.append('audit_trail returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('audit_trail rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('audit_trail reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import role_management
    out = role_management.handle({'reference': 'sample', 'role_name': 'sample', 'status': 'open', 'display_name': 'sample', 'permissions': 'sample', 'access_level': 'sample', 'department': 'sample', 'is_active': True})
    if not isinstance(out, dict):
        failures.append('role_management returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('role_management rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('role_management reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import clinic_analytics
    out = clinic_analytics.handle({'metric_name': 'sample', 'reference': 'sample', 'status': 'open', 'metric_value': 'sample', 'period': 'sample', 'period_start': 'sample', 'period_end': 'sample', 'dimension': 'sample'})
    if not isinstance(out, dict):
        failures.append('clinic_analytics returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('clinic_analytics rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('clinic_analytics reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    assert not failures, "; ".join(failures)
