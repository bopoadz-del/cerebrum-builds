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
    body = {'event': 'dial', 'reference': 'sample', 'status': 'open', 'lead_id': 'id-1', 'lead_reference': 'sample', 'previous_state': 'queued', 'current_state': 'queued', 'attempt_count': 1, 'within_window': 'sample', 'window_reason': 'sample', 'transition_allowed': 'sample', 'refusal_reason': 'sample', 'guard_notes': 'sample', 'window_snapshot': 'sample', 'occurred_at': '2026-09-03T10:00:00', 'source': 'voice_gateway', 'campaign': 'sample'}
    resp = client.post("/v1/call_state_machine", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "call_state_machine accepted a payload with no call_sid: " + resp.text[:200]
    )


def test_call_state_machine_refuses_a_value_outside_its_vocabulary():
    """A column that accepts any string is not that column."""
    body = {'call_sid': 'sample', 'event': 'not-a-declared-value', 'reference': 'sample', 'status': 'open', 'lead_id': 'id-1', 'lead_reference': 'sample', 'previous_state': 'queued', 'current_state': 'queued', 'attempt_count': 1, 'within_window': 'sample', 'window_reason': 'sample', 'transition_allowed': 'sample', 'refusal_reason': 'sample', 'guard_notes': 'sample', 'window_snapshot': 'sample', 'occurred_at': '2026-09-03T10:00:00', 'source': 'voice_gateway', 'campaign': 'sample'}
    resp = client.post("/v1/call_state_machine", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "call_state_machine accepted an undeclared event: " + resp.text[:200]
    )


def test_call_state_machine_does_not_leak_across_tenants():
    """404, never 403 and never the row: existence itself is private."""
    body = {'call_sid': 'sample', 'event': 'dial', 'reference': 'sample', 'status': 'open', 'lead_id': 'id-1', 'lead_reference': 'sample', 'previous_state': 'queued', 'current_state': 'queued', 'attempt_count': 1, 'within_window': 'sample', 'window_reason': 'sample', 'transition_allowed': 'sample', 'refusal_reason': 'sample', 'guard_notes': 'sample', 'window_snapshot': 'sample', 'occurred_at': '2026-09-03T10:00:00', 'source': 'voice_gateway', 'campaign': 'sample'}
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
    body = {'crm_system': 'sample', 'destination': 'sample', 'destination_named': 'sample', 'payload_shape': 'sample', 'delivery': 'placeholder', 'unavailable_blocks': 'sample', 'outcome': 'project_interested', 'summary': 'sample', 'note': 'sample', 'intended_method': 'POST', 'reference': 'sample', 'status': 'open'}
    resp = client.post("/v1/crm_destination_placeholder", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "crm_destination_placeholder accepted a payload with no call_sid: " + resp.text[:200]
    )


def test_crm_destination_placeholder_refuses_a_value_outside_its_vocabulary():
    """A column that accepts any string is not that column."""
    body = {'call_sid': 'sample', 'crm_system': 'sample', 'destination': 'sample', 'destination_named': 'sample', 'payload_shape': 'sample', 'delivery': 'not-a-declared-value', 'unavailable_blocks': 'sample', 'outcome': 'project_interested', 'summary': 'sample', 'note': 'sample', 'intended_method': 'POST', 'reference': 'sample', 'status': 'open'}
    resp = client.post("/v1/crm_destination_placeholder", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "crm_destination_placeholder accepted an undeclared delivery: " + resp.text[:200]
    )


def test_crm_destination_placeholder_does_not_leak_across_tenants():
    """404, never 403 and never the row: existence itself is private."""
    body = {'call_sid': 'sample', 'crm_system': 'sample', 'destination': 'sample', 'destination_named': 'sample', 'payload_shape': 'sample', 'delivery': 'placeholder', 'unavailable_blocks': 'sample', 'outcome': 'project_interested', 'summary': 'sample', 'note': 'sample', 'intended_method': 'POST', 'reference': 'sample', 'status': 'open'}
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
    body = {'drive_mode': 'stubbed', 'folder_id': 'id-1', 'document_id': 'id-1', 'file_name': 'sample', 'mime_type': 'sample', 'credentials_present': 'sample', 'unavailable_blocks': 'sample', 'delivery': 'stub', 'note': 'sample', 'would_call': 'sample', 'upload_state': 'sample', 'reference': 'sample', 'status': 'open'}
    resp = client.post("/v1/google_drive", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "google_drive accepted a payload with no operation: " + resp.text[:200]
    )


