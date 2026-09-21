"""Counter-cases: what each capability REFUSES.

Written by the factory TESTER role. The floor (negative_floor) requires four
per capability; these four are derived from each capability's own spec. Add
the domain cases the brief implies -- the boundary of a rule, a state machine
that must not skip a step -- they count toward the same floor.
"""

import os

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer " + os.environ.get("PLATFORM_TOKEN", "dev-local-token")}
OTHER_TENANT = {
    "Authorization": "Bearer " + os.environ.get("PLATFORM_TOKEN_B", "dev-local-token-b")
}

REFUSED = (400, 403, 404, 409, 422)


def _refused(response):
    """A refusal, by status or by the envelope's own ok:false."""
    if response.status_code in REFUSED:
        return True
    if response.status_code != 200:
        return False
    try:
        body = response.json()
    except Exception:
        return False
    return isinstance(body, dict) and body.get("ok") is False



# -- call_state_machine ------------------------------------------


def test_call_state_machine_refuses_a_missing_required_field():
    """A partial record is refused, never completed by the handler."""
    body = {'status': 'open', 'call_sid': 'sample', 'lead_name': 'sample', 'phone': 'sample', 'current_state': 'queued', 'previous_state': 'queued', 'call_window': 'sample', 'window_state': 'open', 'transition_event': 'sample', 'attempt_count': 1, 'notes': 'sample'}
    resp = client.post("/v1/call_state_machine", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "call_state_machine accepted a payload with no reference: " + resp.text[:200]
    )


def test_call_state_machine_refuses_a_value_outside_its_vocabulary():
    """A column that accepts any string is not that column."""
    body = {'reference': 'sample', 'status': 'not-a-declared-value', 'call_sid': 'sample', 'lead_name': 'sample', 'phone': 'sample', 'current_state': 'queued', 'previous_state': 'queued', 'call_window': 'sample', 'window_state': 'open', 'transition_event': 'sample', 'attempt_count': 1, 'notes': 'sample'}
    resp = client.post("/v1/call_state_machine", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "call_state_machine accepted an undeclared status: " + resp.text[:200]
    )


def test_call_state_machine_does_not_leak_across_tenants():
    """404, never 403 and never the row: existence itself is private."""
    body = {'reference': 'sample', 'status': 'open', 'call_sid': 'sample', 'lead_name': 'sample', 'phone': 'sample', 'current_state': 'queued', 'previous_state': 'queued', 'call_window': 'sample', 'window_state': 'open', 'transition_event': 'sample', 'attempt_count': 1, 'notes': 'sample'}
    made = client.post("/v1/call_state_machine", json=body, headers=AUTH)
    if made.status_code != 200:
        pytest.skip("capability did not accept the sample record")
    try:
        record = made.json()
    except Exception:
        pytest.skip("capability did not answer JSON")
    rid = (record.get("id") or (record.get("result") or {}).get("id")
           if isinstance(record, dict) else None)
    if not rid:
        pytest.skip("capability returned no record id to read back")
    other = client.get("/v1/call_state_machine/" + str(rid), headers=OTHER_TENANT)
    assert other.status_code == 404, (
        "call_state_machine answered %s to another tenant, not 404" % other.status_code
    )


def test_call_state_machine_refuses_a_malformed_payload():
    """Garbage in is a refusal, never a 500 and never a stored row."""
    for junk in ([], "", {"": None}, {"x" * 300: "y" * 2000}):
        resp = client.post("/v1/call_state_machine", json=junk, headers=AUTH)
        assert resp.status_code != 500, (
            "call_state_machine raised on malformed input: " + resp.text[:200]
        )
        assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
            "call_state_machine accepted malformed input %r" % (junk,)
        )


# -- crm_destination_placeholder ---------------------------------


def test_crm_destination_placeholder_refuses_a_missing_required_field():
    """A partial record is refused, never completed by the handler."""
    body = {'status': 'open', 'crm_system': 'unstated', 'destination_url': 'sample', 'payload_shape': 'sample', 'delivery_state': 'queued', 'mock_mode': True, 'notes': 'sample'}
    resp = client.post("/v1/crm_destination_placeholder", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "crm_destination_placeholder accepted a payload with no reference: " + resp.text[:200]
    )


