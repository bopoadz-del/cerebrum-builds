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
    payload = {'guest_name': 'sample', 'reference': 'sample', 'room_number': 'sample', 'status': 'open', 'checked_in_at': '2026-09-03T10:00:00', 'guests_count': 1, 'notes': 'sample'}
    resp = client.post("/v1/record_guest_check_in", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('record_guest_check_in: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('record_guest_check_in: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('record_guest_check_in: JSON body is not a dict')
            listed = client.get("/v1/record_guest_check_in", headers=AUTH)
            if listed.status_code != 200:
                failures.append('record_guest_check_in list: HTTP ' + str(listed.status_code))

    payload = {'check_in_date': '2026-09-03', 'guest_name': 'sample', 'reference': 'sample', 'room_number': 'sample', 'status': 'open', 'check_in_count': 1, 'notes': 'sample'}
    resp = client.post("/v1/list_todays_check_ins", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('list_todays_check_ins: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('list_todays_check_ins: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('list_todays_check_ins: JSON body is not a dict')
            listed = client.get("/v1/list_todays_check_ins", headers=AUTH)
            if listed.status_code != 200:
                failures.append('list_todays_check_ins list: HTTP ' + str(listed.status_code))

    assert not failures, "; ".join(failures)


@pytest.mark.pilot
def test_every_capability_route_accepts_payload():
    """Pilot: spec payload is accepted (ok is not False) and persisted.
    Not the factory code-phase gate."""
    failures = []
    payload = {'guest_name': 'sample', 'reference': 'sample', 'room_number': 'sample', 'status': 'open', 'checked_in_at': '2026-09-03T10:00:00', 'guests_count': 1, 'notes': 'sample'}
    resp = client.post("/v1/record_guest_check_in", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('record_guest_check_in: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('record_guest_check_in rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/record_guest_check_in", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('record_guest_check_in list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('record_guest_check_in list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('record_guest_check_in accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/record_guest_check_in/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('record_guest_check_in get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/record_guest_check_in/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('record_guest_check_in missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'check_in_date': '2026-09-03', 'guest_name': 'sample', 'reference': 'sample', 'room_number': 'sample', 'status': 'open', 'check_in_count': 1, 'notes': 'sample'}
    resp = client.post("/v1/list_todays_check_ins", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('list_todays_check_ins: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('list_todays_check_ins rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/list_todays_check_ins", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('list_todays_check_ins list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('list_todays_check_ins list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('list_todays_check_ins accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/list_todays_check_ins/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('list_todays_check_ins get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/list_todays_check_ins/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('list_todays_check_ins missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    assert not failures, "; ".join(failures)