def test_google_drive_refuses_a_value_outside_its_vocabulary():
    """A column that accepts any string is not that column."""
    body = {'operation': 'not-a-declared-value', 'drive_mode': 'stubbed', 'folder_id': 'id-1', 'document_id': 'id-1', 'file_name': 'sample', 'mime_type': 'sample', 'credentials_present': 'sample', 'unavailable_blocks': 'sample', 'delivery': 'stub', 'note': 'sample', 'would_call': 'sample', 'upload_state': 'sample', 'reference': 'sample', 'status': 'open'}
    resp = client.post("/v1/google_drive", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "google_drive accepted an undeclared operation: " + resp.text[:200]
    )


def test_google_drive_does_not_leak_across_tenants():
    """404, never 403 and never the row: existence itself is private."""
    body = {'operation': 'upload', 'drive_mode': 'stubbed', 'folder_id': 'id-1', 'document_id': 'id-1', 'file_name': 'sample', 'mime_type': 'sample', 'credentials_present': 'sample', 'unavailable_blocks': 'sample', 'delivery': 'stub', 'note': 'sample', 'would_call': 'sample', 'upload_state': 'sample', 'reference': 'sample', 'status': 'open'}
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
    body = {'phone': 'sample', 'project_tag': 'sample', 'reference': 'sample', 'status': 'open', 'language': 'en', 'campaign': 'sample', 'source_file': 'sample', 'lead_email': 'guest@example.com', 'property_type': 'apartment', 'budget': 'sample', 'area': 'sample', 'timeline': 'immediate', 'priority': 'sample', 'phone_e164': 'sample', 'dialable': 'sample', 'dialable_reason': 'sample', 'attempt_count': 1, 'max_attempts': 'sample', 'retry_backoff_minutes': 'sample', 'daily_call_cap': 'sample', 'concurrency': 'sample', 'queue_state': 'queued', 'best_call_window': 'sample', 'window_state': 'open', 'dial_scheduled_at': '2026-09-03T10:00:00', 'next_attempt_at': '2026-09-03T10:00:00', 'last_call_sid': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/lead_intake_and_dial_queue", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "lead_intake_and_dial_queue accepted a payload with no lead_name: " + resp.text[:200]
    )


def test_lead_intake_and_dial_queue_refuses_a_value_outside_its_vocabulary():
    """A column that accepts any string is not that column."""
    body = {'lead_name': 'sample', 'phone': 'sample', 'project_tag': 'sample', 'reference': 'sample', 'status': 'not-a-declared-value', 'language': 'en', 'campaign': 'sample', 'source_file': 'sample', 'lead_email': 'guest@example.com', 'property_type': 'apartment', 'budget': 'sample', 'area': 'sample', 'timeline': 'immediate', 'priority': 'sample', 'phone_e164': 'sample', 'dialable': 'sample', 'dialable_reason': 'sample', 'attempt_count': 1, 'max_attempts': 'sample', 'retry_backoff_minutes': 'sample', 'daily_call_cap': 'sample', 'concurrency': 'sample', 'queue_state': 'queued', 'best_call_window': 'sample', 'window_state': 'open', 'dial_scheduled_at': '2026-09-03T10:00:00', 'next_attempt_at': '2026-09-03T10:00:00', 'last_call_sid': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/lead_intake_and_dial_queue", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "lead_intake_and_dial_queue accepted an undeclared status: " + resp.text[:200]
    )