def test_crm_destination_placeholder_refuses_a_value_outside_its_vocabulary():
    """A column that accepts any string is not that column."""
    body = {'reference': 'sample', 'status': 'not-a-declared-value', 'crm_system': 'unstated', 'destination_url': 'sample', 'payload_shape': 'sample', 'delivery_state': 'queued', 'mock_mode': True, 'notes': 'sample'}
    resp = client.post("/v1/crm_destination_placeholder", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "crm_destination_placeholder accepted an undeclared status: " + resp.text[:200]
    )


def test_crm_destination_placeholder_does_not_leak_across_tenants():
    """404, never 403 and never the row: existence itself is private."""
    body = {'reference': 'sample', 'status': 'open', 'crm_system': 'unstated', 'destination_url': 'sample', 'payload_shape': 'sample', 'delivery_state': 'queued', 'mock_mode': True, 'notes': 'sample'}
    made = client.post("/v1/crm_destination_placeholder", json=body, headers=AUTH)
    if made.status_code != 200:
        pytest.skip("capability did not accept the sample record")
    try:
        record = made.json()
    except Exception:
        pytest.skip("capability did not answer JSON")
    rid = (record.get("id") or (record.get("result") or {}).get("id")
           if isinstance(record, dict) else None)
    if not rid:
        pytest.skip("capability returned no record id to read back")
    other = client.get("/v1/crm_destination_placeholder/" + str(rid), headers=OTHER_TENANT)
    assert other.status_code == 404, (
        "crm_destination_placeholder answered %s to another tenant, not 404" % other.status_code
    )


def test_crm_destination_placeholder_refuses_a_malformed_payload():
    """Garbage in is a refusal, never a 500 and never a stored row."""
    for junk in ([], "", {"": None}, {"x" * 300: "y" * 2000}):
        resp = client.post("/v1/crm_destination_placeholder", json=junk, headers=AUTH)
        assert resp.status_code != 500, (
            "crm_destination_placeholder raised on malformed input: " + resp.text[:200]
        )
        assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
            "crm_destination_placeholder accepted malformed input %r" % (junk,)
        )


# -- google_drive ------------------------------------------------


def test_google_drive_refuses_a_missing_required_field():
    """A partial record is refused, never completed by the handler."""
    body = {'status': 'open', 'drive_mode': 'stubbed', 'folder_id': 'id-1', 'file_name': 'sample', 'operation': 'upload', 'credential_setting': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/google_drive", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "google_drive accepted a payload with no reference: " + resp.text[:200]
    )


def test_google_drive_refuses_a_value_outside_its_vocabulary():
    """A column that accepts any string is not that column."""
    body = {'reference': 'sample', 'status': 'not-a-declared-value', 'drive_mode': 'stubbed', 'folder_id': 'id-1', 'file_name': 'sample', 'operation': 'upload', 'credential_setting': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/google_drive", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "google_drive accepted an undeclared status: " + resp.text[:200]
    )


def test_google_drive_does_not_leak_across_tenants():
    """404, never 403 and never the row: existence itself is private."""
    body = {'reference': 'sample', 'status': 'open', 'drive_mode': 'stubbed', 'folder_id': 'id-1', 'file_name': 'sample', 'operation': 'upload', 'credential_setting': 'sample', 'notes': 'sample'}
    made = client.post("/v1/google_drive", json=body, headers=AUTH)
    if made.status_code != 200:
        pytest.skip("capability did not accept the sample record")
    try:
        record = made.json()
    except Exception:
        pytest.skip("capability did not answer JSON")
    rid = (record.get("id") or (record.get("result") or {}).get("id")
           if isinstance(record, dict) else None)
    if not rid:
        pytest.skip("capability returned no record id to read back")
    other = client.get("/v1/google_drive/" + str(rid), headers=OTHER_TENANT)
    assert other.status_code == 404, (
        "google_drive answered %s to another tenant, not 404" % other.status_code
    )


