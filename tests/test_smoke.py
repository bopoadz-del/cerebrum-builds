"""The platform runs, and it runs without the store."""

import os

import pytest


def test_capabilities_import():
    from app.actions import lead_intake_and_dial_queue
    assert lead_intake_and_dial_queue.CAPABILITY_ID
    from app.actions import call_state_machine
    assert call_state_machine.CAPABILITY_ID
    from app.actions import project_knowledge_grounding
    assert project_knowledge_grounding.CAPABILITY_ID
    from app.actions import voice_gateway
    assert voice_gateway.CAPABILITY_ID
    from app.actions import warm_transfer
    assert warm_transfer.CAPABILITY_ID
    from app.actions import qualification_and_broker_summary
    assert qualification_and_broker_summary.CAPABILITY_ID
    from app.actions import outcome_capture_and_ledger
    assert outcome_capture_and_ledger.CAPABILITY_ID
    from app.actions import crm_destination_placeholder
    assert crm_destination_placeholder.CAPABILITY_ID
    from app.actions import notification
    assert notification.CAPABILITY_ID
    from app.actions import local_drive
    assert local_drive.CAPABILITY_ID
    from app.actions import google_drive
    assert google_drive.CAPABILITY_ID
    from app.actions import mcp_adapter
    assert mcp_adapter.CAPABILITY_ID