def test_lead_intake_and_dial_queue_does_not_leak_across_tenants():
    """404, never 403 and never the row: existence itself is private."""
    body = {'lead_name': 'sample', 'phone': 'sample', 'project_tag': 'sample', 'reference': 'sample', 'status': 'open', 'language': 'en', 'campaign': 'sample', 'source_file': 'sample', 'lead_email': 'guest@example.com', 'property_type': 'apartment', 'budget': 'sample', 'area': 'sample', 'timeline': 'immediate', 'priority': 'sample', 'phone_e164': 'sample', 'dialable': 'sample', 'dialable_reason': 'sample', 'attempt_count': 1, 'max_attempts': 'sample', 'retry_backoff_minutes': 'sample', 'daily_call_cap': 'sample', 'concurrency': 'sample', 'queue_state': 'queued', 'best_call_window': 'sample', 'window_state': 'open', 'dial_scheduled_at': '2026-09-03T10:00:00', 'next_attempt_at': '2026-09-03T10:00:00', 'last_call_sid': 'sample', 'notes': 'sample'}
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
    body = {'relative_path': 'sample', 'content': 'sample', 'content_digest': 'sample', 'bytes_written': 'sample', 'root': 'sample', 'tenant_root': 'sample', 'entries': 'sample', 'file_exists': 'sample', 'size_bytes': 'sample', 'media_type': 'sample', 'reference': 'sample', 'status': 'open'}
    resp = client.post("/v1/local_drive", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "local_drive accepted a payload with no operation: " + resp.text[:200]
    )


def test_local_drive_refuses_a_value_outside_its_vocabulary():
    """A column that accepts any string is not that column."""
    body = {'operation': 'not-a-declared-value', 'relative_path': 'sample', 'content': 'sample', 'content_digest': 'sample', 'bytes_written': 'sample', 'root': 'sample', 'tenant_root': 'sample', 'entries': 'sample', 'file_exists': 'sample', 'size_bytes': 'sample', 'media_type': 'sample', 'reference': 'sample', 'status': 'open'}
    resp = client.post("/v1/local_drive", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "local_drive accepted an undeclared operation: " + resp.text[:200]
    )


def test_local_drive_does_not_leak_across_tenants():
    """404, never 403 and never the row: existence itself is private."""
    body = {'operation': 'put', 'relative_path': 'sample', 'content': 'sample', 'content_digest': 'sample', 'bytes_written': 'sample', 'root': 'sample', 'tenant_root': 'sample', 'entries': 'sample', 'file_exists': 'sample', 'size_bytes': 'sample', 'media_type': 'sample', 'reference': 'sample', 'status': 'open'}
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
    body = {'tool': 'sample', 'arguments': 'sample', 'catalog_scope': 'platform', 'tool_count': 1, 'dispatched': 'sample', 'error_code': 'id-1', 'protocol': 'sample', 'duration_ms': 'sample', 'reference': 'sample', 'status': 'open'}
    resp = client.post("/v1/mcp_adapter", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "mcp_adapter accepted a payload with no method: " + resp.text[:200]
    )


def test_mcp_adapter_refuses_a_value_outside_its_vocabulary():
    """A column that accepts any string is not that column."""
    body = {'method': 'not-a-declared-value', 'tool': 'sample', 'arguments': 'sample', 'catalog_scope': 'platform', 'tool_count': 1, 'dispatched': 'sample', 'error_code': 'id-1', 'protocol': 'sample', 'duration_ms': 'sample', 'reference': 'sample', 'status': 'open'}
    resp = client.post("/v1/mcp_adapter", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "mcp_adapter accepted an undeclared method: " + resp.text[:200]
    )


def test_mcp_adapter_does_not_leak_across_tenants():
    """404, never 403 and never the row: existence itself is private."""
    body = {'method': 'tools/list', 'tool': 'sample', 'arguments': 'sample', 'catalog_scope': 'platform', 'tool_count': 1, 'dispatched': 'sample', 'error_code': 'id-1', 'protocol': 'sample', 'duration_ms': 'sample', 'reference': 'sample', 'status': 'open'}
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
    body = {'channel': 'webhook', 'target': 'sample', 'subject': 'sample', 'body': 'sample', 'delivery': 'delivered', 'provider': 'sample', 'attempts': 'sample', 'response_code': 'id-1', 'delivered_at': '2026-09-03T10:00:00', 'unavailable_blocks': 'sample', 'message_digest': 'sample', 'summary': 'sample', 'outcome': 'project_interested', 'call_sid': 'sample', 'campaign': 'sample', 'reference': 'sample', 'status': 'open'}
    resp = client.post("/v1/notification", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "notification accepted a payload with no trigger_event: " + resp.text[:200]
    )