def test_google_drive_refuses_a_malformed_payload():
    """Garbage in is a refusal, never a 500 and never a stored row."""
    for junk in ([], "", {"": None}, {"x" * 300: "y" * 2000}):
        resp = client.post("/v1/google_drive", json=junk, headers=AUTH)
        assert resp.status_code != 500, (
            "google_drive raised on malformed input: " + resp.text[:200]
        )
        assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
            "google_drive accepted malformed input %r" % (junk,)
        )


# -- lead_intake_and_dial_queue ----------------------------------


def test_lead_intake_and_dial_queue_refuses_a_missing_required_field():
    """A partial record is refused, never completed by the handler."""
    body = {'status': 'open', 'lead_name': 'sample', 'phone': 'sample', 'language': 'en', 'project_tag': 'sample', 'source_file': 'sample', 'call_window': 'sample', 'daily_call_cap': 1, 'concurrency': 1, 'attempt_count': 1, 'retry_backoff_minutes': 1, 'queue_status': 'queued', 'notes': 'sample'}
    resp = client.post("/v1/lead_intake_and_dial_queue", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "lead_intake_and_dial_queue accepted a payload with no reference: " + resp.text[:200]
    )


def test_lead_intake_and_dial_queue_refuses_a_value_outside_its_vocabulary():
    """A column that accepts any string is not that column."""
    body = {'reference': 'sample', 'status': 'not-a-declared-value', 'lead_name': 'sample', 'phone': 'sample', 'language': 'en', 'project_tag': 'sample', 'source_file': 'sample', 'call_window': 'sample', 'daily_call_cap': 1, 'concurrency': 1, 'attempt_count': 1, 'retry_backoff_minutes': 1, 'queue_status': 'queued', 'notes': 'sample'}
    resp = client.post("/v1/lead_intake_and_dial_queue", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "lead_intake_and_dial_queue accepted an undeclared status: " + resp.text[:200]
    )


def test_lead_intake_and_dial_queue_does_not_leak_across_tenants():
    """404, never 403 and never the row: existence itself is private."""
    body = {'reference': 'sample', 'status': 'open', 'lead_name': 'sample', 'phone': 'sample', 'language': 'en', 'project_tag': 'sample', 'source_file': 'sample', 'call_window': 'sample', 'daily_call_cap': 1, 'concurrency': 1, 'attempt_count': 1, 'retry_backoff_minutes': 1, 'queue_status': 'queued', 'notes': 'sample'}
    made = client.post("/v1/lead_intake_and_dial_queue", json=body, headers=AUTH)
    if made.status_code != 200:
        pytest.skip("capability did not accept the sample record")
    try:
        record = made.json()
    except Exception:
        pytest.skip("capability did not answer JSON")
    rid = (record.get("id") or (record.get("result") or {}).get("id")
           if isinstance(record, dict) else None)
    if not rid:
        pytest.skip("capability returned no record id to read back")
    other = client.get("/v1/lead_intake_and_dial_queue/" + str(rid), headers=OTHER_TENANT)
    assert other.status_code == 404, (
        "lead_intake_and_dial_queue answered %s to another tenant, not 404" % other.status_code
    )


def test_lead_intake_and_dial_queue_refuses_a_malformed_payload():
    """Garbage in is a refusal, never a 500 and never a stored row."""
    for junk in ([], "", {"": None}, {"x" * 300: "y" * 2000}):
        resp = client.post("/v1/lead_intake_and_dial_queue", json=junk, headers=AUTH)
        assert resp.status_code != 500, (
            "lead_intake_and_dial_queue raised on malformed input: " + resp.text[:200]
        )
        assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
            "lead_intake_and_dial_queue accepted malformed input %r" % (junk,)
        )


# -- local_drive -------------------------------------------------


def test_local_drive_refuses_a_missing_required_field():
    """A partial record is refused, never completed by the handler."""
    body = {'status': 'open', 'root_path': 'sample', 'relative_path': 'sample', 'operation': 'read', 'bytes_written': 1, 'content_preview': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/local_drive", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "local_drive accepted a payload with no reference: " + resp.text[:200]
    )