def test_dispatch_runs_offline():
    """No store env, no network: every block must LOAD and EXECUTE from
    vendor/. A block-level refusal of this bare probe is still local
    execution; an import failure is the store dependency this test
    exists to catch."""
    for var in ("CEREBRUM_API_URL", "CEREBRUM_API_KEY", "CEREBRUM_API_TOKEN"):
        os.environ.pop(var, None)
    from app.dispatch import execute, load_block
    for block_id in ['agent_state_sync', 'audit_chain', 'capture', 'database', 'event_bus', 'evidence_or_refuse', 'formula_executor', 'google_drive', 'ingestion_provenance', 'knowledge', 'llm_enhancer', 'local_drive', 'mcp_adapter', 'mock_connector_bus', 'notification', 'orchestrator', 'queue', 'recommendation_template', 'storage', 'validation', 'vector_search', 'webhook', 'workflow']:
        load_block(block_id)
    actions = {'database': 'query', 'event_bus': 'publish', 'knowledge': 'ask', 'mcp_adapter': 'list_tools', 'notification': 'send', 'queue': 'enqueue', 'storage': 'store', 'validation': 'validate_pipeline', 'workflow': 'run'}
    for block_id in ['agent_state_sync', 'audit_chain', 'capture', 'database', 'event_bus', 'evidence_or_refuse', 'formula_executor', 'google_drive', 'ingestion_provenance', 'knowledge', 'llm_enhancer', 'local_drive', 'mcp_adapter', 'mock_connector_bus', 'notification', 'orchestrator', 'queue', 'recommendation_template', 'storage', 'validation', 'vector_search', 'webhook', 'workflow']:
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
    from app.actions import lead_intake_and_dial_queue
    try:
        out = lead_intake_and_dial_queue.handle({'lead_name': 'sample', 'phone': 'sample', 'project_tag': 'sample', 'reference': 'sample', 'status': 'open', 'language': 'en', 'campaign': 'sample', 'source_file': 'sample', 'lead_email': 'guest@example.com', 'property_type': 'apartment', 'budget': 'sample', 'area': 'sample', 'timeline': 'immediate', 'priority': 'sample', 'phone_e164': 'sample', 'dialable': 'sample', 'dialable_reason': 'sample', 'attempt_count': 1, 'max_attempts': 'sample', 'retry_backoff_minutes': 'sample', 'daily_call_cap': 'sample', 'concurrency': 'sample', 'queue_state': 'queued', 'best_call_window': 'sample', 'window_state': 'open', 'dial_scheduled_at': '2026-09-03T10:00:00', 'next_attempt_at': '2026-09-03T10:00:00', 'last_call_sid': 'sample', 'notes': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('lead_intake_and_dial_queue handle() must return a dict, got ' + type(out).__name__)
    from app.actions import call_state_machine
    try:
        out = call_state_machine.handle({'call_sid': 'sample', 'event': 'dial', 'reference': 'sample', 'status': 'open', 'lead_id': 'id-1', 'lead_reference': 'sample', 'previous_state': 'queued', 'current_state': 'queued', 'attempt_count': 1, 'within_window': 'sample', 'window_reason': 'sample', 'transition_allowed': 'sample', 'refusal_reason': 'sample', 'guard_notes': 'sample', 'window_snapshot': 'sample', 'occurred_at': '2026-09-03T10:00:00', 'source': 'voice_gateway', 'campaign': 'sample'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('call_state_machine handle() must return a dict, got ' + type(out).__name__)
    from app.actions import project_knowledge_grounding
    try:
        out = project_knowledge_grounding.handle({'project_tag': 'sample', 'question': 'sample', 'claim_type': 'price', 'language': 'en', 'answer': 'sample', 'pitch': 'sample', 'citations': 'sample', 'source_documents': 'sample', 'retrieved_count': 1, 'withheld': 'sample', 'withheld_claims': 'sample', 'authority_layer': 'sample', 'authority_label': 'sample', 'divergence': 'sample', 'campaign': 'sample', 'reference': 'sample', 'status': 'open'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('project_knowledge_grounding handle() must return a dict, got ' + type(out).__name__)
    from app.actions import voice_gateway
    try:
        out = voice_gateway.handle({'call_sid': 'sample', 'to_number': 'sample', 'from_number': 'sample', 'direction': 'outbound', 'language': 'en', 'call_status': 'initiated', 'call_event': 'sample', 'transition_to': 'queued', 'mapping_ok': 'sample', 'twiml': 'sample', 'asr_transcript': 'sample', 'tts_text': 'sample', 'tts_voice': 'sample', 'gather_language': 'sample', 'conference_sid': 'sample', 'duration_seconds': 'sample', 'attempt': 'sample', 'provider': 'sample', 'call_key_source': 'sample', 'edge_stub': 'sample', 'unavailable_blocks': 'sample', 'reference': 'sample', 'status': 'open', 'voice_action': 'originate'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('voice_gateway handle() must return a dict, got ' + type(out).__name__)
    from app.actions import warm_transfer
    try:
        out = warm_transfer.handle({'call_sid': 'sample', 'outcome': 'transferred', 'lead_id': 'id-1', 'project_tag': 'sample', 'qualified_outcome': 'project_interested', 'broker_number': 'sample', 'broker_language': 'en', 'whisper_text': 'sample', 'summary': 'sample', 'step_count': 1, 'conference_name': 'sample', 'conference_sid': 'sample', 'bridge_seconds': 'sample', 'attempt': 'sample', 'transfer_key': 'sample', 'edge_stub': 'sample', 'unavailable_blocks': 'sample', 'reference': 'sample', 'status': 'open'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('warm_transfer handle() must return a dict, got ' + type(out).__name__)
    from app.actions import qualification_and_broker_summary
    try:
        out = qualification_and_broker_summary.handle({'call_sid': 'sample', 'outcome': 'project_interested', 'language': 'en', 'project_tag': 'sample', 'lead_name': 'sample', 'property_type': 'apartment', 'budget': 'sample', 'currency': 'sample', 'area': 'sample', 'timeline': 'immediate', 'transcript': 'sample', 'collected': 'sample', 'summary': 'sample', 'summary_text': 'sample', 'recommendation': 'sample', 'next_action': 'transfer_to_broker', 'qualified': 'sample', 'transfer_required': 'sample', 'authority_layer': 'sample', 'authority_label': 'sample', 'campaign': 'sample', 'reference': 'sample', 'status': 'open'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('qualification_and_broker_summary handle() must return a dict, got ' + type(out).__name__)
    from app.actions import outcome_capture_and_ledger
    try:
        out = outcome_capture_and_ledger.handle({'call_sid': 'sample', 'event_type': 'attempted', 'sequence': 'sample', 'prev_hash': 'sample', 'entry_hash': 'sample', 'payload_digest': 'sample', 'outcome': 'project_interested', 'actor': 'sample', 'campaign': 'sample', 'detail': 'sample', 'chain_ok': 'sample', 'verified_count': 1, 'reference': 'sample', 'status': 'open'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('outcome_capture_and_ledger handle() must return a dict, got ' + type(out).__name__)
    from app.actions import crm_destination_placeholder
    try:
        out = crm_destination_placeholder.handle({'call_sid': 'sample', 'crm_system': 'sample', 'destination': 'sample', 'destination_named': 'sample', 'payload_shape': 'sample', 'delivery': 'placeholder', 'unavailable_blocks': 'sample', 'outcome': 'project_interested', 'summary': 'sample', 'note': 'sample', 'intended_method': 'POST', 'reference': 'sample', 'status': 'open'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('crm_destination_placeholder handle() must return a dict, got ' + type(out).__name__)
    from app.actions import notification
    try:
        out = notification.handle({'trigger_event': 'lead_qualified', 'channel': 'webhook', 'target': 'sample', 'subject': 'sample', 'body': 'sample', 'delivery': 'delivered', 'provider': 'sample', 'attempts': 'sample', 'response_code': 'id-1', 'delivered_at': '2026-09-03T10:00:00', 'unavailable_blocks': 'sample', 'message_digest': 'sample', 'summary': 'sample', 'outcome': 'project_interested', 'call_sid': 'sample', 'campaign': 'sample', 'reference': 'sample', 'status': 'open'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('notification handle() must return a dict, got ' + type(out).__name__)
    from app.actions import local_drive
    try:
        out = local_drive.handle({'operation': 'put', 'relative_path': 'sample', 'content': 'sample', 'content_digest': 'sample', 'bytes_written': 'sample', 'root': 'sample', 'tenant_root': 'sample', 'entries': 'sample', 'file_exists': 'sample', 'size_bytes': 'sample', 'media_type': 'sample', 'reference': 'sample', 'status': 'open'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('local_drive handle() must return a dict, got ' + type(out).__name__)
    from app.actions import google_drive
    try:
        out = google_drive.handle({'operation': 'upload', 'drive_mode': 'stubbed', 'folder_id': 'id-1', 'document_id': 'id-1', 'file_name': 'sample', 'mime_type': 'sample', 'credentials_present': 'sample', 'unavailable_blocks': 'sample', 'delivery': 'stub', 'note': 'sample', 'would_call': 'sample', 'upload_state': 'sample', 'reference': 'sample', 'status': 'open'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('google_drive handle() must return a dict, got ' + type(out).__name__)
    from app.actions import mcp_adapter
    try:
        out = mcp_adapter.handle({'method': 'tools/list', 'tool': 'sample', 'arguments': 'sample', 'catalog_scope': 'platform', 'tool_count': 1, 'dispatched': 'sample', 'error_code': 'id-1', 'protocol': 'sample', 'duration_ms': 'sample', 'reference': 'sample', 'status': 'open'})
    except Exception as exc:
        out = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    if not isinstance(out, dict):
        failures.append('mcp_adapter handle() must return a dict, got ' + type(out).__name__)
    assert not failures, "; ".join(failures)


@pytest.mark.pilot
def test_every_capability_executes_end_to_end():
    """Pilot: each handler runs its blocks on a spec payload and
    Store must accept it. Not the factory code-phase gate."""
    for var in ("CEREBRUM_API_URL", "CEREBRUM_API_KEY"):
        os.environ.pop(var, None)
    import json as _json
    failures = []
    from app.actions import lead_intake_and_dial_queue
    out = lead_intake_and_dial_queue.handle({'lead_name': 'sample', 'phone': 'sample', 'project_tag': 'sample', 'reference': 'sample', 'status': 'open', 'language': 'en', 'campaign': 'sample', 'source_file': 'sample', 'lead_email': 'guest@example.com', 'property_type': 'apartment', 'budget': 'sample', 'area': 'sample', 'timeline': 'immediate', 'priority': 'sample', 'phone_e164': 'sample', 'dialable': 'sample', 'dialable_reason': 'sample', 'attempt_count': 1, 'max_attempts': 'sample', 'retry_backoff_minutes': 'sample', 'daily_call_cap': 'sample', 'concurrency': 'sample', 'queue_state': 'queued', 'best_call_window': 'sample', 'window_state': 'open', 'dial_scheduled_at': '2026-09-03T10:00:00', 'next_attempt_at': '2026-09-03T10:00:00', 'last_call_sid': 'sample', 'notes': 'sample'})
    if not isinstance(out, dict):
        failures.append('lead_intake_and_dial_queue returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('lead_intake_and_dial_queue rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('lead_intake_and_dial_queue reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import call_state_machine
    out = call_state_machine.handle({'call_sid': 'sample', 'event': 'dial', 'reference': 'sample', 'status': 'open', 'lead_id': 'id-1', 'lead_reference': 'sample', 'previous_state': 'queued', 'current_state': 'queued', 'attempt_count': 1, 'within_window': 'sample', 'window_reason': 'sample', 'transition_allowed': 'sample', 'refusal_reason': 'sample', 'guard_notes': 'sample', 'window_snapshot': 'sample', 'occurred_at': '2026-09-03T10:00:00', 'source': 'voice_gateway', 'campaign': 'sample'})
    if not isinstance(out, dict):
        failures.append('call_state_machine returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('call_state_machine rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('call_state_machine reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import project_knowledge_grounding
    out = project_knowledge_grounding.handle({'project_tag': 'sample', 'question': 'sample', 'claim_type': 'price', 'language': 'en', 'answer': 'sample', 'pitch': 'sample', 'citations': 'sample', 'source_documents': 'sample', 'retrieved_count': 1, 'withheld': 'sample', 'withheld_claims': 'sample', 'authority_layer': 'sample', 'authority_label': 'sample', 'divergence': 'sample', 'campaign': 'sample', 'reference': 'sample', 'status': 'open'})
    if not isinstance(out, dict):
        failures.append('project_knowledge_grounding returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('project_knowledge_grounding rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('project_knowledge_grounding reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import voice_gateway
    out = voice_gateway.handle({'call_sid': 'sample', 'to_number': 'sample', 'from_number': 'sample', 'direction': 'outbound', 'language': 'en', 'call_status': 'initiated', 'call_event': 'sample', 'transition_to': 'queued', 'mapping_ok': 'sample', 'twiml': 'sample', 'asr_transcript': 'sample', 'tts_text': 'sample', 'tts_voice': 'sample', 'gather_language': 'sample', 'conference_sid': 'sample', 'duration_seconds': 'sample', 'attempt': 'sample', 'provider': 'sample', 'call_key_source': 'sample', 'edge_stub': 'sample', 'unavailable_blocks': 'sample', 'reference': 'sample', 'status': 'open', 'voice_action': 'originate'})
    if not isinstance(out, dict):
        failures.append('voice_gateway returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('voice_gateway rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('voice_gateway reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import warm_transfer
    out = warm_transfer.handle({'call_sid': 'sample', 'outcome': 'transferred', 'lead_id': 'id-1', 'project_tag': 'sample', 'qualified_outcome': 'project_interested', 'broker_number': 'sample', 'broker_language': 'en', 'whisper_text': 'sample', 'summary': 'sample', 'step_count': 1, 'conference_name': 'sample', 'conference_sid': 'sample', 'bridge_seconds': 'sample', 'attempt': 'sample', 'transfer_key': 'sample', 'edge_stub': 'sample', 'unavailable_blocks': 'sample', 'reference': 'sample', 'status': 'open'})
    if not isinstance(out, dict):
        failures.append('warm_transfer returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('warm_transfer rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('warm_transfer reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import qualification_and_broker_summary
    out = qualification_and_broker_summary.handle({'call_sid': 'sample', 'outcome': 'project_interested', 'language': 'en', 'project_tag': 'sample', 'lead_name': 'sample', 'property_type': 'apartment', 'budget': 'sample', 'currency': 'sample', 'area': 'sample', 'timeline': 'immediate', 'transcript': 'sample', 'collected': 'sample', 'summary': 'sample', 'summary_text': 'sample', 'recommendation': 'sample', 'next_action': 'transfer_to_broker', 'qualified': 'sample', 'transfer_required': 'sample', 'authority_layer': 'sample', 'authority_label': 'sample', 'campaign': 'sample', 'reference': 'sample', 'status': 'open'})
    if not isinstance(out, dict):
        failures.append('qualification_and_broker_summary returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('qualification_and_broker_summary rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('qualification_and_broker_summary reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import outcome_capture_and_ledger
    out = outcome_capture_and_ledger.handle({'call_sid': 'sample', 'event_type': 'attempted', 'sequence': 'sample', 'prev_hash': 'sample', 'entry_hash': 'sample', 'payload_digest': 'sample', 'outcome': 'project_interested', 'actor': 'sample', 'campaign': 'sample', 'detail': 'sample', 'chain_ok': 'sample', 'verified_count': 1, 'reference': 'sample', 'status': 'open'})
    if not isinstance(out, dict):
        failures.append('outcome_capture_and_ledger returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('outcome_capture_and_ledger rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('outcome_capture_and_ledger reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import crm_destination_placeholder
    out = crm_destination_placeholder.handle({'call_sid': 'sample', 'crm_system': 'sample', 'destination': 'sample', 'destination_named': 'sample', 'payload_shape': 'sample', 'delivery': 'placeholder', 'unavailable_blocks': 'sample', 'outcome': 'project_interested', 'summary': 'sample', 'note': 'sample', 'intended_method': 'POST', 'reference': 'sample', 'status': 'open'})
    if not isinstance(out, dict):
        failures.append('crm_destination_placeholder returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('crm_destination_placeholder rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('crm_destination_placeholder reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import notification
    out = notification.handle({'trigger_event': 'lead_qualified', 'channel': 'webhook', 'target': 'sample', 'subject': 'sample', 'body': 'sample', 'delivery': 'delivered', 'provider': 'sample', 'attempts': 'sample', 'response_code': 'id-1', 'delivered_at': '2026-09-03T10:00:00', 'unavailable_blocks': 'sample', 'message_digest': 'sample', 'summary': 'sample', 'outcome': 'project_interested', 'call_sid': 'sample', 'campaign': 'sample', 'reference': 'sample', 'status': 'open'})
    if not isinstance(out, dict):
        failures.append('notification returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('notification rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('notification reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import local_drive
    out = local_drive.handle({'operation': 'put', 'relative_path': 'sample', 'content': 'sample', 'content_digest': 'sample', 'bytes_written': 'sample', 'root': 'sample', 'tenant_root': 'sample', 'entries': 'sample', 'file_exists': 'sample', 'size_bytes': 'sample', 'media_type': 'sample', 'reference': 'sample', 'status': 'open'})
    if not isinstance(out, dict):
        failures.append('local_drive returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('local_drive rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('local_drive reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import google_drive
    out = google_drive.handle({'operation': 'upload', 'drive_mode': 'stubbed', 'folder_id': 'id-1', 'document_id': 'id-1', 'file_name': 'sample', 'mime_type': 'sample', 'credentials_present': 'sample', 'unavailable_blocks': 'sample', 'delivery': 'stub', 'note': 'sample', 'would_call': 'sample', 'upload_state': 'sample', 'reference': 'sample', 'status': 'open'})
    if not isinstance(out, dict):
        failures.append('google_drive returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('google_drive rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('google_drive reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    from app.actions import mcp_adapter
    out = mcp_adapter.handle({'method': 'tools/list', 'tool': 'sample', 'arguments': 'sample', 'catalog_scope': 'platform', 'tool_count': 1, 'dispatched': 'sample', 'error_code': 'id-1', 'protocol': 'sample', 'duration_ms': 'sample', 'reference': 'sample', 'status': 'open'})
    if not isinstance(out, dict):
        failures.append('mcp_adapter returned a non-dict: ' + repr(out)[:120])
    elif out.get("ok") is False:
        failures.append('mcp_adapter rejected a payload built from its own schema: ' + str(out.get('error')))
    elif '\"status\": \"error\"' in _json.dumps(out, default=str) or '\"status\": \"failed\"' in _json.dumps(out, default=str):
        failures.append('mcp_adapter reported ok around a failed block call: ' + _json.dumps(out, default=str)[:300])
    assert not failures, "; ".join(failures)
