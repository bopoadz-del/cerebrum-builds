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
    resp = client.post("/v1/stock_inventory_management", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('stock_inventory_management: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('stock_inventory_management: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('stock_inventory_management: JSON body is not a dict')
            listed = client.get("/v1/stock_inventory_management", headers=AUTH)
            if listed.status_code != 200:
                failures.append('stock_inventory_management list: HTTP ' + str(listed.status_code))

    payload = {}
    resp = client.post("/v1/product_pricing", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('product_pricing: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('product_pricing: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('product_pricing: JSON body is not a dict')
            listed = client.get("/v1/product_pricing", headers=AUTH)
            if listed.status_code != 200:
                failures.append('product_pricing list: HTTP ' + str(listed.status_code))

    payload = {}
    resp = client.post("/v1/delivery_dispatch_tracking", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('delivery_dispatch_tracking: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('delivery_dispatch_tracking: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('delivery_dispatch_tracking: JSON body is not a dict')
            listed = client.get("/v1/delivery_dispatch_tracking", headers=AUTH)
            if listed.status_code != 200:
                failures.append('delivery_dispatch_tracking list: HTTP ' + str(listed.status_code))

    payload = {}
    resp = client.post("/v1/fleet_cost_tracking", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('fleet_cost_tracking: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('fleet_cost_tracking: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('fleet_cost_tracking: JSON body is not a dict')
            listed = client.get("/v1/fleet_cost_tracking", headers=AUTH)
            if listed.status_code != 200:
                failures.append('fleet_cost_tracking list: HTTP ' + str(listed.status_code))

    payload = {}
    resp = client.post("/v1/management_reporting_dashboard", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('management_reporting_dashboard: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('management_reporting_dashboard: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('management_reporting_dashboard: JSON body is not a dict')
            listed = client.get("/v1/management_reporting_dashboard", headers=AUTH)
            if listed.status_code != 200:
                failures.append('management_reporting_dashboard list: HTTP ' + str(listed.status_code))

    payload = {}
    resp = client.post("/v1/user_roles_workforce", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('user_roles_workforce: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('user_roles_workforce: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('user_roles_workforce: JSON body is not a dict')
            listed = client.get("/v1/user_roles_workforce", headers=AUTH)
            if listed.status_code != 200:
                failures.append('user_roles_workforce list: HTTP ' + str(listed.status_code))

    payload = {}
    resp = client.post("/v1/document_knowledge_qa", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('document_knowledge_qa: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('document_knowledge_qa: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('document_knowledge_qa: JSON body is not a dict')
            listed = client.get("/v1/document_knowledge_qa", headers=AUTH)
            if listed.status_code != 200:
                failures.append('document_knowledge_qa list: HTTP ' + str(listed.status_code))

    payload = {}
    resp = client.post("/v1/procedures_readiness_and_audit_trail", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('procedures_readiness_and_audit_trail: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('procedures_readiness_and_audit_trail: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('procedures_readiness_and_audit_trail: JSON body is not a dict')
            listed = client.get("/v1/procedures_readiness_and_audit_trail", headers=AUTH)
            if listed.status_code != 200:
                failures.append('procedures_readiness_and_audit_trail list: HTTP ' + str(listed.status_code))

    assert not failures, "; ".join(failures)


@pytest.mark.pilot
def test_every_capability_route_accepts_payload():
    """Pilot: spec payload is accepted (ok is not False) and persisted.
    Not the factory code-phase gate."""
    failures = []
    payload = {}
    resp = client.post("/v1/stock_inventory_management", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('stock_inventory_management: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('stock_inventory_management rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/stock_inventory_management", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('stock_inventory_management list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('stock_inventory_management list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('stock_inventory_management accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/stock_inventory_management/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('stock_inventory_management get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/stock_inventory_management/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('stock_inventory_management missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {}
    resp = client.post("/v1/product_pricing", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('product_pricing: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('product_pricing rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/product_pricing", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('product_pricing list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('product_pricing list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('product_pricing accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/product_pricing/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('product_pricing get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/product_pricing/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('product_pricing missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {}
    resp = client.post("/v1/delivery_dispatch_tracking", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('delivery_dispatch_tracking: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('delivery_dispatch_tracking rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/delivery_dispatch_tracking", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('delivery_dispatch_tracking list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('delivery_dispatch_tracking list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('delivery_dispatch_tracking accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/delivery_dispatch_tracking/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('delivery_dispatch_tracking get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/delivery_dispatch_tracking/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('delivery_dispatch_tracking missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {}
    resp = client.post("/v1/fleet_cost_tracking", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('fleet_cost_tracking: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('fleet_cost_tracking rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/fleet_cost_tracking", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('fleet_cost_tracking list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('fleet_cost_tracking list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('fleet_cost_tracking accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/fleet_cost_tracking/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('fleet_cost_tracking get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/fleet_cost_tracking/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('fleet_cost_tracking missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {}
    resp = client.post("/v1/management_reporting_dashboard", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('management_reporting_dashboard: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('management_reporting_dashboard rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/management_reporting_dashboard", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('management_reporting_dashboard list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('management_reporting_dashboard list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('management_reporting_dashboard accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/management_reporting_dashboard/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('management_reporting_dashboard get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/management_reporting_dashboard/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('management_reporting_dashboard missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {}
    resp = client.post("/v1/user_roles_workforce", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('user_roles_workforce: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('user_roles_workforce rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/user_roles_workforce", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('user_roles_workforce list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('user_roles_workforce list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('user_roles_workforce accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/user_roles_workforce/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('user_roles_workforce get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/user_roles_workforce/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('user_roles_workforce missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {}
    resp = client.post("/v1/document_knowledge_qa", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('document_knowledge_qa: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('document_knowledge_qa rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/document_knowledge_qa", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('document_knowledge_qa list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('document_knowledge_qa list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('document_knowledge_qa accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/document_knowledge_qa/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('document_knowledge_qa get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/document_knowledge_qa/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('document_knowledge_qa missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {}
    resp = client.post("/v1/procedures_readiness_and_audit_trail", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('procedures_readiness_and_audit_trail: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('procedures_readiness_and_audit_trail rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/procedures_readiness_and_audit_trail", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('procedures_readiness_and_audit_trail list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('procedures_readiness_and_audit_trail list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('procedures_readiness_and_audit_trail accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/procedures_readiness_and_audit_trail/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('procedures_readiness_and_audit_trail get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/procedures_readiness_and_audit_trail/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('procedures_readiness_and_audit_trail missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    assert not failures, "; ".join(failures)