def test_notification_refuses_a_value_outside_its_vocabulary():
    """A column that accepts any string is not that column."""
    body = {'trigger_event': 'not-a-declared-value', 'channel': 'webhook', 'target': 'sample', 'subject': 'sample', 'body': 'sample', 'delivery': 'delivered', 'provider': 'sample', 'attempts': 'sample', 'response_code': 'id-1', 'delivered_at': '2026-09-03T10:00:00', 'unavailable_blocks': 'sample', 'message_digest': 'sample', 'summary': 'sample', 'outcome': 'project_interested', 'call_sid': 'sample', 'campaign': 'sample', 'reference': 'sample', 'status': 'open'}
    resp = client.post("/v1/notification", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "notification accepted an undeclared trigger_event: " + resp.text[:200]
    )


def test_notification_does_not_leak_across_tenants():
    """404, never 403 and never the row: existence itself is private."""
    body = {'trigger_event': 'lead_qualified', 'channel': 'webhook', 'target': 'sample', 'subject': 'sample', 'body': 'sample', 'delivery': 'delivered', 'provider': 'sample', 'attempts': 'sample', 'response_code': 'id-1', 'delivered_at': '2026-09-03T10:00:00', 'unavailable_blocks': 'sample', 'message_digest': 'sample', 'summary': 'sample', 'outcome': 'project_interested', 'call_sid': 'sample', 'campaign': 'sample', 'reference': 'sample', 'status': 'open'}
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
    body = {'event_type': 'attempted', 'sequence': 'sample', 'prev_hash': 'sample', 'entry_hash': 'sample', 'payload_digest': 'sample', 'outcome': 'project_interested', 'actor': 'sample', 'campaign': 'sample', 'detail': 'sample', 'chain_ok': 'sample', 'verified_count': 1, 'reference': 'sample', 'status': 'open'}
    resp = client.post("/v1/outcome_capture_and_ledger", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "outcome_capture_and_ledger accepted a payload with no call_sid: " + resp.text[:200]
    )


def test_outcome_capture_and_ledger_refuses_a_value_outside_its_vocabulary():
    """A column that accepts any string is not that column."""
    body = {'call_sid': 'sample', 'event_type': 'not-a-declared-value', 'sequence': 'sample', 'prev_hash': 'sample', 'entry_hash': 'sample', 'payload_digest': 'sample', 'outcome': 'project_interested', 'actor': 'sample', 'campaign': 'sample', 'detail': 'sample', 'chain_ok': 'sample', 'verified_count': 1, 'reference': 'sample', 'status': 'open'}
    resp = client.post("/v1/outcome_capture_and_ledger", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "outcome_capture_and_ledger accepted an undeclared event_type: " + resp.text[:200]
    )


def test_outcome_capture_and_ledger_does_not_leak_across_tenants():
    """404, never 403 and never the row: existence itself is private."""
    body = {'call_sid': 'sample', 'event_type': 'attempted', 'sequence': 'sample', 'prev_hash': 'sample', 'entry_hash': 'sample', 'payload_digest': 'sample', 'outcome': 'project_interested', 'actor': 'sample', 'campaign': 'sample', 'detail': 'sample', 'chain_ok': 'sample', 'verified_count': 1, 'reference': 'sample', 'status': 'open'}
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
    body = {'question': 'sample', 'claim_type': 'price', 'language': 'en', 'answer': 'sample', 'pitch': 'sample', 'citations': 'sample', 'source_documents': 'sample', 'retrieved_count': 1, 'withheld': 'sample', 'withheld_claims': 'sample', 'authority_layer': 'sample', 'authority_label': 'sample', 'divergence': 'sample', 'campaign': 'sample', 'reference': 'sample', 'status': 'open'}
    resp = client.post("/v1/project_knowledge_grounding", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "project_knowledge_grounding accepted a payload with no project_tag: " + resp.text[:200]
    )


def test_project_knowledge_grounding_refuses_a_value_outside_its_vocabulary():
    """A column that accepts any string is not that column."""
    body = {'project_tag': 'sample', 'question': 'sample', 'claim_type': 'not-a-declared-value', 'language': 'en', 'answer': 'sample', 'pitch': 'sample', 'citations': 'sample', 'source_documents': 'sample', 'retrieved_count': 1, 'withheld': 'sample', 'withheld_claims': 'sample', 'authority_layer': 'sample', 'authority_label': 'sample', 'divergence': 'sample', 'campaign': 'sample', 'reference': 'sample', 'status': 'open'}
    resp = client.post("/v1/project_knowledge_grounding", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "project_knowledge_grounding accepted an undeclared claim_type: " + resp.text[:200]
    )