def test_local_drive_refuses_a_value_outside_its_vocabulary():
    """A column that accepts any string is not that column."""
    body = {'reference': 'sample', 'status': 'not-a-declared-value', 'root_path': 'sample', 'relative_path': 'sample', 'operation': 'read', 'bytes_written': 1, 'content_preview': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/local_drive", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "local_drive accepted an undeclared status: " + resp.text[:200]
    )


def test_local_drive_does_not_leak_across_tenants():
    """404, never 403 and never the row: existence itself is private."""
    body = {'reference': 'sample', 'status': 'open', 'root_path': 'sample', 'relative_path': 'sample', 'operation': 'read', 'bytes_written': 1, 'content_preview': 'sample', 'notes': 'sample'}
    made = client.post("/v1/local_drive", json=body, headers=AUTH)
    if made.status_code != 200:
        pytest.skip("capability did not accept the sample record")
    try:
        record = made.json()
    except Exception:
        pytest.skip("capability did not answer JSON")
    rid = (record.get("id") or (record.get("result") or {}).get("id")
           if isinstance(record, dict) else None)
    if not rid:
        pytest.skip("capability returned no record id to read back")
    other = client.get("/v1/local_drive/" + str(rid), headers=OTHER_TENANT)
    assert other.status_code == 404, (
        "local_drive answered %s to another tenant, not 404" % other.status_code
    )


def test_local_drive_refuses_a_malformed_payload():
    """Garbage in is a refusal, never a 500 and never a stored row."""
    for junk in ([], "", {"": None}, {"x" * 300: "y" * 2000}):
        resp = client.post("/v1/local_drive", json=junk, headers=AUTH)
        assert resp.status_code != 500, (
            "local_drive raised on malformed input: " + resp.text[:200]
        )
        assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
            "local_drive accepted malformed input %r" % (junk,)
        )


# -- mcp_adapter -------------------------------------------------


def test_mcp_adapter_refuses_a_missing_required_field():
    """A partial record is refused, never completed by the handler."""
    body = {'status': 'open', 'tool_name': 'sample', 'catalog_scope': 'platform', 'request_shape': 'sample', 'response_shape': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/mcp_adapter", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "mcp_adapter accepted a payload with no reference: " + resp.text[:200]
    )


def test_mcp_adapter_refuses_a_value_outside_its_vocabulary():
    """A column that accepts any string is not that column."""
    body = {'reference': 'sample', 'status': 'not-a-declared-value', 'tool_name': 'sample', 'catalog_scope': 'platform', 'request_shape': 'sample', 'response_shape': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/mcp_adapter", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "mcp_adapter accepted an undeclared status: " + resp.text[:200]
    )


def test_mcp_adapter_does_not_leak_across_tenants():
    """404, never 403 and never the row: existence itself is private."""
    body = {'reference': 'sample', 'status': 'open', 'tool_name': 'sample', 'catalog_scope': 'platform', 'request_shape': 'sample', 'response_shape': 'sample', 'notes': 'sample'}
    made = client.post("/v1/mcp_adapter", json=body, headers=AUTH)
    if made.status_code != 200:
        pytest.skip("capability did not accept the sample record")
    try:
        record = made.json()
    except Exception:
        pytest.skip("capability did not answer JSON")
    rid = (record.get("id") or (record.get("result") or {}).get("id")
           if isinstance(record, dict) else None)
    if not rid:
        pytest.skip("capability returned no record id to read back")
    other = client.get("/v1/mcp_adapter/" + str(rid), headers=OTHER_TENANT)
    assert other.status_code == 404, (
        "mcp_adapter answered %s to another tenant, not 404" % other.status_code
    )


def test_mcp_adapter_refuses_a_malformed_payload():
    """Garbage in is a refusal, never a 500 and never a stored row."""
    for junk in ([], "", {"": None}, {"x" * 300: "y" * 2000}):
        resp = client.post("/v1/mcp_adapter", json=junk, headers=AUTH)
        assert resp.status_code != 500, (
            "mcp_adapter raised on malformed input: " + resp.text[:200]
        )
        assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
            "mcp_adapter accepted malformed input %r" % (junk,)
        )


# -- notification ------------------------------------------------


