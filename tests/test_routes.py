"""The HTTP surface answers, and what it answers has the right shape."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
AUTH = {'Authorization': 'Bearer ' + __import__('os').environ.get('PLATFORM_TOKEN', 'dev-local-token')}


def _listed(payload):
    """Same list shapes as PRODUCT round-trip (_listed / _listed_records).

    Hard-coding listed.json()['items'] KeyError'd when GET answered
    {ok: False} or {records: [...]} — pytest then reported only
    'suite is red' with no capability id (sess_5dfb4a3 class).
    """
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    if payload.get("ok") is False:
        return []
    for key in ("items", "records", "results", "data", "rows"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return []


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["ok"] is True
    names = {item["name"] for item in body["checks"]}
    assert {"process", "persistent_disk", "database", "migrations"} <= names
    assert all(item["ok"] for item in body["checks"])


def test_kernel_jobs_roster():
    """GET /v1/jobs publishes every kernel JD; distinctive routes answer."""
    resp = client.get("/v1/jobs")
    assert resp.status_code == 200
    jobs = resp.json()["jobs"]
    by_kernel = {j["kernel"]: j for j in jobs}
    assert set(by_kernel) == {
        "COLLECTOR", "CLONER", "WRITER", "TESTER", "STORE_MANAGER"
    }
    assert by_kernel["COLLECTOR"]["title"] == "Binding surveyor"
    assert by_kernel["CLONER"]["title"] == "Block stocker"
    assert by_kernel["WRITER"]["title"] == "Platform manufacturer"
    assert by_kernel["TESTER"]["title"] == "Acceptance inspector"
    assert by_kernel["STORE_MANAGER"]["title"] == "Store registrar"
    for job in jobs:
        assert job["mandate"] and job["http_routes"] and job["agent"]
    catalog = client.get("/v1/catalog")
    assert catalog.status_code == 200
    assert catalog.json()["kernel"] == "COLLECTOR"
    inventory = client.get("/v1/inventory")
    assert inventory.status_code == 200
    assert inventory.json()["kernel"] == "CLONER"
    assert "lock" in inventory.json()
    caps_resp = client.get("/v1/capabilities")
    assert caps_resp.status_code == 200
    assert isinstance(caps_resp.json()["items"], list)
    gates = client.get("/v1/gates")
    assert gates.status_code == 200
    assert gates.json()["kernel"] == "TESTER"
    assert gates.json()["runs_over_http"] is False
    prov = client.get("/v1/provenance")
    assert prov.status_code == 200
    assert prov.json()["kernel"] == "STORE_MANAGER"


def test_every_capability_route_answers():
    """Code-phase: each capability POST answers HTTP 200 JSON.
    Store ok: False is allowed here — acceptance is the pilot test."""
    failures = []
    payload = {'lead_name': 'sample', 'phone': 'sample', 'project_tag': 'sample', 'reference': 'sample', 'status': 'open', 'language': 'en', 'campaign': 'sample', 'source_file': 'sample', 'lead_email': 'guest@example.com', 'property_type': 'apartment', 'budget': 'sample', 'area': 'sample', 'timeline': 'immediate', 'priority': 'sample', 'phone_e164': 'sample', 'dialable': 'sample', 'dialable_reason': 'sample', 'attempt_count': 1, 'max_attempts': 'sample', 'retry_backoff_minutes': 'sample', 'daily_call_cap': 'sample', 'concurrency': 'sample', 'queue_state': 'queued', 'best_call_window': 'sample', 'window_state': 'open', 'dial_scheduled_at': '2026-09-03T10:00:00', 'next_attempt_at': '2026-09-03T10:00:00', 'last_call_sid': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/lead_intake_and_dial_queue", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('lead_intake_and_dial_queue: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('lead_intake_and_dial_queue: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('lead_intake_and_dial_queue: JSON body is not a dict')
            # A connector with no credentials answers as a DECLARED
            # STUB -- ok:true, naming what is unavailable. That IS the
            # right answer before the operator configures it.
            elif 'blocks_unavailable' in body or 'blocks_unavailable' in str(body.get('result')):
                unavailable = body.get('blocks_unavailable') or (
                    (body.get('result') or {}).get('blocks_unavailable')
                    if isinstance(body.get('result'), dict) else None)
                if body.get('ok') is not True or not unavailable:
                    failures.append('lead_intake_and_dial_queue: declared stub must be ok:true' + ' and name blocks_unavailable')
            listed = client.get("/v1/lead_intake_and_dial_queue", headers=AUTH)
            if listed.status_code != 200:
                failures.append('lead_intake_and_dial_queue list: HTTP ' + str(listed.status_code))

    payload = {'call_sid': 'sample', 'event': 'dial', 'reference': 'sample', 'status': 'open', 'lead_id': 'id-1', 'lead_reference': 'sample', 'previous_state': 'queued', 'current_state': 'queued', 'attempt_count': 1, 'within_window': 'sample', 'window_reason': 'sample', 'transition_allowed': 'sample', 'refusal_reason': 'sample', 'guard_notes': 'sample', 'window_snapshot': 'sample', 'occurred_at': '2026-09-03T10:00:00', 'source': 'voice_gateway', 'campaign': 'sample'}
    resp = client.post("/v1/call_state_machine", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('call_state_machine: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('call_state_machine: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('call_state_machine: JSON body is not a dict')
            # A connector with no credentials answers as a DECLARED
            # STUB -- ok:true, naming what is unavailable. That IS the
            # right answer before the operator configures it.
            elif 'blocks_unavailable' in body or 'blocks_unavailable' in str(body.get('result')):
                unavailable = body.get('blocks_unavailable') or (
                    (body.get('result') or {}).get('blocks_unavailable')
                    if isinstance(body.get('result'), dict) else None)
                if body.get('ok') is not True or not unavailable:
                    failures.append('call_state_machine: declared stub must be ok:true' + ' and name blocks_unavailable')
            listed = client.get("/v1/call_state_machine", headers=AUTH)
            if listed.status_code != 200:
                failures.append('call_state_machine list: HTTP ' + str(listed.status_code))

    payload = {'project_tag': 'sample', 'question': 'sample', 'claim_type': 'price', 'language': 'en', 'answer': 'sample', 'pitch': 'sample', 'citations': 'sample', 'source_documents': 'sample', 'retrieved_count': 1, 'withheld': 'sample', 'withheld_claims': 'sample', 'authority_layer': 'sample', 'authority_label': 'sample', 'divergence': 'sample', 'campaign': 'sample', 'reference': 'sample', 'status': 'open'}
    resp = client.post("/v1/project_knowledge_grounding", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('project_knowledge_grounding: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('project_knowledge_grounding: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('project_knowledge_grounding: JSON body is not a dict')
            # A connector with no credentials answers as a DECLARED
            # STUB -- ok:true, naming what is unavailable. That IS the
            # right answer before the operator configures it.
            elif 'blocks_unavailable' in body or 'blocks_unavailable' in str(body.get('result')):
                unavailable = body.get('blocks_unavailable') or (
                    (body.get('result') or {}).get('blocks_unavailable')
                    if isinstance(body.get('result'), dict) else None)
                if body.get('ok') is not True or not unavailable:
                    failures.append('project_knowledge_grounding: declared stub must be ok:true' + ' and name blocks_unavailable')
            listed = client.get("/v1/project_knowledge_grounding", headers=AUTH)
            if listed.status_code != 200:
                failures.append('project_knowledge_grounding list: HTTP ' + str(listed.status_code))

    payload = {'call_sid': 'sample', 'to_number': 'sample', 'from_number': 'sample', 'direction': 'outbound', 'language': 'en', 'call_status': 'initiated', 'call_event': 'sample', 'transition_to': 'queued', 'mapping_ok': 'sample', 'twiml': 'sample', 'asr_transcript': 'sample', 'tts_text': 'sample', 'tts_voice': 'sample', 'gather_language': 'sample', 'conference_sid': 'sample', 'duration_seconds': 'sample', 'attempt': 'sample', 'provider': 'sample', 'call_key_source': 'sample', 'edge_stub': 'sample', 'unavailable_blocks': 'sample', 'reference': 'sample', 'status': 'open', 'voice_action': 'originate'}
    resp = client.post("/v1/voice_gateway", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('voice_gateway: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('voice_gateway: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('voice_gateway: JSON body is not a dict')
            # A connector with no credentials answers as a DECLARED
            # STUB -- ok:true, naming what is unavailable. That IS the
            # right answer before the operator configures it.
            elif 'blocks_unavailable' in body or 'blocks_unavailable' in str(body.get('result')):
                unavailable = body.get('blocks_unavailable') or (
                    (body.get('result') or {}).get('blocks_unavailable')
                    if isinstance(body.get('result'), dict) else None)
                if body.get('ok') is not True or not unavailable:
                    failures.append('voice_gateway: declared stub must be ok:true' + ' and name blocks_unavailable')
            listed = client.get("/v1/voice_gateway", headers=AUTH)
            if listed.status_code != 200:
                failures.append('voice_gateway list: HTTP ' + str(listed.status_code))

    payload = {'call_sid': 'sample', 'outcome': 'transferred', 'lead_id': 'id-1', 'project_tag': 'sample', 'qualified_outcome': 'project_interested', 'broker_number': 'sample', 'broker_language': 'en', 'whisper_text': 'sample', 'summary': 'sample', 'step_count': 1, 'conference_name': 'sample', 'conference_sid': 'sample', 'bridge_seconds': 'sample', 'attempt': 'sample', 'transfer_key': 'sample', 'edge_stub': 'sample', 'unavailable_blocks': 'sample', 'reference': 'sample', 'status': 'open'}
    resp = client.post("/v1/warm_transfer", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('warm_transfer: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('warm_transfer: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('warm_transfer: JSON body is not a dict')
            # A connector with no credentials answers as a DECLARED
            # STUB -- ok:true, naming what is unavailable. That IS the
            # right answer before the operator configures it.
            elif 'blocks_unavailable' in body or 'blocks_unavailable' in str(body.get('result')):
                unavailable = body.get('blocks_unavailable') or (
                    (body.get('result') or {}).get('blocks_unavailable')
                    if isinstance(body.get('result'), dict) else None)
                if body.get('ok') is not True or not unavailable:
                    failures.append('warm_transfer: declared stub must be ok:true' + ' and name blocks_unavailable')
            listed = client.get("/v1/warm_transfer", headers=AUTH)
            if listed.status_code != 200:
                failures.append('warm_transfer list: HTTP ' + str(listed.status_code))

    payload = {'call_sid': 'sample', 'outcome': 'project_interested', 'language': 'en', 'project_tag': 'sample', 'lead_name': 'sample', 'property_type': 'apartment', 'budget': 'sample', 'currency': 'sample', 'area': 'sample', 'timeline': 'immediate', 'transcript': 'sample', 'collected': 'sample', 'summary': 'sample', 'summary_text': 'sample', 'recommendation': 'sample', 'next_action': 'transfer_to_broker', 'qualified': 'sample', 'transfer_required': 'sample', 'authority_layer': 'sample', 'authority_label': 'sample', 'campaign': 'sample', 'reference': 'sample', 'status': 'open'}
    resp = client.post("/v1/qualification_and_broker_summary", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('qualification_and_broker_summary: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('qualification_and_broker_summary: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('qualification_and_broker_summary: JSON body is not a dict')
            # A connector with no credentials answers as a DECLARED
            # STUB -- ok:true, naming what is unavailable. That IS the
            # right answer before the operator configures it.
            elif 'blocks_unavailable' in body or 'blocks_unavailable' in str(body.get('result')):
                unavailable = body.get('blocks_unavailable') or (
                    (body.get('result') or {}).get('blocks_unavailable')
                    if isinstance(body.get('result'), dict) else None)
                if body.get('ok') is not True or not unavailable:
                    failures.append('qualification_and_broker_summary: declared stub must be ok:true' + ' and name blocks_unavailable')
            listed = client.get("/v1/qualification_and_broker_summary", headers=AUTH)
            if listed.status_code != 200:
                failures.append('qualification_and_broker_summary list: HTTP ' + str(listed.status_code))

    payload = {'call_sid': 'sample', 'event_type': 'attempted', 'sequence': 'sample', 'prev_hash': 'sample', 'entry_hash': 'sample', 'payload_digest': 'sample', 'outcome': 'project_interested', 'actor': 'sample', 'campaign': 'sample', 'detail': 'sample', 'chain_ok': 'sample', 'verified_count': 1, 'reference': 'sample', 'status': 'open'}
    resp = client.post("/v1/outcome_capture_and_ledger", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('outcome_capture_and_ledger: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('outcome_capture_and_ledger: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('outcome_capture_and_ledger: JSON body is not a dict')
            # A connector with no credentials answers as a DECLARED
            # STUB -- ok:true, naming what is unavailable. That IS the
            # right answer before the operator configures it.
            elif 'blocks_unavailable' in body or 'blocks_unavailable' in str(body.get('result')):
                unavailable = body.get('blocks_unavailable') or (
                    (body.get('result') or {}).get('blocks_unavailable')
                    if isinstance(body.get('result'), dict) else None)
                if body.get('ok') is not True or not unavailable:
                    failures.append('outcome_capture_and_ledger: declared stub must be ok:true' + ' and name blocks_unavailable')
            listed = client.get("/v1/outcome_capture_and_ledger", headers=AUTH)
            if listed.status_code != 200:
                failures.append('outcome_capture_and_ledger list: HTTP ' + str(listed.status_code))

    payload = {'call_sid': 'sample', 'crm_system': 'sample', 'destination': 'sample', 'destination_named': 'sample', 'payload_shape': 'sample', 'delivery': 'placeholder', 'unavailable_blocks': 'sample', 'outcome': 'project_interested', 'summary': 'sample', 'note': 'sample', 'intended_method': 'POST', 'reference': 'sample', 'status': 'open'}
    resp = client.post("/v1/crm_destination_placeholder", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('crm_destination_placeholder: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('crm_destination_placeholder: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('crm_destination_placeholder: JSON body is not a dict')
            # A connector with no credentials answers as a DECLARED
            # STUB -- ok:true, naming what is unavailable. That IS the
            # right answer before the operator configures it.
            elif 'blocks_unavailable' in body or 'blocks_unavailable' in str(body.get('result')):
                unavailable = body.get('blocks_unavailable') or (
                    (body.get('result') or {}).get('blocks_unavailable')
                    if isinstance(body.get('result'), dict) else None)
                if body.get('ok') is not True or not unavailable:
                    failures.append('crm_destination_placeholder: declared stub must be ok:true' + ' and name blocks_unavailable')
            listed = client.get("/v1/crm_destination_placeholder", headers=AUTH)
            if listed.status_code != 200:
                failures.append('crm_destination_placeholder list: HTTP ' + str(listed.status_code))

    payload = {'trigger_event': 'lead_qualified', 'channel': 'webhook', 'target': 'sample', 'subject': 'sample', 'body': 'sample', 'delivery': 'delivered', 'provider': 'sample', 'attempts': 'sample', 'response_code': 'id-1', 'delivered_at': '2026-09-03T10:00:00', 'unavailable_blocks': 'sample', 'message_digest': 'sample', 'summary': 'sample', 'outcome': 'project_interested', 'call_sid': 'sample', 'campaign': 'sample', 'reference': 'sample', 'status': 'open'}
    resp = client.post("/v1/notification", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('notification: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('notification: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('notification: JSON body is not a dict')
            # A connector with no credentials answers as a DECLARED
            # STUB -- ok:true, naming what is unavailable. That IS the
            # right answer before the operator configures it.
            elif 'blocks_unavailable' in body or 'blocks_unavailable' in str(body.get('result')):
                unavailable = body.get('blocks_unavailable') or (
                    (body.get('result') or {}).get('blocks_unavailable')
                    if isinstance(body.get('result'), dict) else None)
                if body.get('ok') is not True or not unavailable:
                    failures.append('notification: declared stub must be ok:true' + ' and name blocks_unavailable')
            listed = client.get("/v1/notification", headers=AUTH)
            if listed.status_code != 200:
                failures.append('notification list: HTTP ' + str(listed.status_code))

    payload = {'operation': 'put', 'relative_path': 'sample', 'content': 'sample', 'content_digest': 'sample', 'bytes_written': 'sample', 'root': 'sample', 'tenant_root': 'sample', 'entries': 'sample', 'file_exists': 'sample', 'size_bytes': 'sample', 'media_type': 'sample', 'reference': 'sample', 'status': 'open'}
    resp = client.post("/v1/local_drive", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('local_drive: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('local_drive: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('local_drive: JSON body is not a dict')
            # A connector with no credentials answers as a DECLARED
            # STUB -- ok:true, naming what is unavailable. That IS the
            # right answer before the operator configures it.
            elif 'blocks_unavailable' in body or 'blocks_unavailable' in str(body.get('result')):
                unavailable = body.get('blocks_unavailable') or (
                    (body.get('result') or {}).get('blocks_unavailable')
                    if isinstance(body.get('result'), dict) else None)
                if body.get('ok') is not True or not unavailable:
                    failures.append('local_drive: declared stub must be ok:true' + ' and name blocks_unavailable')
            listed = client.get("/v1/local_drive", headers=AUTH)
            if listed.status_code != 200:
                failures.append('local_drive list: HTTP ' + str(listed.status_code))

    payload = {'operation': 'upload', 'drive_mode': 'stubbed', 'folder_id': 'id-1', 'document_id': 'id-1', 'file_name': 'sample', 'mime_type': 'sample', 'credentials_present': 'sample', 'unavailable_blocks': 'sample', 'delivery': 'stub', 'note': 'sample', 'would_call': 'sample', 'upload_state': 'sample', 'reference': 'sample', 'status': 'open'}
    resp = client.post("/v1/google_drive", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('google_drive: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('google_drive: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('google_drive: JSON body is not a dict')
            # A connector with no credentials answers as a DECLARED
            # STUB -- ok:true, naming what is unavailable. That IS the
            # right answer before the operator configures it.
            elif 'blocks_unavailable' in body or 'blocks_unavailable' in str(body.get('result')):
                unavailable = body.get('blocks_unavailable') or (
                    (body.get('result') or {}).get('blocks_unavailable')
                    if isinstance(body.get('result'), dict) else None)
                if body.get('ok') is not True or not unavailable:
                    failures.append('google_drive: declared stub must be ok:true' + ' and name blocks_unavailable')
            listed = client.get("/v1/google_drive", headers=AUTH)
            if listed.status_code != 200:
                failures.append('google_drive list: HTTP ' + str(listed.status_code))

    payload = {'method': 'tools/list', 'tool': 'sample', 'arguments': 'sample', 'catalog_scope': 'platform', 'tool_count': 1, 'dispatched': 'sample', 'error_code': 'id-1', 'protocol': 'sample', 'duration_ms': 'sample', 'reference': 'sample', 'status': 'open'}
    resp = client.post("/v1/mcp_adapter", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('mcp_adapter: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('mcp_adapter: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('mcp_adapter: JSON body is not a dict')
            # A connector with no credentials answers as a DECLARED
            # STUB -- ok:true, naming what is unavailable. That IS the
            # right answer before the operator configures it.
            elif 'blocks_unavailable' in body or 'blocks_unavailable' in str(body.get('result')):
                unavailable = body.get('blocks_unavailable') or (
                    (body.get('result') or {}).get('blocks_unavailable')
                    if isinstance(body.get('result'), dict) else None)
                if body.get('ok') is not True or not unavailable:
                    failures.append('mcp_adapter: declared stub must be ok:true' + ' and name blocks_unavailable')
            listed = client.get("/v1/mcp_adapter", headers=AUTH)
            if listed.status_code != 200:
                failures.append('mcp_adapter list: HTTP ' + str(listed.status_code))

    assert not failures, "; ".join(failures)


@pytest.mark.pilot
def test_every_capability_route_accepts_payload():
    """Pilot: spec payload is accepted (ok is not False) and persisted.
    Not the factory code-phase gate."""
    failures = []
    payload = {'lead_name': 'sample', 'phone': 'sample', 'project_tag': 'sample', 'reference': 'sample', 'status': 'open', 'language': 'en', 'campaign': 'sample', 'source_file': 'sample', 'lead_email': 'guest@example.com', 'property_type': 'apartment', 'budget': 'sample', 'area': 'sample', 'timeline': 'immediate', 'priority': 'sample', 'phone_e164': 'sample', 'dialable': 'sample', 'dialable_reason': 'sample', 'attempt_count': 1, 'max_attempts': 'sample', 'retry_backoff_minutes': 'sample', 'daily_call_cap': 'sample', 'concurrency': 'sample', 'queue_state': 'queued', 'best_call_window': 'sample', 'window_state': 'open', 'dial_scheduled_at': '2026-09-03T10:00:00', 'next_attempt_at': '2026-09-03T10:00:00', 'last_call_sid': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/lead_intake_and_dial_queue", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('lead_intake_and_dial_queue: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('lead_intake_and_dial_queue rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/lead_intake_and_dial_queue", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('lead_intake_and_dial_queue list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('lead_intake_and_dial_queue list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('lead_intake_and_dial_queue accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/lead_intake_and_dial_queue/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('lead_intake_and_dial_queue get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/lead_intake_and_dial_queue/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('lead_intake_and_dial_queue missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'call_sid': 'sample', 'event': 'dial', 'reference': 'sample', 'status': 'open', 'lead_id': 'id-1', 'lead_reference': 'sample', 'previous_state': 'queued', 'current_state': 'queued', 'attempt_count': 1, 'within_window': 'sample', 'window_reason': 'sample', 'transition_allowed': 'sample', 'refusal_reason': 'sample', 'guard_notes': 'sample', 'window_snapshot': 'sample', 'occurred_at': '2026-09-03T10:00:00', 'source': 'voice_gateway', 'campaign': 'sample'}
    resp = client.post("/v1/call_state_machine", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('call_state_machine: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('call_state_machine rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/call_state_machine", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('call_state_machine list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('call_state_machine list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('call_state_machine accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/call_state_machine/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('call_state_machine get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/call_state_machine/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('call_state_machine missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'project_tag': 'sample', 'question': 'sample', 'claim_type': 'price', 'language': 'en', 'answer': 'sample', 'pitch': 'sample', 'citations': 'sample', 'source_documents': 'sample', 'retrieved_count': 1, 'withheld': 'sample', 'withheld_claims': 'sample', 'authority_layer': 'sample', 'authority_label': 'sample', 'divergence': 'sample', 'campaign': 'sample', 'reference': 'sample', 'status': 'open'}
    resp = client.post("/v1/project_knowledge_grounding", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('project_knowledge_grounding: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('project_knowledge_grounding rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/project_knowledge_grounding", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('project_knowledge_grounding list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('project_knowledge_grounding list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('project_knowledge_grounding accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/project_knowledge_grounding/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('project_knowledge_grounding get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/project_knowledge_grounding/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('project_knowledge_grounding missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'call_sid': 'sample', 'to_number': 'sample', 'from_number': 'sample', 'direction': 'outbound', 'language': 'en', 'call_status': 'initiated', 'call_event': 'sample', 'transition_to': 'queued', 'mapping_ok': 'sample', 'twiml': 'sample', 'asr_transcript': 'sample', 'tts_text': 'sample', 'tts_voice': 'sample', 'gather_language': 'sample', 'conference_sid': 'sample', 'duration_seconds': 'sample', 'attempt': 'sample', 'provider': 'sample', 'call_key_source': 'sample', 'edge_stub': 'sample', 'unavailable_blocks': 'sample', 'reference': 'sample', 'status': 'open', 'voice_action': 'originate'}
    resp = client.post("/v1/voice_gateway", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('voice_gateway: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('voice_gateway rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/voice_gateway", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('voice_gateway list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('voice_gateway list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('voice_gateway accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/voice_gateway/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('voice_gateway get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/voice_gateway/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('voice_gateway missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'call_sid': 'sample', 'outcome': 'transferred', 'lead_id': 'id-1', 'project_tag': 'sample', 'qualified_outcome': 'project_interested', 'broker_number': 'sample', 'broker_language': 'en', 'whisper_text': 'sample', 'summary': 'sample', 'step_count': 1, 'conference_name': 'sample', 'conference_sid': 'sample', 'bridge_seconds': 'sample', 'attempt': 'sample', 'transfer_key': 'sample', 'edge_stub': 'sample', 'unavailable_blocks': 'sample', 'reference': 'sample', 'status': 'open'}
    resp = client.post("/v1/warm_transfer", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('warm_transfer: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('warm_transfer rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/warm_transfer", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('warm_transfer list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('warm_transfer list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('warm_transfer accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/warm_transfer/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('warm_transfer get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/warm_transfer/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('warm_transfer missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'call_sid': 'sample', 'outcome': 'project_interested', 'language': 'en', 'project_tag': 'sample', 'lead_name': 'sample', 'property_type': 'apartment', 'budget': 'sample', 'currency': 'sample', 'area': 'sample', 'timeline': 'immediate', 'transcript': 'sample', 'collected': 'sample', 'summary': 'sample', 'summary_text': 'sample', 'recommendation': 'sample', 'next_action': 'transfer_to_broker', 'qualified': 'sample', 'transfer_required': 'sample', 'authority_layer': 'sample', 'authority_label': 'sample', 'campaign': 'sample', 'reference': 'sample', 'status': 'open'}
    resp = client.post("/v1/qualification_and_broker_summary", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('qualification_and_broker_summary: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('qualification_and_broker_summary rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/qualification_and_broker_summary", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('qualification_and_broker_summary list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('qualification_and_broker_summary list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('qualification_and_broker_summary accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/qualification_and_broker_summary/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('qualification_and_broker_summary get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/qualification_and_broker_summary/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('qualification_and_broker_summary missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'call_sid': 'sample', 'event_type': 'attempted', 'sequence': 'sample', 'prev_hash': 'sample', 'entry_hash': 'sample', 'payload_digest': 'sample', 'outcome': 'project_interested', 'actor': 'sample', 'campaign': 'sample', 'detail': 'sample', 'chain_ok': 'sample', 'verified_count': 1, 'reference': 'sample', 'status': 'open'}
    resp = client.post("/v1/outcome_capture_and_ledger", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('outcome_capture_and_ledger: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('outcome_capture_and_ledger rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/outcome_capture_and_ledger", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('outcome_capture_and_ledger list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('outcome_capture_and_ledger list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('outcome_capture_and_ledger accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/outcome_capture_and_ledger/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('outcome_capture_and_ledger get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/outcome_capture_and_ledger/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('outcome_capture_and_ledger missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'call_sid': 'sample', 'crm_system': 'sample', 'destination': 'sample', 'destination_named': 'sample', 'payload_shape': 'sample', 'delivery': 'placeholder', 'unavailable_blocks': 'sample', 'outcome': 'project_interested', 'summary': 'sample', 'note': 'sample', 'intended_method': 'POST', 'reference': 'sample', 'status': 'open'}
    resp = client.post("/v1/crm_destination_placeholder", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('crm_destination_placeholder: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('crm_destination_placeholder rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/crm_destination_placeholder", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('crm_destination_placeholder list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('crm_destination_placeholder list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('crm_destination_placeholder accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/crm_destination_placeholder/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('crm_destination_placeholder get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/crm_destination_placeholder/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('crm_destination_placeholder missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'trigger_event': 'lead_qualified', 'channel': 'webhook', 'target': 'sample', 'subject': 'sample', 'body': 'sample', 'delivery': 'delivered', 'provider': 'sample', 'attempts': 'sample', 'response_code': 'id-1', 'delivered_at': '2026-09-03T10:00:00', 'unavailable_blocks': 'sample', 'message_digest': 'sample', 'summary': 'sample', 'outcome': 'project_interested', 'call_sid': 'sample', 'campaign': 'sample', 'reference': 'sample', 'status': 'open'}
    resp = client.post("/v1/notification", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('notification: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('notification rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/notification", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('notification list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('notification list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('notification accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/notification/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('notification get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/notification/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('notification missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'operation': 'put', 'relative_path': 'sample', 'content': 'sample', 'content_digest': 'sample', 'bytes_written': 'sample', 'root': 'sample', 'tenant_root': 'sample', 'entries': 'sample', 'file_exists': 'sample', 'size_bytes': 'sample', 'media_type': 'sample', 'reference': 'sample', 'status': 'open'}
    resp = client.post("/v1/local_drive", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('local_drive: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('local_drive rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/local_drive", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('local_drive list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('local_drive list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('local_drive accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/local_drive/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('local_drive get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/local_drive/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('local_drive missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'operation': 'upload', 'drive_mode': 'stubbed', 'folder_id': 'id-1', 'document_id': 'id-1', 'file_name': 'sample', 'mime_type': 'sample', 'credentials_present': 'sample', 'unavailable_blocks': 'sample', 'delivery': 'stub', 'note': 'sample', 'would_call': 'sample', 'upload_state': 'sample', 'reference': 'sample', 'status': 'open'}
    resp = client.post("/v1/google_drive", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('google_drive: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('google_drive rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/google_drive", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('google_drive list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('google_drive list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('google_drive accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/google_drive/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('google_drive get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/google_drive/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('google_drive missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'method': 'tools/list', 'tool': 'sample', 'arguments': 'sample', 'catalog_scope': 'platform', 'tool_count': 1, 'dispatched': 'sample', 'error_code': 'id-1', 'protocol': 'sample', 'duration_ms': 'sample', 'reference': 'sample', 'status': 'open'}
    resp = client.post("/v1/mcp_adapter", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('mcp_adapter: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('mcp_adapter rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/mcp_adapter", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('mcp_adapter list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('mcp_adapter list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('mcp_adapter accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/mcp_adapter/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('mcp_adapter get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/mcp_adapter/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('mcp_adapter missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    assert not failures, "; ".join(failures)