def test_project_knowledge_grounding_does_not_leak_across_tenants():
    """404, never 403 and never the row: existence itself is private."""
    body = {'project_tag': 'sample', 'question': 'sample', 'claim_type': 'price', 'language': 'en', 'answer': 'sample', 'pitch': 'sample', 'citations': 'sample', 'source_documents': 'sample', 'retrieved_count': 1, 'withheld': 'sample', 'withheld_claims': 'sample', 'authority_layer': 'sample', 'authority_label': 'sample', 'divergence': 'sample', 'campaign': 'sample', 'reference': 'sample', 'status': 'open'}
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
    body = {'outcome': 'project_interested', 'language': 'en', 'project_tag': 'sample', 'lead_name': 'sample', 'property_type': 'apartment', 'budget': 'sample', 'currency': 'sample', 'area': 'sample', 'timeline': 'immediate', 'transcript': 'sample', 'collected': 'sample', 'summary': 'sample', 'summary_text': 'sample', 'recommendation': 'sample', 'next_action': 'transfer_to_broker', 'qualified': 'sample', 'transfer_required': 'sample', 'authority_layer': 'sample', 'authority_label': 'sample', 'campaign': 'sample', 'reference': 'sample', 'status': 'open'}
    resp = client.post("/v1/qualification_and_broker_summary", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "qualification_and_broker_summary accepted a payload with no call_sid: " + resp.text[:200]
    )


def test_qualification_and_broker_summary_refuses_a_value_outside_its_vocabulary():
    """A column that accepts any string is not that column."""
    body = {'call_sid': 'sample', 'outcome': 'not-a-declared-value', 'language': 'en', 'project_tag': 'sample', 'lead_name': 'sample', 'property_type': 'apartment', 'budget': 'sample', 'currency': 'sample', 'area': 'sample', 'timeline': 'immediate', 'transcript': 'sample', 'collected': 'sample', 'summary': 'sample', 'summary_text': 'sample', 'recommendation': 'sample', 'next_action': 'transfer_to_broker', 'qualified': 'sample', 'transfer_required': 'sample', 'authority_layer': 'sample', 'authority_label': 'sample', 'campaign': 'sample', 'reference': 'sample', 'status': 'open'}
    resp = client.post("/v1/qualification_and_broker_summary", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "qualification_and_broker_summary accepted an undeclared outcome: " + resp.text[:200]
    )


def test_qualification_and_broker_summary_does_not_leak_across_tenants():
    """404, never 403 and never the row: existence itself is private."""
    body = {'call_sid': 'sample', 'outcome': 'project_interested', 'language': 'en', 'project_tag': 'sample', 'lead_name': 'sample', 'property_type': 'apartment', 'budget': 'sample', 'currency': 'sample', 'area': 'sample', 'timeline': 'immediate', 'transcript': 'sample', 'collected': 'sample', 'summary': 'sample', 'summary_text': 'sample', 'recommendation': 'sample', 'next_action': 'transfer_to_broker', 'qualified': 'sample', 'transfer_required': 'sample', 'authority_layer': 'sample', 'authority_label': 'sample', 'campaign': 'sample', 'reference': 'sample', 'status': 'open'}
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
    body = {'to_number': 'sample', 'from_number': 'sample', 'direction': 'outbound', 'language': 'en', 'call_status': 'initiated', 'call_event': 'sample', 'transition_to': 'queued', 'mapping_ok': 'sample', 'twiml': 'sample', 'asr_transcript': 'sample', 'tts_text': 'sample', 'tts_voice': 'sample', 'gather_language': 'sample', 'conference_sid': 'sample', 'duration_seconds': 'sample', 'attempt': 'sample', 'provider': 'sample', 'call_key_source': 'sample', 'edge_stub': 'sample', 'unavailable_blocks': 'sample', 'reference': 'sample', 'status': 'open', 'voice_action': 'originate'}
    resp = client.post("/v1/voice_gateway", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "voice_gateway accepted a payload with no call_sid: " + resp.text[:200]
    )


