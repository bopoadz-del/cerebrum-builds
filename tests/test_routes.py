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
    payload = {'branch': 'sample', 'reference': 'sample', 'role_view': 'sample', 'status': 'open', 'view_scope': 'sample', 'period': 'sample', 'metrics_summary': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/branch_and_consolidated_operations", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('branch_and_consolidated_operations: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('branch_and_consolidated_operations: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('branch_and_consolidated_operations: JSON body is not a dict')
            listed = client.get("/v1/branch_and_consolidated_operations", headers=AUTH)
            if listed.status_code != 200:
                failures.append('branch_and_consolidated_operations list: HTTP ' + str(listed.status_code))

    payload = {'branch': 'sample', 'item_name': 'sample', 'item_type': 'ingredient', 'reference': 'sample', 'status': 'open', 'quantity_on_hand': 'sample', 'reorder_threshold': 'sample', 'unit': 'sample', 'supplier': 'sample', 'transfer_to_branch': 'sample', 'low_stock': 'sample'}
    resp = client.post("/v1/inventory_and_replenishment", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('inventory_and_replenishment: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('inventory_and_replenishment: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('inventory_and_replenishment: JSON body is not a dict')
            listed = client.get("/v1/inventory_and_replenishment", headers=AUTH)
            if listed.status_code != 200:
                failures.append('inventory_and_replenishment list: HTTP ' + str(listed.status_code))

    payload = {'branch': 'sample', 'entry_type': 'sale', 'reference': 'sample', 'status': 'open', 'entry_date': '2026-09-03', 'amount': 'sample', 'margin_percent': 'sample', 'ingredient': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/branch_books_and_accounting", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('branch_books_and_accounting: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('branch_books_and_accounting: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('branch_books_and_accounting: JSON body is not a dict')
            listed = client.get("/v1/branch_books_and_accounting", headers=AUTH)
            if listed.status_code != 200:
                failures.append('branch_books_and_accounting list: HTTP ' + str(listed.status_code))

    payload = {'branch': 'sample', 'driver': 'sample', 'reference': 'sample', 'status': 'open', 'vehicle_type': 'car', 'vehicle_code': 'id-1', 'delivery_zone': 'sample', 'route': 'sample', 'order_reference': 'sample', 'proof_of_delivery': 'sample', 'scheduled_at': '2026-09-03T10:00:00'}
    resp = client.post("/v1/delivery_and_dispatch", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('delivery_and_dispatch: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('delivery_and_dispatch: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('delivery_and_dispatch: JSON body is not a dict')
            listed = client.get("/v1/delivery_and_dispatch", headers=AUTH)
            if listed.status_code != 200:
                failures.append('delivery_and_dispatch list: HTTP ' + str(listed.status_code))

    payload = {'branch': 'sample', 'channel': 'email', 'customer_name': 'sample', 'reference': 'sample', 'status': 'open', 'order_status': 'open', 'payment_status': 'unpaid', 'confirmed': 'sample', 'due_at': '2026-09-03T10:00:00', 'follow_up_note': 'sample'}
    resp = client.post("/v1/order_follow_up", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('order_follow_up: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('order_follow_up: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('order_follow_up: JSON body is not a dict')
            listed = client.get("/v1/order_follow_up", headers=AUTH)
            if listed.status_code != 200:
                failures.append('order_follow_up list: HTTP ' + str(listed.status_code))

    payload = {'branch': 'sample', 'event_name': 'sample', 'reference': 'sample', 'status': 'open', 'event_date': '2026-09-03', 'guest_count': 1, 'deposit_amount': 'sample', 'delivery_time': '10:00:00', 'venue': 'sample', 'contact_email': 'guest@example.com'}
    resp = client.post("/v1/events_supply", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('events_supply: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('events_supply: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('events_supply: JSON body is not a dict')
            listed = client.get("/v1/events_supply", headers=AUTH)
            if listed.status_code != 200:
                failures.append('events_supply list: HTTP ' + str(listed.status_code))

    payload = {'branch': 'sample', 'document_type': 'price_list', 'question': 'sample', 'reference': 'sample', 'status': 'open', 'answer': 'sample', 'citations': 'sample', 'confidence': 'sample'}
    resp = client.post("/v1/document_grounded_knowledge", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('document_grounded_knowledge: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('document_grounded_knowledge: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('document_grounded_knowledge: JSON body is not a dict')
            listed = client.get("/v1/document_grounded_knowledge", headers=AUTH)
            if listed.status_code != 200:
                failures.append('document_grounded_knowledge list: HTTP ' + str(listed.status_code))

    payload = {'branch': 'sample', 'direction': 'inbound', 'mailbox': 'sample', 'reference': 'sample', 'status': 'open', 'subject': 'sample', 'body': 'sample', 'message_reference': 'sample', 'received_at': '2026-09-03T10:00:00'}
    resp = client.post("/v1/outlook_branch_messaging_integration", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('outlook_branch_messaging_integration: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('outlook_branch_messaging_integration: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('outlook_branch_messaging_integration: JSON body is not a dict')
            listed = client.get("/v1/outlook_branch_messaging_integration", headers=AUTH)
            if listed.status_code != 200:
                failures.append('outlook_branch_messaging_integration list: HTTP ' + str(listed.status_code))

    assert not failures, "; ".join(failures)


@pytest.mark.pilot
def test_every_capability_route_accepts_payload():
    """Pilot: spec payload is accepted (ok is not False) and persisted.
    Not the factory code-phase gate."""
    failures = []
    payload = {'branch': 'sample', 'reference': 'sample', 'role_view': 'sample', 'status': 'open', 'view_scope': 'sample', 'period': 'sample', 'metrics_summary': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/branch_and_consolidated_operations", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('branch_and_consolidated_operations: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('branch_and_consolidated_operations rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/branch_and_consolidated_operations", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('branch_and_consolidated_operations list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('branch_and_consolidated_operations list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('branch_and_consolidated_operations accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/branch_and_consolidated_operations/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('branch_and_consolidated_operations get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/branch_and_consolidated_operations/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('branch_and_consolidated_operations missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'branch': 'sample', 'item_name': 'sample', 'item_type': 'ingredient', 'reference': 'sample', 'status': 'open', 'quantity_on_hand': 'sample', 'reorder_threshold': 'sample', 'unit': 'sample', 'supplier': 'sample', 'transfer_to_branch': 'sample', 'low_stock': 'sample'}
    resp = client.post("/v1/inventory_and_replenishment", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('inventory_and_replenishment: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('inventory_and_replenishment rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/inventory_and_replenishment", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('inventory_and_replenishment list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('inventory_and_replenishment list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('inventory_and_replenishment accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/inventory_and_replenishment/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('inventory_and_replenishment get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/inventory_and_replenishment/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('inventory_and_replenishment missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'branch': 'sample', 'entry_type': 'sale', 'reference': 'sample', 'status': 'open', 'entry_date': '2026-09-03', 'amount': 'sample', 'margin_percent': 'sample', 'ingredient': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/branch_books_and_accounting", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('branch_books_and_accounting: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('branch_books_and_accounting rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/branch_books_and_accounting", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('branch_books_and_accounting list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('branch_books_and_accounting list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('branch_books_and_accounting accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/branch_books_and_accounting/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('branch_books_and_accounting get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/branch_books_and_accounting/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('branch_books_and_accounting missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'branch': 'sample', 'driver': 'sample', 'reference': 'sample', 'status': 'open', 'vehicle_type': 'car', 'vehicle_code': 'id-1', 'delivery_zone': 'sample', 'route': 'sample', 'order_reference': 'sample', 'proof_of_delivery': 'sample', 'scheduled_at': '2026-09-03T10:00:00'}
    resp = client.post("/v1/delivery_and_dispatch", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('delivery_and_dispatch: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('delivery_and_dispatch rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/delivery_and_dispatch", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('delivery_and_dispatch list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('delivery_and_dispatch list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('delivery_and_dispatch accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/delivery_and_dispatch/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('delivery_and_dispatch get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/delivery_and_dispatch/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('delivery_and_dispatch missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'branch': 'sample', 'channel': 'email', 'customer_name': 'sample', 'reference': 'sample', 'status': 'open', 'order_status': 'open', 'payment_status': 'unpaid', 'confirmed': 'sample', 'due_at': '2026-09-03T10:00:00', 'follow_up_note': 'sample'}
    resp = client.post("/v1/order_follow_up", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('order_follow_up: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('order_follow_up rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/order_follow_up", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('order_follow_up list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('order_follow_up list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('order_follow_up accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/order_follow_up/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('order_follow_up get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/order_follow_up/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('order_follow_up missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'branch': 'sample', 'event_name': 'sample', 'reference': 'sample', 'status': 'open', 'event_date': '2026-09-03', 'guest_count': 1, 'deposit_amount': 'sample', 'delivery_time': '10:00:00', 'venue': 'sample', 'contact_email': 'guest@example.com'}
    resp = client.post("/v1/events_supply", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('events_supply: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('events_supply rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/events_supply", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('events_supply list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('events_supply list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('events_supply accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/events_supply/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('events_supply get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/events_supply/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('events_supply missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'branch': 'sample', 'document_type': 'price_list', 'question': 'sample', 'reference': 'sample', 'status': 'open', 'answer': 'sample', 'citations': 'sample', 'confidence': 'sample'}
    resp = client.post("/v1/document_grounded_knowledge", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('document_grounded_knowledge: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('document_grounded_knowledge rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/document_grounded_knowledge", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('document_grounded_knowledge list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('document_grounded_knowledge list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('document_grounded_knowledge accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/document_grounded_knowledge/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('document_grounded_knowledge get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/document_grounded_knowledge/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('document_grounded_knowledge missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'branch': 'sample', 'direction': 'inbound', 'mailbox': 'sample', 'reference': 'sample', 'status': 'open', 'subject': 'sample', 'body': 'sample', 'message_reference': 'sample', 'received_at': '2026-09-03T10:00:00'}
    resp = client.post("/v1/outlook_branch_messaging_integration", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('outlook_branch_messaging_integration: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('outlook_branch_messaging_integration rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/outlook_branch_messaging_integration", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('outlook_branch_messaging_integration list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('outlook_branch_messaging_integration list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('outlook_branch_messaging_integration accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/outlook_branch_messaging_integration/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('outlook_branch_messaging_integration get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/outlook_branch_messaging_integration/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('outlook_branch_messaging_integration missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    assert not failures, "; ".join(failures)
