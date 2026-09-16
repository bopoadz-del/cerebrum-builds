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
    payload = {'client_name': 'sample', 'matter_number': 'sample', 'matter_title': 'sample', 'reference': 'sample', 'status': 'open', 'client_email': 'guest@example.com', 'practice_area': 'sample', 'responsible_attorney': 'sample', 'matter_stage': 'sample', 'priority': 'sample', 'opened_date': '2026-09-03', 'deadline_date': '2026-09-03', 'billing_type': 'sample', 'document_path': 'sample'}
    resp = client.post("/v1/matter_management", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('matter_management: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('matter_management: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('matter_management: JSON body is not a dict')
            listed = client.get("/v1/matter_management")
            if listed.status_code != 200:
                failures.append('matter_management list: HTTP ' + str(listed.status_code))

    payload = {'client_name': 'sample', 'reference': 'sample', 'status': 'open', 'client_email': 'guest@example.com', 'client_phone': 'sample', 'matter_type': 'sample', 'referral_source': 'sample', 'conflict_check': 'sample', 'risk_score': 'sample', 'estimated_fee': 'sample', 'retainer_amount': 'sample', 'document_path': 'sample', 'intake_date': '2026-09-03'}
    resp = client.post("/v1/client_intake", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('client_intake: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('client_intake: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('client_intake: JSON body is not a dict')
            listed = client.get("/v1/client_intake")
            if listed.status_code != 200:
                failures.append('client_intake list: HTTP ' + str(listed.status_code))

    payload = {'document_title': 'sample', 'reference': 'sample', 'status': 'open', 'document_type': 'sample', 'matter_number': 'sample', 'version': 'sample', 'file_path': 'sample', 'content_hash': 'sample', 'confidentiality': 'sample', 'document_owner': 'sample', 'tags': 'sample', 'uploaded_by': 'sample', 'uploaded_at': '2026-09-03T10:00:00'}
    resp = client.post("/v1/document_management", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('document_management: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('document_management: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('document_management: JSON body is not a dict')
            listed = client.get("/v1/document_management")
            if listed.status_code != 200:
                failures.append('document_management list: HTTP ' + str(listed.status_code))

    payload = {'matter_number': 'sample', 'reference': 'sample', 'status': 'open', 'timekeeper': 'sample', 'client_name': 'sample', 'client_email': 'guest@example.com', 'activity_date': '2026-09-03', 'hours': 'sample', 'hourly_rate': 'sample', 'billable_amount': 'sample', 'invoice_number': 'sample', 'payment_status': 'open', 'narrative': 'sample'}
    resp = client.post("/v1/time_and_billing", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('time_and_billing: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('time_and_billing: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('time_and_billing: JSON body is not a dict')
            listed = client.get("/v1/time_and_billing")
            if listed.status_code != 200:
                failures.append('time_and_billing list: HTTP ' + str(listed.status_code))

    payload = {'client_name': 'sample', 'reference': 'sample', 'status': 'open', 'client_email': 'guest@example.com', 'matter_number': 'sample', 'portal_access_level': 'sample', 'unread_messages': 'sample', 'shared_documents': 'sample', 'message_subject': 'sample', 'message_body': 'sample', 'last_login_at': '2026-09-03T10:00:00', 'document_path': 'sample'}
    resp = client.post("/v1/client_portal", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('client_portal: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('client_portal: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('client_portal: JSON body is not a dict')
            listed = client.get("/v1/client_portal")
            if listed.status_code != 200:
                failures.append('client_portal list: HTTP ' + str(listed.status_code))

    payload = {'metric_name': 'sample', 'reference': 'sample', 'status': 'open', 'metric_value': 'sample', 'benchmark_value': 'sample', 'practice_area': 'sample', 'dimension': 'sample', 'period_start': 'sample', 'period_end': 'sample', 'source_matter': 'sample'}
    resp = client.post("/v1/legal_analytics", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('legal_analytics: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('legal_analytics: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('legal_analytics: JSON body is not a dict')
            listed = client.get("/v1/legal_analytics")
            if listed.status_code != 200:
                failures.append('legal_analytics list: HTTP ' + str(listed.status_code))

    payload = {'action_taken': 'sample', 'actor': 'sample', 'control_id': 'id-1', 'reference': 'sample', 'status': 'open', 'framework': 'sample', 'regulation': 'sample', 'event_type': 'sample', 'actor_role': 'sample', 'evidence_ref': 'sample', 'findings': 'sample', 'occurred_at': '2026-09-03T10:00:00'}
    resp = client.post("/v1/compliance_audit", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('compliance_audit: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('compliance_audit: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('compliance_audit: JSON body is not a dict')
            listed = client.get("/v1/compliance_audit")
            if listed.status_code != 200:
                failures.append('compliance_audit list: HTTP ' + str(listed.status_code))

    assert not failures, "; ".join(failures)


@pytest.mark.pilot
def test_every_capability_route_accepts_payload():
    """Pilot: spec payload is accepted (ok is not False) and persisted.
    Not the factory code-phase gate."""
    failures = []
    payload = {'client_name': 'sample', 'matter_number': 'sample', 'matter_title': 'sample', 'reference': 'sample', 'status': 'open', 'client_email': 'guest@example.com', 'practice_area': 'sample', 'responsible_attorney': 'sample', 'matter_stage': 'sample', 'priority': 'sample', 'opened_date': '2026-09-03', 'deadline_date': '2026-09-03', 'billing_type': 'sample', 'document_path': 'sample'}
    resp = client.post("/v1/matter_management", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('matter_management: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('matter_management rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/matter_management")
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('matter_management list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('matter_management list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('matter_management accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/matter_management/{item_id}")
                if got.status_code != 200:
                    failures.append('matter_management get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/matter_management/999999")
                if missing.status_code != 404:
                    failures.append('matter_management missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'client_name': 'sample', 'reference': 'sample', 'status': 'open', 'client_email': 'guest@example.com', 'client_phone': 'sample', 'matter_type': 'sample', 'referral_source': 'sample', 'conflict_check': 'sample', 'risk_score': 'sample', 'estimated_fee': 'sample', 'retainer_amount': 'sample', 'document_path': 'sample', 'intake_date': '2026-09-03'}
    resp = client.post("/v1/client_intake", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('client_intake: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('client_intake rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/client_intake")
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('client_intake list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('client_intake list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('client_intake accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/client_intake/{item_id}")
                if got.status_code != 200:
                    failures.append('client_intake get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/client_intake/999999")
                if missing.status_code != 404:
                    failures.append('client_intake missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'document_title': 'sample', 'reference': 'sample', 'status': 'open', 'document_type': 'sample', 'matter_number': 'sample', 'version': 'sample', 'file_path': 'sample', 'content_hash': 'sample', 'confidentiality': 'sample', 'document_owner': 'sample', 'tags': 'sample', 'uploaded_by': 'sample', 'uploaded_at': '2026-09-03T10:00:00'}
    resp = client.post("/v1/document_management", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('document_management: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('document_management rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/document_management")
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('document_management list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('document_management list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('document_management accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/document_management/{item_id}")
                if got.status_code != 200:
                    failures.append('document_management get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/document_management/999999")
                if missing.status_code != 404:
                    failures.append('document_management missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'matter_number': 'sample', 'reference': 'sample', 'status': 'open', 'timekeeper': 'sample', 'client_name': 'sample', 'client_email': 'guest@example.com', 'activity_date': '2026-09-03', 'hours': 'sample', 'hourly_rate': 'sample', 'billable_amount': 'sample', 'invoice_number': 'sample', 'payment_status': 'open', 'narrative': 'sample'}
    resp = client.post("/v1/time_and_billing", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('time_and_billing: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('time_and_billing rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/time_and_billing")
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('time_and_billing list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('time_and_billing list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('time_and_billing accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/time_and_billing/{item_id}")
                if got.status_code != 200:
                    failures.append('time_and_billing get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/time_and_billing/999999")
                if missing.status_code != 404:
                    failures.append('time_and_billing missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'client_name': 'sample', 'reference': 'sample', 'status': 'open', 'client_email': 'guest@example.com', 'matter_number': 'sample', 'portal_access_level': 'sample', 'unread_messages': 'sample', 'shared_documents': 'sample', 'message_subject': 'sample', 'message_body': 'sample', 'last_login_at': '2026-09-03T10:00:00', 'document_path': 'sample'}
    resp = client.post("/v1/client_portal", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('client_portal: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('client_portal rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/client_portal")
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('client_portal list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('client_portal list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('client_portal accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/client_portal/{item_id}")
                if got.status_code != 200:
                    failures.append('client_portal get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/client_portal/999999")
                if missing.status_code != 404:
                    failures.append('client_portal missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'metric_name': 'sample', 'reference': 'sample', 'status': 'open', 'metric_value': 'sample', 'benchmark_value': 'sample', 'practice_area': 'sample', 'dimension': 'sample', 'period_start': 'sample', 'period_end': 'sample', 'source_matter': 'sample'}
    resp = client.post("/v1/legal_analytics", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('legal_analytics: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('legal_analytics rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/legal_analytics")
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('legal_analytics list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('legal_analytics list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('legal_analytics accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/legal_analytics/{item_id}")
                if got.status_code != 200:
                    failures.append('legal_analytics get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/legal_analytics/999999")
                if missing.status_code != 404:
                    failures.append('legal_analytics missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'action_taken': 'sample', 'actor': 'sample', 'control_id': 'id-1', 'reference': 'sample', 'status': 'open', 'framework': 'sample', 'regulation': 'sample', 'event_type': 'sample', 'actor_role': 'sample', 'evidence_ref': 'sample', 'findings': 'sample', 'occurred_at': '2026-09-03T10:00:00'}
    resp = client.post("/v1/compliance_audit", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('compliance_audit: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('compliance_audit rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/compliance_audit")
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('compliance_audit list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('compliance_audit list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('compliance_audit accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/compliance_audit/{item_id}")
                if got.status_code != 200:
                    failures.append('compliance_audit get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/compliance_audit/999999")
                if missing.status_code != 404:
                    failures.append('compliance_audit missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    assert not failures, "; ".join(failures)