def test_notification_refuses_a_missing_required_field():
    """A partial record is refused, never completed by the handler."""
    body = {'status': 'open', 'channel': 'email', 'recipient': 'sample', 'subject': 'sample', 'message': 'sample', 'trigger_event': 'lead_qualified', 'delivery_state': 'queued', 'notes': 'sample'}
    resp = client.post("/v1/notification", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "notification accepted a payload with no reference: " + resp.text[:200]
    )


def test_notification_refuses_a_value_outside_its_vocabulary():
    """A column that accepts any string is not that column."""
    body = {'reference': 'sample', 'status': 'not-a-declared-value', 'channel': 'email', 'recipient': 'sample', 'subject': 'sample', 'message': 'sample', 'trigger_event': 'lead_qualified', 'delivery_state': 'queued', 'notes': 'sample'}
    resp = client.post("/v1/notification", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "notification accepted an undeclared status: " + resp.text[:200]
    )


def test_notification_does_not_leak_across_tenants():
    """404, never 403 and never the row: existence itself is private."""
    body = {'reference': 'sample', 'status': 'open', 'channel': 'email', 'recipient': 'sample', 'subject': 'sample', 'message': 'sample', 'trigger_event': 'lead_qualified', 'delivery_state': 'queued', 'notes': 'sample'}
    made = client.post("/v1/notification", json=body, headers=AUTH)
    if made.status_code != 200:
        pytest.skip("capability did not accept the sample record")
    try:
        record = made.json()
    except Exception:
        pytest.skip("capability did not answer JSON")
    rid = (record.get("id") or (record.get("result") or {}).get("id")
           if isinstance(record, dict) else None)
    if not rid:
        pytest.skip("capability returned no record id to read back")
    other = client.get("/v1/notification/" + str(rid), headers=OTHER_TENANT)
    assert other.status_code == 404, (
        "notification answered %s to another tenant, not 404" % other.status_code
    )


def test_notification_refuses_a_malformed_payload():
    """Garbage in is a refusal, never a 500 and never a stored row."""
    for junk in ([], "", {"": None}, {"x" * 300: "y" * 2000}):
        resp = client.post("/v1/notification", json=junk, headers=AUTH)
        assert resp.status_code != 500, (
            "notification raised on malformed input: " + resp.text[:200]
        )
        assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
            "notification accepted malformed input %r" % (junk,)
        )


# -- outcome_capture_and_ledger ----------------------------------


def test_outcome_capture_and_ledger_refuses_a_missing_required_field():
    """A partial record is refused, never completed by the handler."""
    body = {'status': 'open', 'call_sid': 'sample', 'campaign': 'sample', 'event_type': 'attempt', 'outcome': 'project_interested', 'attempt_count': 1, 'ledger_index': 1, 'vector_clock': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/outcome_capture_and_ledger", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "outcome_capture_and_ledger accepted a payload with no reference: " + resp.text[:200]
    )


def test_outcome_capture_and_ledger_refuses_a_value_outside_its_vocabulary():
    """A column that accepts any string is not that column."""
    body = {'reference': 'sample', 'status': 'not-a-declared-value', 'call_sid': 'sample', 'campaign': 'sample', 'event_type': 'attempt', 'outcome': 'project_interested', 'attempt_count': 1, 'ledger_index': 1, 'vector_clock': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/outcome_capture_and_ledger", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "outcome_capture_and_ledger accepted an undeclared status: " + resp.text[:200]
    )


def test_outcome_capture_and_ledger_does_not_leak_across_tenants():
    """404, never 403 and never the row: existence itself is private."""
    body = {'reference': 'sample', 'status': 'open', 'call_sid': 'sample', 'campaign': 'sample', 'event_type': 'attempt', 'outcome': 'project_interested', 'attempt_count': 1, 'ledger_index': 1, 'vector_clock': 'sample', 'notes': 'sample'}
    made = client.post("/v1/outcome_capture_and_ledger", json=body, headers=AUTH)
    if made.status_code != 200:
        pytest.skip("capability did not accept the sample record")
    try:
        record = made.json()
    except Exception:
        pytest.skip("capability did not answer JSON")
    rid = (record.get("id") or (record.get("result") or {}).get("id")
           if isinstance(record, dict) else None)
    if not rid:
        pytest.skip("capability returned no record id to read back")
    other = client.get("/v1/outcome_capture_and_ledger/" + str(rid), headers=OTHER_TENANT)
    assert other.status_code == 404, (
        "outcome_capture_and_ledger answered %s to another tenant, not 404" % other.status_code
    )


