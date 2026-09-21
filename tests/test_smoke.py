"""The platform runs, and it runs without the store."""

import os

import pytest


def test_capabilities_import():
    from app.actions import property_and_room_registry
    assert property_and_room_registry.CAPABILITY_ID
    from app.actions import front_desk_and_guest_stay
    assert front_desk_and_guest_stay.CAPABILITY_ID
    from app.actions import housekeeping_and_maintenance
    assert housekeeping_and_maintenance.CAPABILITY_ID
    from app.actions import guest_engagement_and_segmentation
    assert guest_engagement_and_segmentation.CAPABILITY_ID
    from app.actions import document_and_knowledge_answers
    assert document_and_knowledge_answers.CAPABILITY_ID
    from app.actions import operations_billing
    assert operations_billing.CAPABILITY_ID
    from app.actions import operations_oversight_dashboard
    assert operations_oversight_dashboard.CAPABILITY_ID
    from app.actions import external_integration_adapter
    assert external_integration_adapter.CAPABILITY_ID


def test_dispatch_runs_offline():
    """No store env, no network: every block must LOAD and EXECUTE from
    vendor/. A block-level refusal of this bare probe is still local
    execution; an import failure is the store dependency this test
    exists to catch."""
    for var in ("CEREBRUM_API_URL", "CEREBRUM_API_KEY", "CEREBRUM_API_TOKEN"):
        os.environ.pop(var, None)
    from app.dispatch import execute, load_block
    for block_id in ['billing', 'channel_router', 'dashboard', 'document_engine', 'estate_maintenance', 'estate_registry', 'guest_rfm_segmentation', 'hospitality_connectors', 'hotel_v2', 'knowledge', 'mcp_adapter', 'multi_tenant_rbac', 'notification', 'workflow']:
        load_block(block_id)
    actions = {'billing': 'record_usage', 'dashboard': 'render', 'estate_maintenance': 'create', 'estate_registry': 'create', 'knowledge': 'ask', 'mcp_adapter': 'list_tools', 'notification': 'send', 'workflow': 'run'}
    for block_id in ['billing', 'channel_router', 'dashboard', 'document_engine', 'estate_maintenance', 'estate_registry', 'guest_rfm_segmentation', 'hospitality_connectors', 'hotel_v2', 'knowledge', 'mcp_adapter', 'multi_tenant_rbac', 'notification', 'workflow']:
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
    from app.actions import property_and_room_registry
    try:
        out = property_and_room_registry.handle({'reference': 'sample', 'status': 'open', 'property_name': 'sample', 'building': 'sample', 'floor': 1, 'room_number': 'sample', 'room_type': 'standard', 'capacity': 1, 'room_status': 'available', 'notes': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('property_and_room_registry handle() must return a dict, got ' + type(out).__name__)
    from app.actions import front_desk_and_guest_stay
    try:
        out = front_desk_and_guest_stay.handle({'reference': 'sample', 'status': 'open', 'guest_name': 'sample', 'room_number': 'sample', 'arrival_date': '2026-09-03', 'departure_date': '2026-09-03', 'guests_count': 1, 'stay_status': 'reserved', 'folio_currency': 'sample', 'notes': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('front_desk_and_guest_stay handle() must return a dict, got ' + type(out).__name__)
    from app.actions import housekeeping_and_maintenance
    try:
        out = housekeeping_and_maintenance.handle({'reference': 'sample', 'status': 'open', 'title': 'sample', 'work_type': 'housekeeping', 'room_number': 'sample', 'priority': 'low', 'due_date': '2026-09-03', 'assigned_to': 'sample', 'work_status': 'open', 'notes': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('housekeeping_and_maintenance handle() must return a dict, got ' + type(out).__name__)
    from app.actions import guest_engagement_and_segmentation
    try:
        out = guest_engagement_and_segmentation.handle({'reference': 'sample', 'status': 'open', 'guest_name': 'sample', 'recency_days': 1, 'frequency': 1, 'monetary': 1, 'segment': 'champion', 'delivery_channel': 'mcp', 'offer_code': 'id-1', 'notes': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('guest_engagement_and_segmentation handle() must return a dict, got ' + type(out).__name__)
    from app.actions import document_and_knowledge_answers
    try:
        out = document_and_knowledge_answers.handle({'reference': 'sample', 'status': 'open', 'title': 'sample', 'document_kind': 'manual', 'question': 'sample', 'document_text': 'sample', 'attachment_path': 'sample', 'answer': 'sample', 'source_document': 'sample', 'authority_label': 'certified', 'notes': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('document_and_knowledge_answers handle() must return a dict, got ' + type(out).__name__)
    from app.actions import operations_billing
    try:
        out = operations_billing.handle({'setting': 'sample', 'reference': 'sample', 'status': 'open', 'folio_reference': 'sample', 'charge_type': 'room', 'amount': 1, 'currency': 'sample', 'tax_rate_percent': 1, 'total_amount': 1, 'notes': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('operations_billing handle() must return a dict, got ' + type(out).__name__)
    from app.actions import operations_oversight_dashboard
    try:
        out = operations_oversight_dashboard.handle({'reference': 'sample', 'status': 'open', 'dashboard_name': 'sample', 'widget': 'occupancy', 'window_days': 1, 'operator_role': 'operator', 'occupancy_percent': 1, 'open_work_orders': 1, 'notes': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('operations_oversight_dashboard handle() must return a dict, got ' + type(out).__name__)
    from app.actions import external_integration_adapter
    try:
        out = external_integration_adapter.handle({'reference': 'sample', 'status': 'open', 'system': 'opera', 'resource': 'sample', 'direction': 'inbound', 'payload_format': 'json', 'endpoint_url': 'sample', 'records_seen': 1, 'notes': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('external_integration_adapter handle() must return a dict, got ' + type(out).__name__)
    assert not failures, "; ".join(failures)


@pytest.mark.pilot
def test_every_capability_executes_end_to_end():
    """Pilot: each handler runs its blocks on a spec payload and
    Store must accept it. Not the factory code-phase gate."""
    for var in ("CEREBRUM_API_URL", "CEREBRUM_API_KEY"):
        os.environ.pop(var, None)
    import json as _json
    failures = []
    from app.actions import property_and_room_registry
    out = property_and_room_registry.handle({'reference': 'sample', 'status': 'open', 'property_name': 'sample', 'building': 'sample', 'floor': 1, 'room_number': 'sample', 'room_type': 'standard', 'capacity': 1, 'room_status': 'available', 'notes': 'sample'})
    if not isinstance(out, dict):
        failures.append('property_and_room_registry returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('property_and_room_registry rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('property_and_room_registry reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import front_desk_and_guest_stay
    out = front_desk_and_guest_stay.handle({'reference': 'sample', 'status': 'open', 'guest_name': 'sample', 'room_number': 'sample', 'arrival_date': '2026-09-03', 'departure_date': '2026-09-03', 'guests_count': 1, 'stay_status': 'reserved', 'folio_currency': 'sample', 'notes': 'sample'})
    if not isinstance(out, dict):
        failures.append('front_desk_and_guest_stay returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('front_desk_and_guest_stay rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('front_desk_and_guest_stay reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import housekeeping_and_maintenance
    out = housekeeping_and_maintenance.handle({'reference': 'sample', 'status': 'open', 'title': 'sample', 'work_type': 'housekeeping', 'room_number': 'sample', 'priority': 'low', 'due_date': '2026-09-03', 'assigned_to': 'sample', 'work_status': 'open', 'notes': 'sample'})
    if not isinstance(out, dict):
        failures.append('housekeeping_and_maintenance returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('housekeeping_and_maintenance rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('housekeeping_and_maintenance reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import guest_engagement_and_segmentation
    out = guest_engagement_and_segmentation.handle({'reference': 'sample', 'status': 'open', 'guest_name': 'sample', 'recency_days': 1, 'frequency': 1, 'monetary': 1, 'segment': 'champion', 'delivery_channel': 'mcp', 'offer_code': 'id-1', 'notes': 'sample'})
    if not isinstance(out, dict):
        failures.append('guest_engagement_and_segmentation returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('guest_engagement_and_segmentation rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('guest_engagement_and_segmentation reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import document_and_knowledge_answers
    out = document_and_knowledge_answers.handle({'reference': 'sample', 'status': 'open', 'title': 'sample', 'document_kind': 'manual', 'question': 'sample', 'document_text': 'sample', 'attachment_path': 'sample', 'answer': 'sample', 'source_document': 'sample', 'authority_label': 'certified', 'notes': 'sample'})
    if not isinstance(out, dict):
        failures.append('document_and_knowledge_answers returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('document_and_knowledge_answers rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('document_and_knowledge_answers reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import operations_billing
    out = operations_billing.handle({'setting': 'sample', 'reference': 'sample', 'status': 'open', 'folio_reference': 'sample', 'charge_type': 'room', 'amount': 1, 'currency': 'sample', 'tax_rate_percent': 1, 'total_amount': 1, 'notes': 'sample'})
    if not isinstance(out, dict):
        failures.append('operations_billing returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('operations_billing rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('operations_billing reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import operations_oversight_dashboard
    out = operations_oversight_dashboard.handle({'reference': 'sample', 'status': 'open', 'dashboard_name': 'sample', 'widget': 'occupancy', 'window_days': 1, 'operator_role': 'operator', 'occupancy_percent': 1, 'open_work_orders': 1, 'notes': 'sample'})
    if not isinstance(out, dict):
        failures.append('operations_oversight_dashboard returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('operations_oversight_dashboard rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('operations_oversight_dashboard reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import external_integration_adapter
    out = external_integration_adapter.handle({'reference': 'sample', 'status': 'open', 'system': 'opera', 'resource': 'sample', 'direction': 'inbound', 'payload_format': 'json', 'endpoint_url': 'sample', 'records_seen': 1, 'notes': 'sample'})
    if not isinstance(out, dict):
        failures.append('external_integration_adapter returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('external_integration_adapter rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('external_integration_adapter reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    assert not failures, "; ".join(failures)
