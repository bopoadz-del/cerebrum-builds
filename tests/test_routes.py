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
    payload = {'patient_name': 'sample', 'procedure': 'sample', 'reference': 'sample', 'status': 'open', 'tooth': 'sample', 'fee': 'sample', 'visit_date': '2026-09-03', 'provider': 'sample', 'clinical_notes': 'sample'}
    resp = client.post("/v1/patient_visit_records", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('patient_visit_records: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('patient_visit_records: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('patient_visit_records: JSON body is not a dict')
            listed = client.get("/v1/patient_visit_records", headers=AUTH)
            if listed.status_code != 200:
                failures.append('patient_visit_records list: HTTP ' + str(listed.status_code))

    payload = {'appointment_type': 'exam', 'patient_name': 'sample', 'reference': 'sample', 'scheduled_at': '2026-09-03T10:00:00', 'status': 'open', 'patient_email': 'guest@example.com', 'provider': 'sample', 'chair_room': 'sample', 'duration_minutes': 'sample', 'reminder_channel': 'email', 'notes': 'sample'}
    resp = client.post("/v1/appointment_scheduling", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('appointment_scheduling: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('appointment_scheduling: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('appointment_scheduling: JSON body is not a dict')
            listed = client.get("/v1/appointment_scheduling", headers=AUTH)
            if listed.status_code != 200:
                failures.append('appointment_scheduling list: HTTP ' + str(listed.status_code))

    payload = {'list_date': '2026-09-03', 'patient_name': 'sample', 'reference': 'sample', 'status': 'open', 'provider': 'sample', 'procedure': 'sample', 'appointment_time': '10:00:00', 'appointment_status': 'scheduled', 'chair_room': 'sample'}
    resp = client.post("/v1/todays_appointment_list", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('todays_appointment_list: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('todays_appointment_list: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('todays_appointment_list: JSON body is not a dict')
            listed = client.get("/v1/todays_appointment_list", headers=AUTH)
            if listed.status_code != 200:
                failures.append('todays_appointment_list list: HTTP ' + str(listed.status_code))

    payload = {'patient_email': 'guest@example.com', 'patient_name': 'sample', 'reference': 'sample', 'reminder_date': '2026-09-03', 'status': 'open', 'appointment_at': '2026-09-03T10:00:00', 'reminder_channel': 'email', 'message_body': 'sample', 'delivery_state': 'queued'}
    resp = client.post("/v1/day_before_email_reminders", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('day_before_email_reminders: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('day_before_email_reminders: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('day_before_email_reminders: JSON body is not a dict')
            listed = client.get("/v1/day_before_email_reminders", headers=AUTH)
            if listed.status_code != 200:
                failures.append('day_before_email_reminders list: HTTP ' + str(listed.status_code))

    payload = {'patient_name': 'sample', 'reference': 'sample', 'status': 'open', 'patient_email': 'guest@example.com', 'patient_phone': 'sample', 'date_of_birth': 'sample', 'primary_provider': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/patient_directory", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('patient_directory: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('patient_directory: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('patient_directory: JSON body is not a dict')
            listed = client.get("/v1/patient_directory", headers=AUTH)
            if listed.status_code != 200:
                failures.append('patient_directory list: HTTP ' + str(listed.status_code))

    payload = {'patient_name': 'sample', 'reference': 'sample', 'status': 'open', 'tooth': 'sample', 'procedure': 'sample', 'provider': 'sample', 'visit_date': '2026-09-03', 'date_from': 'sample', 'date_to': 'sample', 'search_notes': 'sample'}
    resp = client.post("/v1/clinical_history_search", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('clinical_history_search: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('clinical_history_search: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('clinical_history_search: JSON body is not a dict')
            listed = client.get("/v1/clinical_history_search", headers=AUTH)
            if listed.status_code != 200:
                failures.append('clinical_history_search list: HTTP ' + str(listed.status_code))

    payload = {'reference': 'sample', 'staff_name': 'sample', 'staff_role': 'dentist', 'status': 'open', 'staff_email': 'guest@example.com', 'permission_scope': 'sample', 'active_from': 'sample'}
    resp = client.post("/v1/role_based_access", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('role_based_access: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('role_based_access: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('role_based_access: JSON body is not a dict')
            listed = client.get("/v1/role_based_access", headers=AUTH)
            if listed.status_code != 200:
                failures.append('role_based_access list: HTTP ' + str(listed.status_code))

    assert not failures, "; ".join(failures)


@pytest.mark.pilot
def test_every_capability_route_accepts_payload():
    """Pilot: spec payload is accepted (ok is not False) and persisted.
    Not the factory code-phase gate."""
    failures = []
    payload = {'patient_name': 'sample', 'procedure': 'sample', 'reference': 'sample', 'status': 'open', 'tooth': 'sample', 'fee': 'sample', 'visit_date': '2026-09-03', 'provider': 'sample', 'clinical_notes': 'sample'}
    resp = client.post("/v1/patient_visit_records", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('patient_visit_records: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('patient_visit_records rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/patient_visit_records", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('patient_visit_records list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('patient_visit_records list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('patient_visit_records accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/patient_visit_records/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('patient_visit_records get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/patient_visit_records/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('patient_visit_records missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'appointment_type': 'exam', 'patient_name': 'sample', 'reference': 'sample', 'scheduled_at': '2026-09-03T10:00:00', 'status': 'open', 'patient_email': 'guest@example.com', 'provider': 'sample', 'chair_room': 'sample', 'duration_minutes': 'sample', 'reminder_channel': 'email', 'notes': 'sample'}
    resp = client.post("/v1/appointment_scheduling", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('appointment_scheduling: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('appointment_scheduling rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/appointment_scheduling", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('appointment_scheduling list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('appointment_scheduling list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('appointment_scheduling accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/appointment_scheduling/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('appointment_scheduling get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/appointment_scheduling/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('appointment_scheduling missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'list_date': '2026-09-03', 'patient_name': 'sample', 'reference': 'sample', 'status': 'open', 'provider': 'sample', 'procedure': 'sample', 'appointment_time': '10:00:00', 'appointment_status': 'scheduled', 'chair_room': 'sample'}
    resp = client.post("/v1/todays_appointment_list", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('todays_appointment_list: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('todays_appointment_list rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/todays_appointment_list", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('todays_appointment_list list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('todays_appointment_list list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('todays_appointment_list accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/todays_appointment_list/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('todays_appointment_list get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/todays_appointment_list/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('todays_appointment_list missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'patient_email': 'guest@example.com', 'patient_name': 'sample', 'reference': 'sample', 'reminder_date': '2026-09-03', 'status': 'open', 'appointment_at': '2026-09-03T10:00:00', 'reminder_channel': 'email', 'message_body': 'sample', 'delivery_state': 'queued'}
    resp = client.post("/v1/day_before_email_reminders", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('day_before_email_reminders: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('day_before_email_reminders rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/day_before_email_reminders", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('day_before_email_reminders list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('day_before_email_reminders list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('day_before_email_reminders accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/day_before_email_reminders/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('day_before_email_reminders get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/day_before_email_reminders/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('day_before_email_reminders missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'patient_name': 'sample', 'reference': 'sample', 'status': 'open', 'patient_email': 'guest@example.com', 'patient_phone': 'sample', 'date_of_birth': 'sample', 'primary_provider': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/patient_directory", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('patient_directory: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('patient_directory rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/patient_directory", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('patient_directory list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('patient_directory list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('patient_directory accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/patient_directory/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('patient_directory get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/patient_directory/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('patient_directory missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'patient_name': 'sample', 'reference': 'sample', 'status': 'open', 'tooth': 'sample', 'procedure': 'sample', 'provider': 'sample', 'visit_date': '2026-09-03', 'date_from': 'sample', 'date_to': 'sample', 'search_notes': 'sample'}
    resp = client.post("/v1/clinical_history_search", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('clinical_history_search: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('clinical_history_search rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/clinical_history_search", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('clinical_history_search list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('clinical_history_search list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('clinical_history_search accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/clinical_history_search/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('clinical_history_search get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/clinical_history_search/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('clinical_history_search missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'reference': 'sample', 'staff_name': 'sample', 'staff_role': 'dentist', 'status': 'open', 'staff_email': 'guest@example.com', 'permission_scope': 'sample', 'active_from': 'sample'}
    resp = client.post("/v1/role_based_access", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('role_based_access: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('role_based_access rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/role_based_access", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('role_based_access list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('role_based_access list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('role_based_access accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/role_based_access/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('role_based_access get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/role_based_access/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('role_based_access missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    assert not failures, "; ".join(failures)