def test_outcome_capture_and_ledger_refuses_a_malformed_payload():
    """Garbage in is a refusal, never a 500 and never a stored row."""
    for junk in ([], "", {"": None}, {"x" * 300: "y" * 2000}):
        resp = client.post("/v1/outcome_capture_and_ledger", json=junk, headers=AUTH)
        assert resp.status_code != 500, (
            "outcome_capture_and_ledger raised on malformed input: " + resp.text[:200]
        )
        assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
            "outcome_capture_and_ledger accepted malformed input %r" % (junk,)
        )


# -- project_knowledge_grounding ---------------------------------


def test_project_knowledge_grounding_refuses_a_missing_required_field():
    """A partial record is refused, never completed by the handler."""
    body = {'status': 'open', 'project_tag': 'sample', 'claim_type': 'price', 'question': 'sample', 'document_name': 'sample', 'document_text': 'sample', 'citation': 'sample', 'authority_label': 'certified', 'grounded': True, 'answer': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/project_knowledge_grounding", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "project_knowledge_grounding accepted a payload with no reference: " + resp.text[:200]
    )


def test_project_knowledge_grounding_refuses_a_value_outside_its_vocabulary():
    """A column that accepts any string is not that column."""
    body = {'reference': 'sample', 'status': 'not-a-declared-value', 'project_tag': 'sample', 'claim_type': 'price', 'question': 'sample', 'document_name': 'sample', 'document_text': 'sample', 'citation': 'sample', 'authority_label': 'certified', 'grounded': True, 'answer': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/project_knowledge_grounding", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "project_knowledge_grounding accepted an undeclared status: " + resp.text[:200]
    )


def test_project_knowledge_grounding_does_not_leak_across_tenants():
    """404, never 403 and never the row: existence itself is private."""
    body = {'reference': 'sample', 'status': 'open', 'project_tag': 'sample', 'claim_type': 'price', 'question': 'sample', 'document_name': 'sample', 'document_text': 'sample', 'citation': 'sample', 'authority_label': 'certified', 'grounded': True, 'answer': 'sample', 'notes': 'sample'}
    made = client.post("/v1/project_knowledge_grounding", json=body, headers=AUTH)
    if made.status_code != 200:
        pytest.skip("capability did not accept the sample record")
    try:
        record = made.json()
    except Exception:
        pytest.skip("capability did not answer JSON")
    rid = (record.get("id") or (record.get("result") or {}).get("id")
           if isinstance(record, dict) else None)
    if not rid:
        pytest.skip("capability returned no record id to read back")
    other = client.get("/v1/project_knowledge_grounding/" + str(rid), headers=OTHER_TENANT)
    assert other.status_code == 404, (
        "project_knowledge_grounding answered %s to another tenant, not 404" % other.status_code
    )


def test_project_knowledge_grounding_refuses_a_malformed_payload():
    """Garbage in is a refusal, never a 500 and never a stored row."""
    for junk in ([], "", {"": None}, {"x" * 300: "y" * 2000}):
        resp = client.post("/v1/project_knowledge_grounding", json=junk, headers=AUTH)
        assert resp.status_code != 500, (
            "project_knowledge_grounding raised on malformed input: " + resp.text[:200]
        )
        assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
            "project_knowledge_grounding accepted malformed input %r" % (junk,)
        )


# -- qualification_and_broker_summary ----------------------------


def test_qualification_and_broker_summary_refuses_a_missing_required_field():
    """A partial record is refused, never completed by the handler."""
    body = {'status': 'open', 'call_sid': 'sample', 'lead_name': 'sample', 'outcome': 'project_interested', 'property_type': 'apartment', 'budget': 1.0, 'area': 'sample', 'timeline': 'sample', 'currency_setting': 'sample', 'broker_summary': 'sample', 'recommended_action': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/qualification_and_broker_summary", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "qualification_and_broker_summary accepted a payload with no reference: " + resp.text[:200]
    )


