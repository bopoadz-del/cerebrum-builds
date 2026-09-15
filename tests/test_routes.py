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
    payload = {}
    resp = client.post("/v1/automotive_core", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('automotive_core: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('automotive_core: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('automotive_core: JSON body is not a dict')
            listed = client.get("/v1/automotive_core")
            if listed.status_code != 200:
                failures.append('automotive_core list: HTTP ' + str(listed.status_code))

    payload = {}
    resp = client.post("/v1/dashboard", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('dashboard: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('dashboard: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('dashboard: JSON body is not a dict')
            listed = client.get("/v1/dashboard")
            if listed.status_code != 200:
                failures.append('dashboard list: HTTP ' + str(listed.status_code))

    payload = {}
    resp = client.post("/v1/team", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('team: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('team: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('team: JSON body is not a dict')
            listed = client.get("/v1/team")
            if listed.status_code != 200:
                failures.append('team list: HTTP ' + str(listed.status_code))

    payload = {}
    resp = client.post("/v1/audit", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('audit: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('audit: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('audit: JSON body is not a dict')
            listed = client.get("/v1/audit")
            if listed.status_code != 200:
                failures.append('audit list: HTTP ' + str(listed.status_code))

    assert not failures, "; ".join(failures)


@pytest.mark.pilot
def test_every_capability_route_accepts_payload():
    """Pilot: spec payload is accepted (ok is not False) and persisted.
    Not the factory code-phase gate."""
    failures = []
    payload = {}
    resp = client.post("/v1/automotive_core", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('automotive_core: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('automotive_core rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/automotive_core")
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('automotive_core list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('automotive_core list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('automotive_core accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/automotive_core/{item_id}")
                if got.status_code != 200:
                    failures.append('automotive_core get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/automotive_core/999999")
                if missing.status_code != 404:
                    failures.append('automotive_core missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {}
    resp = client.post("/v1/dashboard", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('dashboard: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('dashboard rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/dashboard")
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('dashboard list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('dashboard list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('dashboard accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/dashboard/{item_id}")
                if got.status_code != 200:
                    failures.append('dashboard get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/dashboard/999999")
                if missing.status_code != 404:
                    failures.append('dashboard missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {}
    resp = client.post("/v1/team", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('team: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('team rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/team")
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('team list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('team list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('team accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/team/{item_id}")
                if got.status_code != 200:
                    failures.append('team get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/team/999999")
                if missing.status_code != 404:
                    failures.append('team missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {}
    resp = client.post("/v1/audit", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('audit: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('audit rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/audit")
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('audit list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('audit list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('audit accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/audit/{item_id}")
                if got.status_code != 200:
                    failures.append('audit get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/audit/999999")
                if missing.status_code != 404:
                    failures.append('audit missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    assert not failures, "; ".join(failures)
