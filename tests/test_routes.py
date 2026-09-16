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
    payload = {'product_name': 'sample', 'quantity_on_hand': 'sample', 'reference': 'sample', 'sku': 'sample', 'status': 'open', 'location': 'sample', 'reorder_point': 'sample', 'unit_cost': 'sample', 'supplier_name': 'sample', 'category': 'sample', 'movement_type': 'sample', 'last_counted_date': '2026-09-03'}
    resp = client.post("/v1/inventory_management", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('inventory_management: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('inventory_management: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('inventory_management: JSON body is not a dict')
            listed = client.get("/v1/inventory_management", headers=AUTH)
            if listed.status_code != 200:
                failures.append('inventory_management list: HTTP ' + str(listed.status_code))

    payload = {'customer_name': 'sample', 'order_number': 'sample', 'reference': 'sample', 'status': 'open', 'customer_email': 'guest@example.com', 'channel': 'email', 'order_total': 'sample', 'item_count': 1, 'payment_status': 'open', 'fulfilment_status': 'open', 'order_date': '2026-09-03', 'notes': 'sample'}
    resp = client.post("/v1/sales_and_orders", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('sales_and_orders: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('sales_and_orders: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('sales_and_orders: JSON body is not a dict')
            listed = client.get("/v1/sales_and_orders", headers=AUTH)
            if listed.status_code != 200:
                failures.append('sales_and_orders list: HTTP ' + str(listed.status_code))

    payload = {'customer_name': 'sample', 'reference': 'sample', 'status': 'open', 'customer_email': 'guest@example.com', 'segment': 'sample', 'lifetime_value': 'sample', 'orders_count': 1, 'last_purchase_date': '2026-09-03', 'loyalty_tier': 'sample', 'preferred_channel': 'email', 'insight_summary': 'sample', 'tags': 'sample'}
    resp = client.post("/v1/customer_insights", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('customer_insights: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('customer_insights: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('customer_insights: JSON body is not a dict')
            listed = client.get("/v1/customer_insights", headers=AUTH)
            if listed.status_code != 200:
                failures.append('customer_insights list: HTTP ' + str(listed.status_code))

    payload = {'dashboard_name': 'sample', 'metric_name': 'sample', 'reference': 'sample', 'status': 'open', 'metric_value': 'sample', 'period_start': 'sample', 'period_end': 'sample', 'store_location': 'sample', 'widget_type': 'sample', 'report_format': 'sample', 'owner': 'sample', 'generated_at': '2026-09-03T10:00:00'}
    resp = client.post("/v1/analytics_dashboard", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('analytics_dashboard: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('analytics_dashboard: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('analytics_dashboard: JSON body is not a dict')
            listed = client.get("/v1/analytics_dashboard", headers=AUTH)
            if listed.status_code != 200:
                failures.append('analytics_dashboard list: HTTP ' + str(listed.status_code))

    payload = {'purchase_order_number': 'sample', 'reference': 'sample', 'status': 'open', 'supplier_name': 'sample', 'supplier_email': 'guest@example.com', 'sku': 'sample', 'quantity_ordered': 'sample', 'unit_cost': 'sample', 'lead_time_days': 'sample', 'order_date': '2026-09-03', 'expected_date': '2026-09-03', 'payment_terms': 'sample'}
    resp = client.post("/v1/supplier_and_purchasing", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('supplier_and_purchasing: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('supplier_and_purchasing: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('supplier_and_purchasing: JSON body is not a dict')
            listed = client.get("/v1/supplier_and_purchasing", headers=AUTH)
            if listed.status_code != 200:
                failures.append('supplier_and_purchasing list: HTTP ' + str(listed.status_code))

    payload = {'integration_name': 'sample', 'reference': 'sample', 'status': 'open', 'channel': 'email', 'external_order_id': 'id-1', 'sync_direction': 'sample', 'sync_status': 'open', 'sku': 'sample', 'quantity': 1, 'sync_at': '2026-09-03T10:00:00', 'marketplace': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/omnichannel_integration", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('omnichannel_integration: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('omnichannel_integration: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('omnichannel_integration: JSON body is not a dict')
            listed = client.get("/v1/omnichannel_integration", headers=AUTH)
            if listed.status_code != 200:
                failures.append('omnichannel_integration list: HTTP ' + str(listed.status_code))

    payload = {'action_taken': 'sample', 'actor': 'sample', 'control_id': 'id-1', 'reference': 'sample', 'status': 'open', 'regulation': 'sample', 'event_type': 'sample', 'evidence_ref': 'sample', 'file_path': 'sample', 'findings': 'sample', 'occurred_at': '2026-09-03T10:00:00', 'severity': 'sample'}
    resp = client.post("/v1/compliance_and_audit", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('compliance_and_audit: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('compliance_and_audit: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('compliance_and_audit: JSON body is not a dict')
            listed = client.get("/v1/compliance_and_audit", headers=AUTH)
            if listed.status_code != 200:
                failures.append('compliance_and_audit list: HTTP ' + str(listed.status_code))

    assert not failures, "; ".join(failures)


@pytest.mark.pilot
def test_every_capability_route_accepts_payload():
    """Pilot: spec payload is accepted (ok is not False) and persisted.
    Not the factory code-phase gate."""
    failures = []
    payload = {'product_name': 'sample', 'quantity_on_hand': 'sample', 'reference': 'sample', 'sku': 'sample', 'status': 'open', 'location': 'sample', 'reorder_point': 'sample', 'unit_cost': 'sample', 'supplier_name': 'sample', 'category': 'sample', 'movement_type': 'sample', 'last_counted_date': '2026-09-03'}
    resp = client.post("/v1/inventory_management", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('inventory_management: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('inventory_management rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/inventory_management", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('inventory_management list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('inventory_management list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('inventory_management accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/inventory_management/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('inventory_management get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/inventory_management/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('inventory_management missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'customer_name': 'sample', 'order_number': 'sample', 'reference': 'sample', 'status': 'open', 'customer_email': 'guest@example.com', 'channel': 'email', 'order_total': 'sample', 'item_count': 1, 'payment_status': 'open', 'fulfilment_status': 'open', 'order_date': '2026-09-03', 'notes': 'sample'}
    resp = client.post("/v1/sales_and_orders", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('sales_and_orders: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('sales_and_orders rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/sales_and_orders", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('sales_and_orders list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('sales_and_orders list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('sales_and_orders accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/sales_and_orders/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('sales_and_orders get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/sales_and_orders/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('sales_and_orders missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'customer_name': 'sample', 'reference': 'sample', 'status': 'open', 'customer_email': 'guest@example.com', 'segment': 'sample', 'lifetime_value': 'sample', 'orders_count': 1, 'last_purchase_date': '2026-09-03', 'loyalty_tier': 'sample', 'preferred_channel': 'email', 'insight_summary': 'sample', 'tags': 'sample'}
    resp = client.post("/v1/customer_insights", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('customer_insights: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('customer_insights rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/customer_insights", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('customer_insights list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('customer_insights list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('customer_insights accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/customer_insights/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('customer_insights get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/customer_insights/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('customer_insights missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'dashboard_name': 'sample', 'metric_name': 'sample', 'reference': 'sample', 'status': 'open', 'metric_value': 'sample', 'period_start': 'sample', 'period_end': 'sample', 'store_location': 'sample', 'widget_type': 'sample', 'report_format': 'sample', 'owner': 'sample', 'generated_at': '2026-09-03T10:00:00'}
    resp = client.post("/v1/analytics_dashboard", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('analytics_dashboard: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('analytics_dashboard rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/analytics_dashboard", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('analytics_dashboard list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('analytics_dashboard list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('analytics_dashboard accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/analytics_dashboard/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('analytics_dashboard get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/analytics_dashboard/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('analytics_dashboard missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'purchase_order_number': 'sample', 'reference': 'sample', 'status': 'open', 'supplier_name': 'sample', 'supplier_email': 'guest@example.com', 'sku': 'sample', 'quantity_ordered': 'sample', 'unit_cost': 'sample', 'lead_time_days': 'sample', 'order_date': '2026-09-03', 'expected_date': '2026-09-03', 'payment_terms': 'sample'}
    resp = client.post("/v1/supplier_and_purchasing", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('supplier_and_purchasing: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('supplier_and_purchasing rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/supplier_and_purchasing", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('supplier_and_purchasing list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('supplier_and_purchasing list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('supplier_and_purchasing accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/supplier_and_purchasing/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('supplier_and_purchasing get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/supplier_and_purchasing/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('supplier_and_purchasing missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'integration_name': 'sample', 'reference': 'sample', 'status': 'open', 'channel': 'email', 'external_order_id': 'id-1', 'sync_direction': 'sample', 'sync_status': 'open', 'sku': 'sample', 'quantity': 1, 'sync_at': '2026-09-03T10:00:00', 'marketplace': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/omnichannel_integration", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('omnichannel_integration: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('omnichannel_integration rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/omnichannel_integration", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('omnichannel_integration list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('omnichannel_integration list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('omnichannel_integration accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/omnichannel_integration/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('omnichannel_integration get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/omnichannel_integration/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('omnichannel_integration missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'action_taken': 'sample', 'actor': 'sample', 'control_id': 'id-1', 'reference': 'sample', 'status': 'open', 'regulation': 'sample', 'event_type': 'sample', 'evidence_ref': 'sample', 'file_path': 'sample', 'findings': 'sample', 'occurred_at': '2026-09-03T10:00:00', 'severity': 'sample'}
    resp = client.post("/v1/compliance_and_audit", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('compliance_and_audit: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('compliance_and_audit rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/compliance_and_audit", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('compliance_and_audit list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('compliance_and_audit list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('compliance_and_audit accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/compliance_and_audit/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('compliance_and_audit get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/compliance_and_audit/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('compliance_and_audit missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    assert not failures, "; ".join(failures)