def test_qualification_and_broker_summary_refuses_a_value_outside_its_vocabulary():
    """A column that accepts any string is not that column."""
    body = {'reference': 'sample', 'status': 'not-a-declared-value', 'call_sid': 'sample', 'lead_name': 'sample', 'outcome': 'project_interested', 'property_type': 'apartment', 'budget': 1.0, 'area': 'sample', 'timeline': 'sample', 'currency_setting': 'sample', 'broker_summary': 'sample', 'recommended_action': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/qualification_and_broker_summary", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "qualification_and_broker_summary accepted an undeclared status: " + resp.text[:200]
    )


def test_qualification_and_broker_summary_does_not_leak_across_tenants():
    """404, never 403 and never the row: existence itself is private."""
    body = {'reference': 'sample', 'status': 'open', 'call_sid': 'sample', 'lead_name': 'sample', 'outcome': 'project_interested', 'property_type': 'apartment', 'budget': 1.0, 'area': 'sample', 'timeline': 'sample', 'currency_setting': 'sample', 'broker_summary': 'sample', 'recommended_action': 'sample', 'notes': 'sample'}
    made = client.post("/v1/qualification_and_broker_summary", json=body, headers=AUTH)
    if made.status_code != 200:
        pytest.skip("capability did not accept the sample record")
    try:
        record = made.json()
    except Exception:
        pytest.skip("capability did not answer JSON")
    rid = (record.get("id") or (record.get("result") or {}).get("id")
           if isinstance(record, dict) else None)
    if not rid:
        pytest.skip("capability returned no record id to read back")
    other = client.get("/v1/qualification_and_broker_summary/" + str(rid), headers=OTHER_TENANT)
    assert other.status_code == 404, (
        "qualification_and_broker_summary answered %s to another tenant, not 404" % other.status_code
    )


def test_qualification_and_broker_summary_refuses_a_malformed_payload():
    """Garbage in is a refusal, never a 500 and never a stored row."""
    for junk in ([], "", {"": None}, {"x" * 300: "y" * 2000}):
        resp = client.post("/v1/qualification_and_broker_summary", json=junk, headers=AUTH)
        assert resp.status_code != 500, (
            "qualification_and_broker_summary raised on malformed input: " + resp.text[:200]
        )
        assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
            "qualification_and_broker_summary accepted malformed input %r" % (junk,)
        )


# -- voice_gateway -----------------------------------------------


def test_voice_gateway_refuses_a_missing_required_field():
    """A partial record is refused, never completed by the handler."""
    body = {'status': 'open', 'call_sid': 'sample', 'direction': 'outbound', 'to_number': 'sample', 'from_number': 'sample', 'language': 'en', 'voice': 'sample', 'asr_engine': 'twilio_gather_speech', 'twilio_mode': 'stubbed', 'call_status': 'initiated', 'twiml': 'sample', 'recording_url': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/voice_gateway", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "voice_gateway accepted a payload with no reference: " + resp.text[:200]
    )


def test_voice_gateway_refuses_a_value_outside_its_vocabulary():
    """A column that accepts any string is not that column."""
    body = {'reference': 'sample', 'status': 'not-a-declared-value', 'call_sid': 'sample', 'direction': 'outbound', 'to_number': 'sample', 'from_number': 'sample', 'language': 'en', 'voice': 'sample', 'asr_engine': 'twilio_gather_speech', 'twilio_mode': 'stubbed', 'call_status': 'initiated', 'twiml': 'sample', 'recording_url': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/voice_gateway", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "voice_gateway accepted an undeclared status: " + resp.text[:200]
    )


