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
    payload = {'category': 'electrical', 'description': 'sample', 'priority': 'critical', 'raised_by': 'sample', 'raised_by_role': 'school_staff', 'reference': 'sample', 'school': 'sample', 'status': 'open', 'site_code': 'id-1', 'contact_email': 'guest@example.com', 'contact_phone': 'sample', 'logged_by': 'sample', 'assigned_to': 'sample', 'assignment_mode': 'auto', 'reported_at': '2026-09-03T10:00:00', 'due_at': '2026-09-03T10:00:00', 'sla_hours': 'sample', 'closed_at': '2026-09-03T10:00:00', 'resolution_notes': 'sample', 'work_order_reference': 'sample'}
    resp = client.post("/v1/complaints_management", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('complaints_management: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('complaints_management: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('complaints_management: JSON body is not a dict')
            listed = client.get("/v1/complaints_management", headers=AUTH)
            if listed.status_code != 200:
                failures.append('complaints_management list: HTTP ' + str(listed.status_code))

    payload = {'assignment_mode': 'auto', 'category': 'electrical', 'complaint_reference': 'sample', 'priority': 'critical', 'reference': 'sample', 'required_trade': 'sample', 'school': 'sample', 'status': 'open', 'required_skill': 'sample', 'candidate_count': 1, 'assigned_to': 'sample', 'assigned_role': 'technician', 'match_score': 'sample', 'workload_score': 'sample', 'queue_position': 'sample', 'override_reason': 'sample', 'assigned_at': '2026-09-03T10:00:00'}
    resp = client.post("/v1/auto_assignment", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('auto_assignment: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('auto_assignment: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('auto_assignment: JSON body is not a dict')
            listed = client.get("/v1/auto_assignment", headers=AUTH)
            if listed.status_code != 200:
                failures.append('auto_assignment list: HTTP ' + str(listed.status_code))

    payload = {'headcount': 'sample', 'reference': 'sample', 'school': 'sample', 'shift': 'morning', 'status': 'open', 'team_name': 'sample', 'team_type': 'technician', 'trade': 'sample', 'lead_name': 'sample', 'lead_email': 'guest@example.com', 'contact_phone': 'sample', 'active': 'sample', 'open_jobs': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/workforce_management", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('workforce_management: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('workforce_management: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('workforce_management: JSON body is not a dict')
            listed = client.get("/v1/workforce_management", headers=AUTH)
            if listed.status_code != 200:
                failures.append('workforce_management list: HTTP ' + str(listed.status_code))

    payload = {'complaints_open': 'sample', 'period': 'sample', 'reference': 'sample', 'school': 'sample', 'scope': 'school', 'status': 'open', 'complaints_in_progress': 'sample', 'complaints_closed': 'sample', 'jobs_in_progress': 'sample', 'sla_breaches': 'sample', 'sla_compliance_pct': 'sample', 'avg_closure_hours': 'sample', 'headline': 'sample', 'generated_at': '2026-09-03T10:00:00'}
    resp = client.post("/v1/management_dashboards", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('management_dashboards: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('management_dashboards: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('management_dashboards: JSON body is not a dict')
            listed = client.get("/v1/management_dashboards", headers=AUTH)
            if listed.status_code != 200:
                failures.append('management_dashboards list: HTTP ' + str(listed.status_code))

    payload = {'complaints_total': 'sample', 'period_end': 'sample', 'period_start': 'sample', 'reference': 'sample', 'report_type': 'daily', 'school': 'sample', 'scope': 'school', 'status': 'open', 'closed_total': 'sample', 'avg_closure_hours': 'sample', 'sla_compliance_pct': 'sample', 'top_category': 'sample', 'busiest_school': 'sample', 'recipients': 'sample', 'generated_at': '2026-09-03T10:00:00'}
    resp = client.post("/v1/reporting", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('reporting: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('reporting: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('reporting: JSON body is not a dict')
            listed = client.get("/v1/reporting", headers=AUTH)
            if listed.status_code != 200:
                failures.append('reporting list: HTTP ' + str(listed.status_code))

    payload = {'access_scope': 'portfolio', 'principal': 'sample', 'reference': 'sample', 'role': 'management', 'school': 'sample', 'status': 'open', 'principal_email': 'guest@example.com', 'permissions': 'sample', 'granted_by': 'sample', 'effective_from': 'sample', 'last_review_at': '2026-09-03T10:00:00', 'active': 'sample', 'notes': 'sample'}
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

    payload = {'direction': 'inbound', 'entity_type': 'purchase_order', 'integration': 'erp', 'mode': 'placeholder', 'reference': 'sample', 'status': 'open', 'external_reference': 'sample', 'endpoint': 'sample', 'currency': 'sample', 'amount': 'sample', 'sync_state': 'not_implemented', 'last_sync_at': '2026-09-03T10:00:00', 'detail': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/erp_integration", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('erp_integration: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('erp_integration: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('erp_integration: JSON body is not a dict')
            listed = client.get("/v1/erp_integration", headers=AUTH)
            if listed.status_code != 200:
                failures.append('erp_integration list: HTTP ' + str(listed.status_code))

    payload = {'booking_reference': 'sample', 'facility': 'sample', 'integration': 'booking_system', 'mode': 'placeholder', 'reference': 'sample', 'school': 'sample', 'slot_start': 'sample', 'status': 'open', 'slot_end': 'sample', 'requested_by': 'sample', 'sync_state': 'not_implemented', 'last_sync_at': '2026-09-03T10:00:00', 'detail': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/booking_system_integration", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('booking_system_integration: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('booking_system_integration: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('booking_system_integration: JSON body is not a dict')
            listed = client.get("/v1/booking_system_integration", headers=AUTH)
            if listed.status_code != 200:
                failures.append('booking_system_integration list: HTTP ' + str(listed.status_code))

    assert not failures, "; ".join(failures)


@pytest.mark.pilot
def test_every_capability_route_accepts_payload():
    """Pilot: spec payload is accepted (ok is not False) and persisted.
    Not the factory code-phase gate."""
    failures = []
    payload = {'category': 'electrical', 'description': 'sample', 'priority': 'critical', 'raised_by': 'sample', 'raised_by_role': 'school_staff', 'reference': 'sample', 'school': 'sample', 'status': 'open', 'site_code': 'id-1', 'contact_email': 'guest@example.com', 'contact_phone': 'sample', 'logged_by': 'sample', 'assigned_to': 'sample', 'assignment_mode': 'auto', 'reported_at': '2026-09-03T10:00:00', 'due_at': '2026-09-03T10:00:00', 'sla_hours': 'sample', 'closed_at': '2026-09-03T10:00:00', 'resolution_notes': 'sample', 'work_order_reference': 'sample'}
    resp = client.post("/v1/complaints_management", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('complaints_management: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('complaints_management rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/complaints_management", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('complaints_management list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('complaints_management list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('complaints_management accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/complaints_management/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('complaints_management get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/complaints_management/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('complaints_management missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'assignment_mode': 'auto', 'category': 'electrical', 'complaint_reference': 'sample', 'priority': 'critical', 'reference': 'sample', 'required_trade': 'sample', 'school': 'sample', 'status': 'open', 'required_skill': 'sample', 'candidate_count': 1, 'assigned_to': 'sample', 'assigned_role': 'technician', 'match_score': 'sample', 'workload_score': 'sample', 'queue_position': 'sample', 'override_reason': 'sample', 'assigned_at': '2026-09-03T10:00:00'}
    resp = client.post("/v1/auto_assignment", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('auto_assignment: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('auto_assignment rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/auto_assignment", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('auto_assignment list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('auto_assignment list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('auto_assignment accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/auto_assignment/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('auto_assignment get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/auto_assignment/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('auto_assignment missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'headcount': 'sample', 'reference': 'sample', 'school': 'sample', 'shift': 'morning', 'status': 'open', 'team_name': 'sample', 'team_type': 'technician', 'trade': 'sample', 'lead_name': 'sample', 'lead_email': 'guest@example.com', 'contact_phone': 'sample', 'active': 'sample', 'open_jobs': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/workforce_management", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('workforce_management: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('workforce_management rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/workforce_management", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('workforce_management list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('workforce_management list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('workforce_management accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/workforce_management/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('workforce_management get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/workforce_management/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('workforce_management missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'complaints_open': 'sample', 'period': 'sample', 'reference': 'sample', 'school': 'sample', 'scope': 'school', 'status': 'open', 'complaints_in_progress': 'sample', 'complaints_closed': 'sample', 'jobs_in_progress': 'sample', 'sla_breaches': 'sample', 'sla_compliance_pct': 'sample', 'avg_closure_hours': 'sample', 'headline': 'sample', 'generated_at': '2026-09-03T10:00:00'}
    resp = client.post("/v1/management_dashboards", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('management_dashboards: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('management_dashboards rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/management_dashboards", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('management_dashboards list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('management_dashboards list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('management_dashboards accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/management_dashboards/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('management_dashboards get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/management_dashboards/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('management_dashboards missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'complaints_total': 'sample', 'period_end': 'sample', 'period_start': 'sample', 'reference': 'sample', 'report_type': 'daily', 'school': 'sample', 'scope': 'school', 'status': 'open', 'closed_total': 'sample', 'avg_closure_hours': 'sample', 'sla_compliance_pct': 'sample', 'top_category': 'sample', 'busiest_school': 'sample', 'recipients': 'sample', 'generated_at': '2026-09-03T10:00:00'}
    resp = client.post("/v1/reporting", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('reporting: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('reporting rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/reporting", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('reporting list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('reporting list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('reporting accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/reporting/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('reporting get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/reporting/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('reporting missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'access_scope': 'portfolio', 'principal': 'sample', 'reference': 'sample', 'role': 'management', 'school': 'sample', 'status': 'open', 'principal_email': 'guest@example.com', 'permissions': 'sample', 'granted_by': 'sample', 'effective_from': 'sample', 'last_review_at': '2026-09-03T10:00:00', 'active': 'sample', 'notes': 'sample'}
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

    payload = {'direction': 'inbound', 'entity_type': 'purchase_order', 'integration': 'erp', 'mode': 'placeholder', 'reference': 'sample', 'status': 'open', 'external_reference': 'sample', 'endpoint': 'sample', 'currency': 'sample', 'amount': 'sample', 'sync_state': 'not_implemented', 'last_sync_at': '2026-09-03T10:00:00', 'detail': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/erp_integration", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('erp_integration: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('erp_integration rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/erp_integration", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('erp_integration list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('erp_integration list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('erp_integration accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/erp_integration/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('erp_integration get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/erp_integration/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('erp_integration missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'booking_reference': 'sample', 'facility': 'sample', 'integration': 'booking_system', 'mode': 'placeholder', 'reference': 'sample', 'school': 'sample', 'slot_start': 'sample', 'status': 'open', 'slot_end': 'sample', 'requested_by': 'sample', 'sync_state': 'not_implemented', 'last_sync_at': '2026-09-03T10:00:00', 'detail': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/booking_system_integration", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('booking_system_integration: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('booking_system_integration rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/booking_system_integration", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('booking_system_integration list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('booking_system_integration list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('booking_system_integration accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/booking_system_integration/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('booking_system_integration get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/booking_system_integration/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('booking_system_integration missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    assert not failures, "; ".join(failures)
