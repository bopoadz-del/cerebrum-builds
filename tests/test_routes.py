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
    payload = {'audit': 'sample', 'database': 'sample', 'reference': 'sample', 'status': 'open', 'storage': 'sample', 'mileage': 'sample'}
    resp = client.post("/v1/fleet_registry", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('fleet_registry: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('fleet_registry: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('fleet_registry: JSON body is not a dict')
            listed = client.get("/v1/fleet_registry", headers=AUTH)
            if listed.status_code != 200:
                failures.append('fleet_registry list: HTTP ' + str(listed.status_code))

    payload = {'reference': 'sample', 'status': 'open', 'pickup_date': '2026-09-03', 'return_date': '2026-09-03', 'extension_days': 'sample', 'daily_rate': 'sample', 'deposit_amount': 'sample'}
    resp = client.post("/v1/rental_contract_management", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('rental_contract_management: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('rental_contract_management: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('rental_contract_management: JSON body is not a dict')
            listed = client.get("/v1/rental_contract_management", headers=AUTH)
            if listed.status_code != 200:
                failures.append('rental_contract_management list: HTTP ' + str(listed.status_code))

    payload = {'reference': 'sample', 'status': 'open', 'title': 'sample', 'schedule_kind': 'date', 'due_date': '2026-09-03', 'due_mileage': 'sample', 'downtime_days': 'sample', 'estimated_cost': 'sample'}
    resp = client.post("/v1/maintenance_scheduling", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('maintenance_scheduling: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('maintenance_scheduling: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('maintenance_scheduling: JSON body is not a dict')
            listed = client.get("/v1/maintenance_scheduling", headers=AUTH)
            if listed.status_code != 200:
                failures.append('maintenance_scheduling list: HTTP ' + str(listed.status_code))

    payload = {'analytics': 'sample', 'audit': 'sample', 'formula_executor': 'sample', 'reference': 'sample', 'status': 'open', 'validation': 'sample', 'duration_days': 'sample', 'base_rate': 'sample', 'mileage_charge': 'sample', 'fuel_charge': 'sample', 'late_return_charge': 'sample', 'extras_charge': 'sample', 'deposit_amount': 'sample'}
    resp = client.post("/v1/pricing_and_rate_cards", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('pricing_and_rate_cards: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('pricing_and_rate_cards: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('pricing_and_rate_cards: JSON body is not a dict')
            listed = client.get("/v1/pricing_and_rate_cards", headers=AUTH)
            if listed.status_code != 200:
                failures.append('pricing_and_rate_cards list: HTTP ' + str(listed.status_code))

    payload = {'analytics': 'sample', 'audit': 'sample', 'database': 'sample', 'reference': 'sample', 'status': 'open', 'workflow': 'sample', 'amount_due': 'sample', 'deposit_held': 'sample', 'balance_due': 'sample'}
    resp = client.post("/v1/invoicing_and_deposits", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('invoicing_and_deposits: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('invoicing_and_deposits: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('invoicing_and_deposits: JSON body is not a dict')
            listed = client.get("/v1/invoicing_and_deposits", headers=AUTH)
            if listed.status_code != 200:
                failures.append('invoicing_and_deposits list: HTTP ' + str(listed.status_code))

    payload = {'analytics': 'sample', 'dashboard': 'sample', 'estate_registry': 'sample', 'portfolio_rollup': 'sample', 'reference': 'sample', 'status': 'open', 'fleet_utilisation': 'sample', 'revenue': 'sample', 'cost': 'sample'}
    resp = client.post("/v1/multi_branch_rollup", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('multi_branch_rollup: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('multi_branch_rollup: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('multi_branch_rollup: JSON body is not a dict')
            listed = client.get("/v1/multi_branch_rollup", headers=AUTH)
            if listed.status_code != 200:
                failures.append('multi_branch_rollup list: HTTP ' + str(listed.status_code))

    payload = {'analytics': 'sample', 'dashboard': 'sample', 'memory': 'sample', 'reference': 'sample', 'status': 'open', 'vector_search': 'sample', 'value': 'sample'}
    resp = client.post("/v1/reporting_analytics", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('reporting_analytics: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('reporting_analytics: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('reporting_analytics: JSON body is not a dict')
            listed = client.get("/v1/reporting_analytics", headers=AUTH)
            if listed.status_code != 200:
                failures.append('reporting_analytics list: HTTP ' + str(listed.status_code))

    payload = {'audit': 'sample', 'capture': 'sample', 'evidence_verifier': 'sample', 'file_hasher': 'sample', 'reference': 'sample', 'status': 'open'}
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
    payload = {'audit': 'sample', 'database': 'sample', 'reference': 'sample', 'status': 'open', 'storage': 'sample', 'mileage': 'sample'}
    resp = client.post("/v1/fleet_registry", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('fleet_registry: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('fleet_registry rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/fleet_registry", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('fleet_registry list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('fleet_registry list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('fleet_registry accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/fleet_registry/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('fleet_registry get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/fleet_registry/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('fleet_registry missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'reference': 'sample', 'status': 'open', 'pickup_date': '2026-09-03', 'return_date': '2026-09-03', 'extension_days': 'sample', 'daily_rate': 'sample', 'deposit_amount': 'sample'}
    resp = client.post("/v1/rental_contract_management", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('rental_contract_management: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('rental_contract_management rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/rental_contract_management", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('rental_contract_management list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('rental_contract_management list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('rental_contract_management accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/rental_contract_management/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('rental_contract_management get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/rental_contract_management/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('rental_contract_management missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'reference': 'sample', 'status': 'open', 'title': 'sample', 'schedule_kind': 'date', 'due_date': '2026-09-03', 'due_mileage': 'sample', 'downtime_days': 'sample', 'estimated_cost': 'sample'}
    resp = client.post("/v1/maintenance_scheduling", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('maintenance_scheduling: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('maintenance_scheduling rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/maintenance_scheduling", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('maintenance_scheduling list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('maintenance_scheduling list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('maintenance_scheduling accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/maintenance_scheduling/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('maintenance_scheduling get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/maintenance_scheduling/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('maintenance_scheduling missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'analytics': 'sample', 'audit': 'sample', 'formula_executor': 'sample', 'reference': 'sample', 'status': 'open', 'validation': 'sample', 'duration_days': 'sample', 'base_rate': 'sample', 'mileage_charge': 'sample', 'fuel_charge': 'sample', 'late_return_charge': 'sample', 'extras_charge': 'sample', 'deposit_amount': 'sample'}
    resp = client.post("/v1/pricing_and_rate_cards", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('pricing_and_rate_cards: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('pricing_and_rate_cards rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/pricing_and_rate_cards", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('pricing_and_rate_cards list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('pricing_and_rate_cards list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('pricing_and_rate_cards accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/pricing_and_rate_cards/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('pricing_and_rate_cards get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/pricing_and_rate_cards/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('pricing_and_rate_cards missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'analytics': 'sample', 'audit': 'sample', 'database': 'sample', 'reference': 'sample', 'status': 'open', 'workflow': 'sample', 'amount_due': 'sample', 'deposit_held': 'sample', 'balance_due': 'sample'}
    resp = client.post("/v1/invoicing_and_deposits", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('invoicing_and_deposits: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('invoicing_and_deposits rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/invoicing_and_deposits", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('invoicing_and_deposits list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('invoicing_and_deposits list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('invoicing_and_deposits accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/invoicing_and_deposits/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('invoicing_and_deposits get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/invoicing_and_deposits/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('invoicing_and_deposits missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'analytics': 'sample', 'dashboard': 'sample', 'estate_registry': 'sample', 'portfolio_rollup': 'sample', 'reference': 'sample', 'status': 'open', 'fleet_utilisation': 'sample', 'revenue': 'sample', 'cost': 'sample'}
    resp = client.post("/v1/multi_branch_rollup", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('multi_branch_rollup: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('multi_branch_rollup rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/multi_branch_rollup", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('multi_branch_rollup list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('multi_branch_rollup list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('multi_branch_rollup accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/multi_branch_rollup/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('multi_branch_rollup get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/multi_branch_rollup/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('multi_branch_rollup missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'analytics': 'sample', 'dashboard': 'sample', 'memory': 'sample', 'reference': 'sample', 'status': 'open', 'vector_search': 'sample', 'value': 'sample'}
    resp = client.post("/v1/reporting_analytics", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('reporting_analytics: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('reporting_analytics rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/reporting_analytics", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('reporting_analytics list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('reporting_analytics list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('reporting_analytics accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/reporting_analytics/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('reporting_analytics get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/reporting_analytics/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('reporting_analytics missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'audit': 'sample', 'capture': 'sample', 'evidence_verifier': 'sample', 'file_hasher': 'sample', 'reference': 'sample', 'status': 'open'}
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


def test_staff_session_continues_an_authenticated_client():
    """Authenticate once, continue on the session cookie — and nothing else.

    The served console authenticates with the platform token and then keeps
    working; the platform mints an opaque session id bound to the tenant
    that token resolved to. This checks the three states that matter:
    anonymous is refused, the cookie alone is answered, and a session id the
    platform never issued is refused rather than trusted.
    """
    from app.tenancy import SESSION_COOKIE

    payload = {
        "reference": "session-check",
        "status": "open",
        "plate_number": "SESS-001",
        "vin": "VINSESSION0001",
        "branch": "north",
        "category": "compact",
        "vehicle_state": "available",
        "mileage": 120,
        "service_history": "none",
        "attachment_path": "",
        "audit": "sample",
        "database": "sample",
        "storage": "sample",
    }

    anonymous = TestClient(app)
    with anonymous as anon:
        assert anon.get("/v1/fleet_registry").status_code == 401
        assert anon.post("/v1/fleet_registry", json={}).status_code == 401

    staff = TestClient(app)
    with staff as console:
        created = console.post("/v1/fleet_registry", json=payload, headers=AUTH)
        assert created.status_code == 200, created.text[:300]
        assert created.json().get("ok") is not False, created.text[:300]
        assert console.cookies.get(SESSION_COOKIE), "no staff session was minted"

        listed = console.get("/v1/fleet_registry")  # cookie only, no bearer
        assert listed.status_code == 200, listed.text[:300]
        assert _listed(listed.json()), "session client saw none of its own rows"

    forged = TestClient(app)
    with forged as stranger:
        stranger.cookies.set(SESSION_COOKIE, "not-a-session-this-platform-issued")
        assert stranger.get("/v1/fleet_registry").status_code == 401