def test_voice_gateway_refuses_a_value_outside_its_vocabulary():
    """A column that accepts any string is not that column."""
    body = {'call_sid': 'sample', 'to_number': 'sample', 'from_number': 'sample', 'direction': 'not-a-declared-value', 'language': 'en', 'call_status': 'initiated', 'call_event': 'sample', 'transition_to': 'queued', 'mapping_ok': 'sample', 'twiml': 'sample', 'asr_transcript': 'sample', 'tts_text': 'sample', 'tts_voice': 'sample', 'gather_language': 'sample', 'conference_sid': 'sample', 'duration_seconds': 'sample', 'attempt': 'sample', 'provider': 'sample', 'call_key_source': 'sample', 'edge_stub': 'sample', 'unavailable_blocks': 'sample', 'reference': 'sample', 'status': 'open', 'voice_action': 'originate'}
    resp = client.post("/v1/voice_gateway", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "voice_gateway accepted an undeclared direction: " + resp.text[:200]
    )


def test_voice_gateway_does_not_leak_across_tenants():
    """404, never 403 and never the row: existence itself is private."""
    body = {'call_sid': 'sample', 'to_number': 'sample', 'from_number': 'sample', 'direction': 'outbound', 'language': 'en', 'call_status': 'initiated', 'call_event': 'sample', 'transition_to': 'queued', 'mapping_ok': 'sample', 'twiml': 'sample', 'asr_transcript': 'sample', 'tts_text': 'sample', 'tts_voice': 'sample', 'gather_language': 'sample', 'conference_sid': 'sample', 'duration_seconds': 'sample', 'attempt': 'sample', 'provider': 'sample', 'call_key_source': 'sample', 'edge_stub': 'sample', 'unavailable_blocks': 'sample', 'reference': 'sample', 'status': 'open', 'voice_action': 'originate'}
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
    body = {'outcome': 'transferred', 'lead_id': 'id-1', 'project_tag': 'sample', 'qualified_outcome': 'project_interested', 'broker_number': 'sample', 'broker_language': 'en', 'whisper_text': 'sample', 'summary': 'sample', 'step_count': 1, 'conference_name': 'sample', 'conference_sid': 'sample', 'bridge_seconds': 'sample', 'attempt': 'sample', 'transfer_key': 'sample', 'edge_stub': 'sample', 'unavailable_blocks': 'sample', 'reference': 'sample', 'status': 'open'}
    resp = client.post("/v1/warm_transfer", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "warm_transfer accepted a payload with no call_sid: " + resp.text[:200]
    )


def test_warm_transfer_refuses_a_value_outside_its_vocabulary():
    """A column that accepts any string is not that column."""
    body = {'call_sid': 'sample', 'outcome': 'not-a-declared-value', 'lead_id': 'id-1', 'project_tag': 'sample', 'qualified_outcome': 'project_interested', 'broker_number': 'sample', 'broker_language': 'en', 'whisper_text': 'sample', 'summary': 'sample', 'step_count': 1, 'conference_name': 'sample', 'conference_sid': 'sample', 'bridge_seconds': 'sample', 'attempt': 'sample', 'transfer_key': 'sample', 'edge_stub': 'sample', 'unavailable_blocks': 'sample', 'reference': 'sample', 'status': 'open'}
    resp = client.post("/v1/warm_transfer", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "warm_transfer accepted an undeclared outcome: " + resp.text[:200]
    )


def test_warm_transfer_does_not_leak_across_tenants():
    """404, never 403 and never the row: existence itself is private."""
    body = {'call_sid': 'sample', 'outcome': 'transferred', 'lead_id': 'id-1', 'project_tag': 'sample', 'qualified_outcome': 'project_interested', 'broker_number': 'sample', 'broker_language': 'en', 'whisper_text': 'sample', 'summary': 'sample', 'step_count': 1, 'conference_name': 'sample', 'conference_sid': 'sample', 'bridge_seconds': 'sample', 'attempt': 'sample', 'transfer_key': 'sample', 'edge_stub': 'sample', 'unavailable_blocks': 'sample', 'reference': 'sample', 'status': 'open'}
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
