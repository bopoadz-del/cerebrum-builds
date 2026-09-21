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
    resp = client.get("/v1/jobs", headers=AUTH)
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
    catalog = client.get("/v1/catalog", headers=AUTH)
    assert catalog.status_code == 200
    assert catalog.json()["kernel"] == "COLLECTOR"
    inventory = client.get("/v1/inventory", headers=AUTH)
    assert inventory.status_code == 200
    assert inventory.json()["kernel"] == "CLONER"
    assert "lock" in inventory.json()
    caps_resp = client.get("/v1/capabilities", headers=AUTH)
    assert caps_resp.status_code == 200
    assert isinstance(caps_resp.json()["items"], list)
    gates = client.get("/v1/gates", headers=AUTH)
    assert gates.status_code == 200
    assert gates.json()["kernel"] == "TESTER"
    assert gates.json()["runs_over_http"] is False
    prov = client.get("/v1/provenance", headers=AUTH)
    assert prov.status_code == 200
    assert prov.json()["kernel"] == "STORE_MANAGER"


def test_every_capability_route_answers():
    """Code-phase: each capability POST answers HTTP 200 JSON.
    Store ok: False is allowed here — acceptance is the pilot test."""
    failures = []
    payload = {'reference': 'sample', 'status': 'open', 'lead_name': 'sample', 'phone': 'sample', 'language': 'en', 'project_tag': 'sample', 'source_file': 'sample', 'call_window': 'sample', 'daily_call_cap': 1, 'concurrency': 1, 'attempt_count': 1, 'retry_backoff_minutes': 1, 'queue_status': 'queued', 'notes': 'sample'}
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
            # right answer before the operator configures it. Judged
            # only when THIS response declares itself a stub at the top
            # level; a stubbed block nested inside a capability's result
            # is that capability's business, and ok:false stays allowed.
            elif 'blocks_unavailable' in body:
                unavailable = body.get('blocks_unavailable')
                if body.get('ok') is not True or not unavailable:
                    failures.append('lead_intake_and_dial_queue: declared stub must be ok:true' + ' and name blocks_unavailable')
            listed = client.get("/v1/lead_intake_and_dial_queue", headers=AUTH)
            if listed.status_code != 200:
                failures.append('lead_intake_and_dial_queue list: HTTP ' + str(listed.status_code))

    payload = {'reference': 'sample', 'status': 'open', 'call_sid': 'sample', 'lead_name': 'sample', 'phone': 'sample', 'current_state': 'queued', 'previous_state': 'queued', 'call_window': 'sample', 'window_state': 'open', 'transition_event': 'sample', 'attempt_count': 1, 'notes': 'sample'}
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
            # right answer before the operator configures it. Judged
            # only when THIS response declares itself a stub at the top
            # level; a stubbed block nested inside a capability's result
            # is that capability's business, and ok:false stays allowed.
            elif 'blocks_unavailable' in body:
                unavailable = body.get('blocks_unavailable')
                if body.get('ok') is not True or not unavailable:
                    failures.append('call_state_machine: declared stub must be ok:true' + ' and name blocks_unavailable')
            listed = client.get("/v1/call_state_machine", headers=AUTH)
            if listed.status_code != 200:
                failures.append('call_state_machine list: HTTP ' + str(listed.status_code))

    payload = {'reference': 'sample', 'status': 'open', 'project_tag': 'sample', 'claim_type': 'price', 'question': 'sample', 'document_name': 'sample', 'document_text': 'sample', 'citation': 'sample', 'authority_label': 'certified', 'grounded': True, 'answer': 'sample', 'notes': 'sample'}
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
            # right answer before the operator configures it. Judged
            # only when THIS response declares itself a stub at the top
            # level; a stubbed block nested inside a capability's result
            # is that capability's business, and ok:false stays allowed.
            elif 'blocks_unavailable' in body:
                unavailable = body.get('blocks_unavailable')
                if body.get('ok') is not True or not unavailable:
                    failures.append('project_knowledge_grounding: declared stub must be ok:true' + ' and name blocks_unavailable')
            listed = client.get("/v1/project_knowledge_grounding", headers=AUTH)
            if listed.status_code != 200:
                failures.append('project_knowledge_grounding list: HTTP ' + str(listed.status_code))

    payload = {'reference': 'sample', 'status': 'open', 'call_sid': 'sample', 'direction': 'outbound', 'to_number': 'sample', 'from_number': 'sample', 'language': 'en', 'voice': 'sample', 'asr_engine': 'twilio_gather_speech', 'twilio_mode': 'stubbed', 'call_status': 'initiated', 'twiml': 'sample', 'recording_url': 'sample', 'notes': 'sample'}
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
            # right answer before the operator configures it. Judged
            # only when THIS response declares itself a stub at the top
            # level; a stubbed block nested inside a capability's result
            # is that capability's business, and ok:false stays allowed.
            elif 'blocks_unavailable' in body:
                unavailable = body.get('blocks_unavailable')
                if body.get('ok') is not True or not unavailable:
                    failures.append('voice_gateway: declared stub must be ok:true' + ' and name blocks_unavailable')
            listed = client.get("/v1/voice_gateway", headers=AUTH)
            if listed.status_code != 200:
                failures.append('voice_gateway list: HTTP ' + str(listed.status_code))

    payload = {'reference': 'sample', 'status': 'open', 'call_sid': 'sample', 'lead_name': 'sample', 'outcome': 'project_interested', 'broker_number': 'sample', 'conference_name': 'sample', 'summary': 'sample', 'whisper_text': 'sample', 'transfer_status': 'initiated', 'whisper_delivered': True, 'notes': 'sample'}
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
            # right answer before the operator configures it. Judged
            # only when THIS response declares itself a stub at the top
            # level; a stubbed block nested inside a capability's result
            # is that capability's business, and ok:false stays allowed.
            elif 'blocks_unavailable' in body:
                unavailable = body.get('blocks_unavailable')
                if body.get('ok') is not True or not unavailable:
                    failures.append('warm_transfer: declared stub must be ok:true' + ' and name blocks_unavailable')
            listed = client.get("/v1/warm_transfer", headers=AUTH)
            if listed.status_code != 200:
                failures.append('warm_transfer list: HTTP ' + str(listed.status_code))

    payload = {'reference': 'sample', 'status': 'open', 'call_sid': 'sample', 'lead_name': 'sample', 'outcome': 'project_interested', 'property_type': 'apartment', 'budget': 1.0, 'area': 'sample', 'timeline': 'sample', 'currency_setting': 'sample', 'broker_summary': 'sample', 'recommended_action': 'sample', 'notes': 'sample'}
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
            # right answer before the operator configures it. Judged
            # only when THIS response declares itself a stub at the top
            # level; a stubbed block nested inside a capability's result
            # is that capability's business, and ok:false stays allowed.
            elif 'blocks_unavailable' in body:
                unavailable = body.get('blocks_unavailable')
                if body.get('ok') is not True or not unavailable:
                    failures.append('qualification_and_broker_summary: declared stub must be ok:true' + ' and name blocks_unavailable')
            listed = client.get("/v1/qualification_and_broker_summary", headers=AUTH)
            if listed.status_code != 200:
                failures.append('qualification_and_broker_summary list: HTTP ' + str(listed.status_code))

    payload = {'reference': 'sample', 'status': 'open', 'call_sid': 'sample', 'campaign': 'sample', 'event_type': 'attempt', 'outcome': 'project_interested', 'attempt_count': 1, 'ledger_index': 1, 'vector_clock': 'sample', 'notes': 'sample'}
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
            # right answer before the operator configures it. Judged
            # only when THIS response declares itself a stub at the top
            # level; a stubbed block nested inside a capability's result
            # is that capability's business, and ok:false stays allowed.
            elif 'blocks_unavailable' in body:
                unavailable = body.get('blocks_unavailable')
                if body.get('ok') is not True or not unavailable:
                    failures.append('outcome_capture_and_ledger: declared stub must be ok:true' + ' and name blocks_unavailable')
            listed = client.get("/v1/outcome_capture_and_ledger", headers=AUTH)
            if listed.status_code != 200:
                failures.append('outcome_capture_and_ledger list: HTTP ' + str(listed.status_code))

    payload = {'reference': 'sample', 'status': 'open', 'crm_system': 'unstated', 'destination_url': 'sample', 'payload_shape': 'sample', 'delivery_state': 'queued', 'mock_mode': True, 'notes': 'sample'}
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
            # right answer before the operator configures it. Judged
            # only when THIS response declares itself a stub at the top
            # level; a stubbed block nested inside a capability's result
            # is that capability's business, and ok:false stays allowed.
            elif 'blocks_unavailable' in body:
                unavailable = body.get('blocks_unavailable')
                if body.get('ok') is not True or not unavailable:
                    failures.append('crm_destination_placeholder: declared stub must be ok:true' + ' and name blocks_unavailable')
            listed = client.get("/v1/crm_destination_placeholder", headers=AUTH)
            if listed.status_code != 200:
                failures.append('crm_destination_placeholder list: HTTP ' + str(listed.status_code))

    payload = {'reference': 'sample', 'status': 'open', 'channel': 'email', 'recipient': 'sample', 'subject': 'sample', 'message': 'sample', 'trigger_event': 'lead_qualified', 'delivery_state': 'queued', 'notes': 'sample'}
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
            # right answer before the operator configures it. Judged
            # only when THIS response declares itself a stub at the top
            # level; a stubbed block nested inside a capability's result
            # is that capability's business, and ok:false stays allowed.
            elif 'blocks_unavailable' in body:
                unavailable = body.get('blocks_unavailable')
                if body.get('ok') is not True or not unavailable:
                    failures.append('notification: declared stub must be ok:true' + ' and name blocks_unavailable')
            listed = client.get("/v1/notification", headers=AUTH)
            if listed.status_code != 200:
                failures.append('notification list: HTTP ' + str(listed.status_code))

    payload = {'reference': 'sample', 'status': 'open', 'root_path': 'sample', 'relative_path': 'sample', 'operation': 'read', 'bytes_written': 1, 'content_preview': 'sample', 'notes': 'sample'}
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
            # right answer before the operator configures it. Judged
            # only when THIS response declares itself a stub at the top
            # level; a stubbed block nested inside a capability's result
            # is that capability's business, and ok:false stays allowed.
            elif 'blocks_unavailable' in body:
                unavailable = body.get('blocks_unavailable')
                if body.get('ok') is not True or not unavailable:
                    failures.append('local_drive: declared stub must be ok:true' + ' and name blocks_unavailable')
            listed = client.get("/v1/local_drive", headers=AUTH)
            if listed.status_code != 200:
                failures.append('local_drive list: HTTP ' + str(listed.status_code))

    payload = {'reference': 'sample', 'status': 'open', 'drive_mode': 'stubbed', 'folder_id': 'id-1', 'file_name': 'sample', 'operation': 'upload', 'credential_setting': 'sample', 'notes': 'sample'}
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
            # right answer before the operator configures it. Judged
            # only when THIS response declares itself a stub at the top
            # level; a stubbed block nested inside a capability's result
            # is that capability's business, and ok:false stays allowed.
            elif 'blocks_unavailable' in body:
                unavailable = body.get('blocks_unavailable')
                if body.get('ok') is not True or not unavailable:
                    failures.append('google_drive: declared stub must be ok:true' + ' and name blocks_unavailable')
            listed = client.get("/v1/google_drive", headers=AUTH)
            if listed.status_code != 200:
                failures.append('google_drive list: HTTP ' + str(listed.status_code))

    payload = {'reference': 'sample', 'status': 'open', 'tool_name': 'sample', 'catalog_scope': 'platform', 'request_shape': 'sample', 'response_shape': 'sample', 'notes': 'sample'}
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
            # right answer before the operator configures it. Judged
            # only when THIS response declares itself a stub at the top
            # level; a stubbed block nested inside a capability's result
            # is that capability's business, and ok:false stays allowed.
            elif 'blocks_unavailable' in body:
                unavailable = body.get('blocks_unavailable')
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
    payload = {'reference': 'sample', 'status': 'open', 'lead_name': 'sample', 'phone': 'sample', 'language': 'en', 'project_tag': 'sample', 'source_file': 'sample', 'call_window': 'sample', 'daily_call_cap': 1, 'concurrency': 1, 'attempt_count': 1, 'retry_backoff_minutes': 1, 'queue_status': 'queued', 'notes': 'sample'}
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

    payload = {'reference': 'sample', 'status': 'open', 'call_sid': 'sample', 'lead_name': 'sample', 'phone': 'sample', 'current_state': 'queued', 'previous_state': 'queued', 'call_window': 'sample', 'window_state': 'open', 'transition_event': 'sample', 'attempt_count': 1, 'notes': 'sample'}
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

    payload = {'reference': 'sample', 'status': 'open', 'project_tag': 'sample', 'claim_type': 'price', 'question': 'sample', 'document_name': 'sample', 'document_text': 'sample', 'citation': 'sample', 'authority_label': 'certified', 'grounded': True, 'answer': 'sample', 'notes': 'sample'}
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

    payload = {'reference': 'sample', 'status': 'open', 'call_sid': 'sample', 'direction': 'outbound', 'to_number': 'sample', 'from_number': 'sample', 'language': 'en', 'voice': 'sample', 'asr_engine': 'twilio_gather_speech', 'twilio_mode': 'stubbed', 'call_status': 'initiated', 'twiml': 'sample', 'recording_url': 'sample', 'notes': 'sample'}
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

    payload = {'reference': 'sample', 'status': 'open', 'call_sid': 'sample', 'lead_name': 'sample', 'outcome': 'project_interested', 'broker_number': 'sample', 'conference_name': 'sample', 'summary': 'sample', 'whisper_text': 'sample', 'transfer_status': 'initiated', 'whisper_delivered': True, 'notes': 'sample'}
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

    payload = {'reference': 'sample', 'status': 'open', 'call_sid': 'sample', 'lead_name': 'sample', 'outcome': 'project_interested', 'property_type': 'apartment', 'budget': 1.0, 'area': 'sample', 'timeline': 'sample', 'currency_setting': 'sample', 'broker_summary': 'sample', 'recommended_action': 'sample', 'notes': 'sample'}
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

    payload = {'reference': 'sample', 'status': 'open', 'call_sid': 'sample', 'campaign': 'sample', 'event_type': 'attempt', 'outcome': 'project_interested', 'attempt_count': 1, 'ledger_index': 1, 'vector_clock': 'sample', 'notes': 'sample'}
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

    payload = {'reference': 'sample', 'status': 'open', 'crm_system': 'unstated', 'destination_url': 'sample', 'payload_shape': 'sample', 'delivery_state': 'queued', 'mock_mode': True, 'notes': 'sample'}
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

    payload = {'reference': 'sample', 'status': 'open', 'channel': 'email', 'recipient': 'sample', 'subject': 'sample', 'message': 'sample', 'trigger_event': 'lead_qualified', 'delivery_state': 'queued', 'notes': 'sample'}
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

    payload = {'reference': 'sample', 'status': 'open', 'root_path': 'sample', 'relative_path': 'sample', 'operation': 'read', 'bytes_written': 1, 'content_preview': 'sample', 'notes': 'sample'}
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

    payload = {'reference': 'sample', 'status': 'open', 'drive_mode': 'stubbed', 'folder_id': 'id-1', 'file_name': 'sample', 'operation': 'upload', 'credential_setting': 'sample', 'notes': 'sample'}
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

    payload = {'reference': 'sample', 'status': 'open', 'tool_name': 'sample', 'catalog_scope': 'platform', 'request_shape': 'sample', 'response_shape': 'sample', 'notes': 'sample'}
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
