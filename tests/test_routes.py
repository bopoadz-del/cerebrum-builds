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
    payload = {'arrival_time': '10:00:00', 'guest_name': 'sample', 'nights': 1, 'reference': 'sample', 'room_number': 'sample', 'status': 'open', 'notes': 'sample'}
    resp = client.post("/v1/record_checkin", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('record_checkin: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('record_checkin: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('record_checkin: JSON body is not a dict')
            listed = client.get("/v1/record_checkin", headers=AUTH)
            if listed.status_code != 200:
                failures.append('record_checkin list: HTTP ' + str(listed.status_code))

    payload = {'arrival_date': '2026-09-03', 'guest_name': 'sample', 'reference': 'sample', 'room_number': 'sample', 'status': 'open', 'arrived': 'sample', 'arrivals_count': 1}
    resp = client.post("/v1/todays_arrivals_board", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('todays_arrivals_board: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('todays_arrivals_board: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('todays_arrivals_board: JSON body is not a dict')
            listed = client.get("/v1/todays_arrivals_board", headers=AUTH)
            if listed.status_code != 200:
                failures.append('todays_arrivals_board list: HTTP ' + str(listed.status_code))

    payload = {'check_in_date': '2026-09-03', 'check_out_date': '2026-09-03', 'reference': 'sample', 'room_number': 'sample', 'status': 'open', 'is_available': True}
    resp = client.post("/v1/room_availability_check", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('room_availability_check: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('room_availability_check: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('room_availability_check: JSON body is not a dict')
            listed = client.get("/v1/room_availability_check", headers=AUTH)
            if listed.status_code != 200:
                failures.append('room_availability_check list: HTTP ' + str(listed.status_code))

    payload = {'guest_name': 'sample', 'reference': 'sample', 'status': 'open', 'room_number': 'sample', 'preference': 'sample', 'note': 'sample'}
    resp = client.post("/v1/guest_notes_and_preferences", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('guest_notes_and_preferences: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('guest_notes_and_preferences: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('guest_notes_and_preferences: JSON body is not a dict')
            listed = client.get("/v1/guest_notes_and_preferences", headers=AUTH)
            if listed.status_code != 200:
                failures.append('guest_notes_and_preferences list: HTTP ' + str(listed.status_code))

    payload = {'guest_name': 'sample', 'reference': 'sample', 'room_number': 'sample', 'status': 'open', 'channel': 'mcp', 'recipient': 'sample'}
    resp = client.post("/v1/checkin_notifications", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('checkin_notifications: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('checkin_notifications: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('checkin_notifications: JSON body is not a dict')
            listed = client.get("/v1/checkin_notifications", headers=AUTH)
            if listed.status_code != 200:
                failures.append('checkin_notifications list: HTTP ' + str(listed.status_code))

    payload = {'reference': 'sample', 'status': 'open', 'summary_date': '2026-09-03', 'arrivals_count': 1, 'occupancy_percent': 'sample', 'no_show_count': 1}
    resp = client.post("/v1/daily_checkin_summary", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('daily_checkin_summary: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('daily_checkin_summary: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('daily_checkin_summary: JSON body is not a dict')
            listed = client.get("/v1/daily_checkin_summary", headers=AUTH)
            if listed.status_code != 200:
                failures.append('daily_checkin_summary list: HTTP ' + str(listed.status_code))

    payload = {'actor': 'sample', 'reference': 'sample', 'status': 'open', 'change_type': 'create', 'subject_capability': 'sample', 'changed_at': '2026-09-03T10:00:00'}
    resp = client.post("/v1/audit_trail", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('audit_trail: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('audit_trail: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('audit_trail: JSON body is not a dict')
            listed = client.get("/v1/audit_trail", headers=AUTH)
            if listed.status_code != 200:
                failures.append('audit_trail list: HTTP ' + str(listed.status_code))

    assert not failures, "; ".join(failures)


@pytest.mark.pilot
def test_every_capability_route_accepts_payload():
    """Pilot: spec payload is accepted (ok is not False) and persisted.
    Not the factory code-phase gate."""
    failures = []
    payload = {'arrival_time': '10:00:00', 'guest_name': 'sample', 'nights': 1, 'reference': 'sample', 'room_number': 'sample', 'status': 'open', 'notes': 'sample'}
    resp = client.post("/v1/record_checkin", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('record_checkin: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('record_checkin rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/record_checkin", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('record_checkin list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('record_checkin list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('record_checkin accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/record_checkin/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('record_checkin get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/record_checkin/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('record_checkin missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'arrival_date': '2026-09-03', 'guest_name': 'sample', 'reference': 'sample', 'room_number': 'sample', 'status': 'open', 'arrived': 'sample', 'arrivals_count': 1}
    resp = client.post("/v1/todays_arrivals_board", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('todays_arrivals_board: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('todays_arrivals_board rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/todays_arrivals_board", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('todays_arrivals_board list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('todays_arrivals_board list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('todays_arrivals_board accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/todays_arrivals_board/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('todays_arrivals_board get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/todays_arrivals_board/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('todays_arrivals_board missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'check_in_date': '2026-09-03', 'check_out_date': '2026-09-03', 'reference': 'sample', 'room_number': 'sample', 'status': 'open', 'is_available': True}
    resp = client.post("/v1/room_availability_check", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('room_availability_check: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('room_availability_check rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/room_availability_check", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('room_availability_check list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('room_availability_check list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('room_availability_check accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/room_availability_check/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('room_availability_check get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/room_availability_check/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('room_availability_check missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'guest_name': 'sample', 'reference': 'sample', 'status': 'open', 'room_number': 'sample', 'preference': 'sample', 'note': 'sample'}
    resp = client.post("/v1/guest_notes_and_preferences", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('guest_notes_and_preferences: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('guest_notes_and_preferences rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/guest_notes_and_preferences", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('guest_notes_and_preferences list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('guest_notes_and_preferences list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('guest_notes_and_preferences accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/guest_notes_and_preferences/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('guest_notes_and_preferences get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/guest_notes_and_preferences/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('guest_notes_and_preferences missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'guest_name': 'sample', 'reference': 'sample', 'room_number': 'sample', 'status': 'open', 'channel': 'mcp', 'recipient': 'sample'}
    resp = client.post("/v1/checkin_notifications", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('checkin_notifications: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('checkin_notifications rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/checkin_notifications", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('checkin_notifications list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('checkin_notifications list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('checkin_notifications accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/checkin_notifications/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('checkin_notifications get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/checkin_notifications/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('checkin_notifications missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'reference': 'sample', 'status': 'open', 'summary_date': '2026-09-03', 'arrivals_count': 1, 'occupancy_percent': 'sample', 'no_show_count': 1}
    resp = client.post("/v1/daily_checkin_summary", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('daily_checkin_summary: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('daily_checkin_summary rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/daily_checkin_summary", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('daily_checkin_summary list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('daily_checkin_summary list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('daily_checkin_summary accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/daily_checkin_summary/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('daily_checkin_summary get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/daily_checkin_summary/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('daily_checkin_summary missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'actor': 'sample', 'reference': 'sample', 'status': 'open', 'change_type': 'create', 'subject_capability': 'sample', 'changed_at': '2026-09-03T10:00:00'}
    resp = client.post("/v1/audit_trail", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('audit_trail: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('audit_trail rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/audit_trail", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('audit_trail list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('audit_trail list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('audit_trail accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/audit_trail/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('audit_trail get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/audit_trail/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('audit_trail missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    assert not failures, "; ".join(failures)
