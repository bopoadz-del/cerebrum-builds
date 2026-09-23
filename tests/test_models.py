"""Models must survive a round trip through sqlite."""

from app import store
from app.models import MODELS


#: Tenant the generated tests act as (the platform token's tenant).
TENANT = 'local'


def test_every_model_round_trips():
    record = {'call_sid': 'sample', 'event': 'dial', 'reference': 'sample', 'status': 'open', 'lead_id': 'id-1', 'lead_reference': 'sample', 'previous_state': 'queued', 'current_state': 'queued', 'attempt_count': 1, 'within_window': 'sample', 'window_reason': 'sample', 'transition_allowed': 'sample', 'refusal_reason': 'sample', 'guard_notes': 'sample', 'window_snapshot': 'sample', 'occurred_at': '2026-09-03T10:00:00', 'source': 'voice_gateway', 'campaign': 'sample'}
    saved = store.save('call_state_machine', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for call_state_machine'
    fetched = store.get('call_state_machine', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'call_state_machine did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('call_state_machine', tenant_id=TENANT))
    record = {'call_sid': 'sample', 'crm_system': 'sample', 'destination': 'sample', 'destination_named': 'sample', 'payload_shape': 'sample', 'delivery': 'placeholder', 'unavailable_blocks': 'sample', 'outcome': 'project_interested', 'summary': 'sample', 'note': 'sample', 'intended_method': 'POST', 'reference': 'sample', 'status': 'open'}
    saved = store.save('crm_destination_placeholder', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for crm_destination_placeholder'
    fetched = store.get('crm_destination_placeholder', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'crm_destination_placeholder did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('crm_destination_placeholder', tenant_id=TENANT))
    record = {'operation': 'upload', 'drive_mode': 'stubbed', 'folder_id': 'id-1', 'document_id': 'id-1', 'file_name': 'sample', 'mime_type': 'sample', 'credentials_present': 'sample', 'unavailable_blocks': 'sample', 'delivery': 'stub', 'note': 'sample', 'would_call': 'sample', 'upload_state': 'sample', 'reference': 'sample', 'status': 'open'}
    saved = store.save('google_drive', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for google_drive'
    fetched = store.get('google_drive', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'google_drive did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('google_drive', tenant_id=TENANT))
    record = {'lead_name': 'sample', 'phone': 'sample', 'project_tag': 'sample', 'reference': 'sample', 'status': 'open', 'language': 'en', 'campaign': 'sample', 'source_file': 'sample', 'lead_email': 'guest@example.com', 'property_type': 'apartment', 'budget': 'sample', 'area': 'sample', 'timeline': 'immediate', 'priority': 'sample', 'phone_e164': 'sample', 'dialable': 'sample', 'dialable_reason': 'sample', 'attempt_count': 1, 'max_attempts': 'sample', 'retry_backoff_minutes': 'sample', 'daily_call_cap': 'sample', 'concurrency': 'sample', 'queue_state': 'queued', 'best_call_window': 'sample', 'window_state': 'open', 'dial_scheduled_at': '2026-09-03T10:00:00', 'next_attempt_at': '2026-09-03T10:00:00', 'last_call_sid': 'sample', 'notes': 'sample'}
    saved = store.save('lead_intake_and_dial_queue', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for lead_intake_and_dial_queue'
    fetched = store.get('lead_intake_and_dial_queue', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'lead_intake_and_dial_queue did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('lead_intake_and_dial_queue', tenant_id=TENANT))
    record = {'operation': 'put', 'relative_path': 'sample', 'content': 'sample', 'content_digest': 'sample', 'bytes_written': 'sample', 'root': 'sample', 'tenant_root': 'sample', 'entries': 'sample', 'file_exists': 'sample', 'size_bytes': 'sample', 'media_type': 'sample', 'reference': 'sample', 'status': 'open'}
    saved = store.save('local_drive', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for local_drive'
    fetched = store.get('local_drive', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'local_drive did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('local_drive', tenant_id=TENANT))
    record = {'method': 'tools/list', 'tool': 'sample', 'arguments': 'sample', 'catalog_scope': 'platform', 'tool_count': 1, 'dispatched': 'sample', 'error_code': 'id-1', 'protocol': 'sample', 'duration_ms': 'sample', 'reference': 'sample', 'status': 'open'}
    saved = store.save('mcp_adapter', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for mcp_adapter'
    fetched = store.get('mcp_adapter', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'mcp_adapter did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('mcp_adapter', tenant_id=TENANT))
    record = {'trigger_event': 'lead_qualified', 'channel': 'webhook', 'target': 'sample', 'subject': 'sample', 'body': 'sample', 'delivery': 'delivered', 'provider': 'sample', 'attempts': 'sample', 'response_code': 'id-1', 'delivered_at': '2026-09-03T10:00:00', 'unavailable_blocks': 'sample', 'message_digest': 'sample', 'summary': 'sample', 'outcome': 'project_interested', 'call_sid': 'sample', 'campaign': 'sample', 'reference': 'sample', 'status': 'open'}
    saved = store.save('notification', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for notification'
    fetched = store.get('notification', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'notification did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('notification', tenant_id=TENANT))
    record = {'call_sid': 'sample', 'event_type': 'attempted', 'sequence': 'sample', 'prev_hash': 'sample', 'entry_hash': 'sample', 'payload_digest': 'sample', 'outcome': 'project_interested', 'actor': 'sample', 'campaign': 'sample', 'detail': 'sample', 'chain_ok': 'sample', 'verified_count': 1, 'reference': 'sample', 'status': 'open'}
    saved = store.save('outcome_capture_and_ledger', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for outcome_capture_and_ledger'
    fetched = store.get('outcome_capture_and_ledger', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'outcome_capture_and_ledger did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('outcome_capture_and_ledger', tenant_id=TENANT))
    record = {'project_tag': 'sample', 'question': 'sample', 'claim_type': 'price', 'language': 'en', 'answer': 'sample', 'pitch': 'sample', 'citations': 'sample', 'source_documents': 'sample', 'retrieved_count': 1, 'withheld': 'sample', 'withheld_claims': 'sample', 'authority_layer': 'sample', 'authority_label': 'sample', 'divergence': 'sample', 'campaign': 'sample', 'reference': 'sample', 'status': 'open'}
    saved = store.save('project_knowledge_grounding', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for project_knowledge_grounding'
    fetched = store.get('project_knowledge_grounding', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'project_knowledge_grounding did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('project_knowledge_grounding', tenant_id=TENANT))
    record = {'call_sid': 'sample', 'outcome': 'project_interested', 'language': 'en', 'project_tag': 'sample', 'lead_name': 'sample', 'property_type': 'apartment', 'budget': 'sample', 'currency': 'sample', 'area': 'sample', 'timeline': 'immediate', 'transcript': 'sample', 'collected': 'sample', 'summary': 'sample', 'summary_text': 'sample', 'recommendation': 'sample', 'next_action': 'transfer_to_broker', 'qualified': 'sample', 'transfer_required': 'sample', 'authority_layer': 'sample', 'authority_label': 'sample', 'campaign': 'sample', 'reference': 'sample', 'status': 'open'}
    saved = store.save('qualification_and_broker_summary', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for qualification_and_broker_summary'
    fetched = store.get('qualification_and_broker_summary', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'qualification_and_broker_summary did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('qualification_and_broker_summary', tenant_id=TENANT))
    record = {'call_sid': 'sample', 'to_number': 'sample', 'from_number': 'sample', 'direction': 'outbound', 'language': 'en', 'call_status': 'initiated', 'call_event': 'sample', 'transition_to': 'queued', 'mapping_ok': 'sample', 'twiml': 'sample', 'asr_transcript': 'sample', 'tts_text': 'sample', 'tts_voice': 'sample', 'gather_language': 'sample', 'conference_sid': 'sample', 'duration_seconds': 'sample', 'attempt': 'sample', 'provider': 'sample', 'call_key_source': 'sample', 'edge_stub': 'sample', 'unavailable_blocks': 'sample', 'reference': 'sample', 'status': 'open', 'voice_action': 'originate'}
    saved = store.save('voice_gateway', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for voice_gateway'
    fetched = store.get('voice_gateway', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'voice_gateway did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('voice_gateway', tenant_id=TENANT))
    record = {'call_sid': 'sample', 'outcome': 'transferred', 'lead_id': 'id-1', 'project_tag': 'sample', 'qualified_outcome': 'project_interested', 'broker_number': 'sample', 'broker_language': 'en', 'whisper_text': 'sample', 'summary': 'sample', 'step_count': 1, 'conference_name': 'sample', 'conference_sid': 'sample', 'bridge_seconds': 'sample', 'attempt': 'sample', 'transfer_key': 'sample', 'edge_stub': 'sample', 'unavailable_blocks': 'sample', 'reference': 'sample', 'status': 'open'}
    saved = store.save('warm_transfer', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for warm_transfer'
    fetched = store.get('warm_transfer', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'warm_transfer did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('warm_transfer', tenant_id=TENANT))


def test_models_expose_their_fields():
    assert MODELS, 'no models were generated'
    for cap_id, cls in MODELS.items():
        instance = cls.from_dict({})
        assert instance.to_dict()['id'] is None
        assert cls.FIELDS, cap_id
