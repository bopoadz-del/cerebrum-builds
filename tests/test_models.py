"""Models must survive a round trip through sqlite."""

from app import store
from app.models import MODELS


#: Tenant the generated tests act as (the platform token's tenant).
TENANT = 'local'


def test_every_model_round_trips():
    record = {'reference': 'sample', 'status': 'open', 'call_sid': 'sample', 'lead_name': 'sample', 'phone': 'sample', 'current_state': 'queued', 'previous_state': 'queued', 'call_window': 'sample', 'window_state': 'open', 'transition_event': 'sample', 'attempt_count': 1, 'notes': 'sample'}
    saved = store.save('call_state_machine', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for call_state_machine'
    fetched = store.get('call_state_machine', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'call_state_machine did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('call_state_machine', tenant_id=TENANT))
    record = {'reference': 'sample', 'status': 'open', 'crm_system': 'unstated', 'destination_url': 'sample', 'payload_shape': 'sample', 'delivery_state': 'queued', 'mock_mode': True, 'notes': 'sample'}
    saved = store.save('crm_destination_placeholder', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for crm_destination_placeholder'
    fetched = store.get('crm_destination_placeholder', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'crm_destination_placeholder did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('crm_destination_placeholder', tenant_id=TENANT))
    record = {'reference': 'sample', 'status': 'open', 'drive_mode': 'stubbed', 'folder_id': 'id-1', 'file_name': 'sample', 'operation': 'upload', 'credential_setting': 'sample', 'notes': 'sample'}
    saved = store.save('google_drive', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for google_drive'
    fetched = store.get('google_drive', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'google_drive did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('google_drive', tenant_id=TENANT))
    record = {'reference': 'sample', 'status': 'open', 'lead_name': 'sample', 'phone': 'sample', 'language': 'en', 'project_tag': 'sample', 'source_file': 'sample', 'call_window': 'sample', 'daily_call_cap': 1, 'concurrency': 1, 'attempt_count': 1, 'retry_backoff_minutes': 1, 'queue_status': 'queued', 'notes': 'sample'}
    saved = store.save('lead_intake_and_dial_queue', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for lead_intake_and_dial_queue'
    fetched = store.get('lead_intake_and_dial_queue', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'lead_intake_and_dial_queue did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('lead_intake_and_dial_queue', tenant_id=TENANT))
    record = {'reference': 'sample', 'status': 'open', 'root_path': 'sample', 'relative_path': 'sample', 'operation': 'read', 'bytes_written': 1, 'content_preview': 'sample', 'notes': 'sample'}
    saved = store.save('local_drive', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for local_drive'
    fetched = store.get('local_drive', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'local_drive did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('local_drive', tenant_id=TENANT))
    record = {'reference': 'sample', 'status': 'open', 'tool_name': 'sample', 'catalog_scope': 'platform', 'request_shape': 'sample', 'response_shape': 'sample', 'notes': 'sample'}
    saved = store.save('mcp_adapter', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for mcp_adapter'
    fetched = store.get('mcp_adapter', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'mcp_adapter did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('mcp_adapter', tenant_id=TENANT))
    record = {'reference': 'sample', 'status': 'open', 'channel': 'email', 'recipient': 'sample', 'subject': 'sample', 'message': 'sample', 'trigger_event': 'lead_qualified', 'delivery_state': 'queued', 'notes': 'sample'}
    saved = store.save('notification', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for notification'
    fetched = store.get('notification', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'notification did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('notification', tenant_id=TENANT))
    record = {'reference': 'sample', 'status': 'open', 'call_sid': 'sample', 'campaign': 'sample', 'event_type': 'attempt', 'outcome': 'project_interested', 'attempt_count': 1, 'ledger_index': 1, 'vector_clock': 'sample', 'notes': 'sample'}
    saved = store.save('outcome_capture_and_ledger', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for outcome_capture_and_ledger'
    fetched = store.get('outcome_capture_and_ledger', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'outcome_capture_and_ledger did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('outcome_capture_and_ledger', tenant_id=TENANT))
    record = {'reference': 'sample', 'status': 'open', 'project_tag': 'sample', 'claim_type': 'price', 'question': 'sample', 'document_name': 'sample', 'document_text': 'sample', 'citation': 'sample', 'authority_label': 'certified', 'grounded': True, 'answer': 'sample', 'notes': 'sample'}
    saved = store.save('project_knowledge_grounding', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for project_knowledge_grounding'
    fetched = store.get('project_knowledge_grounding', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'project_knowledge_grounding did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('project_knowledge_grounding', tenant_id=TENANT))
    record = {'reference': 'sample', 'status': 'open', 'call_sid': 'sample', 'lead_name': 'sample', 'outcome': 'project_interested', 'property_type': 'apartment', 'budget': 1.0, 'area': 'sample', 'timeline': 'sample', 'currency_setting': 'sample', 'broker_summary': 'sample', 'recommended_action': 'sample', 'notes': 'sample'}
    saved = store.save('qualification_and_broker_summary', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for qualification_and_broker_summary'
    fetched = store.get('qualification_and_broker_summary', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'qualification_and_broker_summary did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('qualification_and_broker_summary', tenant_id=TENANT))
    record = {'reference': 'sample', 'status': 'open', 'call_sid': 'sample', 'direction': 'outbound', 'to_number': 'sample', 'from_number': 'sample', 'language': 'en', 'voice': 'sample', 'asr_engine': 'twilio_gather_speech', 'twilio_mode': 'stubbed', 'call_status': 'initiated', 'twiml': 'sample', 'recording_url': 'sample', 'notes': 'sample'}
    saved = store.save('voice_gateway', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for voice_gateway'
    fetched = store.get('voice_gateway', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'voice_gateway did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('voice_gateway', tenant_id=TENANT))
    record = {'reference': 'sample', 'status': 'open', 'call_sid': 'sample', 'lead_name': 'sample', 'outcome': 'project_interested', 'broker_number': 'sample', 'conference_name': 'sample', 'summary': 'sample', 'whisper_text': 'sample', 'transfer_status': 'initiated', 'whisper_delivered': True, 'notes': 'sample'}
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