def test_voice_gateway_does_not_leak_across_tenants():
    """404, never 403 and never the row: existence itself is private."""
    body = {'reference': 'sample', 'status': 'open', 'call_sid': 'sample', 'direction': 'outbound', 'to_number': 'sample', 'from_number': 'sample', 'language': 'en', 'voice': 'sample', 'asr_engine': 'twilio_gather_speech', 'twilio_mode': 'stubbed', 'call_status': 'initiated', 'twiml': 'sample', 'recording_url': 'sample', 'notes': 'sample'}
    made = client.post("/v1/voice_gateway", json=body, headers=AUTH)
    if made.status_code != 200:
        pytest.skip("capability did not accept the sample record")
    try:
        record = made.json()
    except Exception:
        pytest.skip("capability did not answer JSON")
    rid = (record.get("id") or (record.get("result") or {}).get("id")
           if isinstance(record, dict) else None)
    if not rid:
        pytest.skip("capability returned no record id to read back")
    other = client.get("/v1/voice_gateway/" + str(rid), headers=OTHER_TENANT)
    assert other.status_code == 404, (
        "voice_gateway answered %s to another tenant, not 404" % other.status_code
    )


def test_voice_gateway_refuses_a_malformed_payload():
    """Garbage in is a refusal, never a 500 and never a stored row."""
    for junk in ([], "", {"": None}, {"x" * 300: "y" * 2000}):
        resp = client.post("/v1/voice_gateway", json=junk, headers=AUTH)
        assert resp.status_code != 500, (
            "voice_gateway raised on malformed input: " + resp.text[:200]
        )
        assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
            "voice_gateway accepted malformed input %r" % (junk,)
        )


# -- warm_transfer -----------------------------------------------


def test_warm_transfer_refuses_a_missing_required_field():
    """A partial record is refused, never completed by the handler."""
    body = {'status': 'open', 'call_sid': 'sample', 'lead_name': 'sample', 'outcome': 'project_interested', 'broker_number': 'sample', 'conference_name': 'sample', 'summary': 'sample', 'whisper_text': 'sample', 'transfer_status': 'initiated', 'whisper_delivered': True, 'notes': 'sample'}
    resp = client.post("/v1/warm_transfer", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "warm_transfer accepted a payload with no reference: " + resp.text[:200]
    )


def test_warm_transfer_refuses_a_value_outside_its_vocabulary():
    """A column that accepts any string is not that column."""
    body = {'reference': 'sample', 'status': 'not-a-declared-value', 'call_sid': 'sample', 'lead_name': 'sample', 'outcome': 'project_interested', 'broker_number': 'sample', 'conference_name': 'sample', 'summary': 'sample', 'whisper_text': 'sample', 'transfer_status': 'initiated', 'whisper_delivered': True, 'notes': 'sample'}
    resp = client.post("/v1/warm_transfer", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "warm_transfer accepted an undeclared status: " + resp.text[:200]
    )


def test_warm_transfer_does_not_leak_across_tenants():
    """404, never 403 and never the row: existence itself is private."""
    body = {'reference': 'sample', 'status': 'open', 'call_sid': 'sample', 'lead_name': 'sample', 'outcome': 'project_interested', 'broker_number': 'sample', 'conference_name': 'sample', 'summary': 'sample', 'whisper_text': 'sample', 'transfer_status': 'initiated', 'whisper_delivered': True, 'notes': 'sample'}
    made = client.post("/v1/warm_transfer", json=body, headers=AUTH)
    if made.status_code != 200:
        pytest.skip("capability did not accept the sample record")
    try:
        record = made.json()
    except Exception:
        pytest.skip("capability did not answer JSON")
    rid = (record.get("id") or (record.get("result") or {}).get("id")
           if isinstance(record, dict) else None)
    if not rid:
        pytest.skip("capability returned no record id to read back")
    other = client.get("/v1/warm_transfer/" + str(rid), headers=OTHER_TENANT)
    assert other.status_code == 404, (
        "warm_transfer answered %s to another tenant, not 404" % other.status_code
    )


def test_warm_transfer_refuses_a_malformed_payload():
    """Garbage in is a refusal, never a 500 and never a stored row."""
    for junk in ([], "", {"": None}, {"x" * 300: "y" * 2000}):
        resp = client.post("/v1/warm_transfer", json=junk, headers=AUTH)
        assert resp.status_code != 500, (
            "warm_transfer raised on malformed input: " + resp.text[:200]
        )
        assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
            "warm_transfer accepted malformed input %r" % (junk,)
        )
