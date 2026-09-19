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
    payload = {'budget_owner': 'sample', 'department': 'sample', 'reference': 'sample', 'status': 'open', 'cost_centre': 'sample', 'period': 'sample', 'planned_amount': 'sample', 'actual_amount': 'sample', 'currency': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/budget_planning_tracking", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('budget_planning_tracking: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('budget_planning_tracking: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('budget_planning_tracking: JSON body is not a dict')
            listed = client.get("/v1/budget_planning_tracking", headers=AUTH)
            if listed.status_code != 200:
                failures.append('budget_planning_tracking list: HTTP ' + str(listed.status_code))

    payload = {'category': 'software', 'department': 'sample', 'reference': 'sample', 'status': 'open', 'supplier': 'sample', 'amount': 'sample', 'currency': 'sample', 'invoice_date': '2026-09-03', 'invoice_number': 'sample', 'document_path': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/spend_capture_categorisation", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('spend_capture_categorisation: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('spend_capture_categorisation: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('spend_capture_categorisation: JSON body is not a dict')
            listed = client.get("/v1/spend_capture_categorisation", headers=AUTH)
            if listed.status_code != 200:
                failures.append('spend_capture_categorisation list: HTTP ' + str(listed.status_code))

    payload = {'approver': 'sample', 'department': 'sample', 'reference': 'sample', 'request_type': 'invoice', 'status': 'open', 'approver_email': 'guest@example.com', 'amount': 'sample', 'threshold': 'sample', 'priority': 'low', 'submitted_at': '2026-09-03T10:00:00', 'notes': 'sample'}
    resp = client.post("/v1/approval_workflow", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('approval_workflow: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('approval_workflow: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('approval_workflow: JSON body is not a dict')
            listed = client.get("/v1/approval_workflow", headers=AUTH)
            if listed.status_code != 200:
                failures.append('approval_workflow list: HTTP ' + str(listed.status_code))

    payload = {'department': 'sample', 'reference': 'sample', 'status': 'open', 'category': 'sample', 'period': 'sample', 'budget_amount': 'sample', 'actual_amount': 'sample', 'formula': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/variance_analytics", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('variance_analytics: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('variance_analytics: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('variance_analytics: JSON body is not a dict')
            listed = client.get("/v1/variance_analytics", headers=AUTH)
            if listed.status_code != 200:
                failures.append('variance_analytics list: HTTP ' + str(listed.status_code))

    payload = {'department': 'sample', 'reference': 'sample', 'role_view': 'cfo', 'status': 'open', 'view_scope': 'sample', 'period': 'sample', 'spend_total': 'sample', 'commitment_total': 'sample', 'forecast_total': 'sample', 'risk_level': 'low', 'notes': 'sample'}
    resp = client.post("/v1/dashboard_portfolio_rollup", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('dashboard_portfolio_rollup: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('dashboard_portfolio_rollup: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('dashboard_portfolio_rollup: JSON body is not a dict')
            listed = client.get("/v1/dashboard_portfolio_rollup", headers=AUTH)
            if listed.status_code != 200:
                failures.append('dashboard_portfolio_rollup list: HTTP ' + str(listed.status_code))

    payload = {'department': 'sample', 'record_reference': 'sample', 'record_type': 'invoice', 'reference': 'sample', 'status': 'open', 'evidence_hash': 'sample', 'verified': 'sample', 'checked_at': '2026-09-03T10:00:00', 'notes': 'sample'}
    resp = client.post("/v1/audit_evidence_validation", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('audit_evidence_validation: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('audit_evidence_validation: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('audit_evidence_validation: JSON body is not a dict')
            listed = client.get("/v1/audit_evidence_validation", headers=AUTH)
            if listed.status_code != 200:
                failures.append('audit_evidence_validation list: HTTP ' + str(listed.status_code))

    payload = {'department': 'sample', 'document_type': 'invoice', 'question': 'sample', 'reference': 'sample', 'status': 'open', 'answer': 'sample', 'citations': 'sample', 'confidence': 'sample', 'document_path': 'sample'}
    resp = client.post("/v1/finance_document_knowledge", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('finance_document_knowledge: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('finance_document_knowledge: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('finance_document_knowledge: JSON body is not a dict')
            listed = client.get("/v1/finance_document_knowledge", headers=AUTH)
            if listed.status_code != 200:
                failures.append('finance_document_knowledge list: HTTP ' + str(listed.status_code))

    payload = {'department': 'sample', 'direction': 'inbound', 'integration': 'google_drive', 'reference': 'sample', 'status': 'open', 'detail': 'sample', 'external_reference': 'sample', 'last_sync_at': '2026-09-03T10:00:00', 'notes': 'sample'}
    resp = client.post("/v1/integrations_placeholders", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('integrations_placeholders: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    else:
        try:
            body = resp.json()
        except Exception:
            failures.append('integrations_placeholders: response is not JSON')
        else:
            if not isinstance(body, dict):
                failures.append('integrations_placeholders: JSON body is not a dict')
            listed = client.get("/v1/integrations_placeholders", headers=AUTH)
            if listed.status_code != 200:
                failures.append('integrations_placeholders list: HTTP ' + str(listed.status_code))

    assert not failures, "; ".join(failures)


@pytest.mark.pilot
def test_every_capability_route_accepts_payload():
    """Pilot: spec payload is accepted (ok is not False) and persisted.
    Not the factory code-phase gate."""
    failures = []
    payload = {'budget_owner': 'sample', 'department': 'sample', 'reference': 'sample', 'status': 'open', 'cost_centre': 'sample', 'period': 'sample', 'planned_amount': 'sample', 'actual_amount': 'sample', 'currency': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/budget_planning_tracking", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('budget_planning_tracking: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('budget_planning_tracking rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/budget_planning_tracking", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('budget_planning_tracking list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('budget_planning_tracking list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('budget_planning_tracking accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/budget_planning_tracking/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('budget_planning_tracking get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/budget_planning_tracking/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('budget_planning_tracking missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'category': 'software', 'department': 'sample', 'reference': 'sample', 'status': 'open', 'supplier': 'sample', 'amount': 'sample', 'currency': 'sample', 'invoice_date': '2026-09-03', 'invoice_number': 'sample', 'document_path': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/spend_capture_categorisation", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('spend_capture_categorisation: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('spend_capture_categorisation rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/spend_capture_categorisation", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('spend_capture_categorisation list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('spend_capture_categorisation list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('spend_capture_categorisation accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/spend_capture_categorisation/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('spend_capture_categorisation get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/spend_capture_categorisation/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('spend_capture_categorisation missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'approver': 'sample', 'department': 'sample', 'reference': 'sample', 'request_type': 'invoice', 'status': 'open', 'approver_email': 'guest@example.com', 'amount': 'sample', 'threshold': 'sample', 'priority': 'low', 'submitted_at': '2026-09-03T10:00:00', 'notes': 'sample'}
    resp = client.post("/v1/approval_workflow", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('approval_workflow: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('approval_workflow rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/approval_workflow", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('approval_workflow list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('approval_workflow list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('approval_workflow accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/approval_workflow/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('approval_workflow get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/approval_workflow/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('approval_workflow missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'department': 'sample', 'reference': 'sample', 'status': 'open', 'category': 'sample', 'period': 'sample', 'budget_amount': 'sample', 'actual_amount': 'sample', 'formula': 'sample', 'notes': 'sample'}
    resp = client.post("/v1/variance_analytics", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('variance_analytics: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('variance_analytics rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/variance_analytics", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('variance_analytics list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('variance_analytics list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('variance_analytics accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/variance_analytics/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('variance_analytics get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/variance_analytics/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('variance_analytics missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'department': 'sample', 'reference': 'sample', 'role_view': 'cfo', 'status': 'open', 'view_scope': 'sample', 'period': 'sample', 'spend_total': 'sample', 'commitment_total': 'sample', 'forecast_total': 'sample', 'risk_level': 'low', 'notes': 'sample'}
    resp = client.post("/v1/dashboard_portfolio_rollup", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('dashboard_portfolio_rollup: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('dashboard_portfolio_rollup rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/dashboard_portfolio_rollup", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('dashboard_portfolio_rollup list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('dashboard_portfolio_rollup list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('dashboard_portfolio_rollup accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/dashboard_portfolio_rollup/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('dashboard_portfolio_rollup get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/dashboard_portfolio_rollup/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('dashboard_portfolio_rollup missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'department': 'sample', 'record_reference': 'sample', 'record_type': 'invoice', 'reference': 'sample', 'status': 'open', 'evidence_hash': 'sample', 'verified': 'sample', 'checked_at': '2026-09-03T10:00:00', 'notes': 'sample'}
    resp = client.post("/v1/audit_evidence_validation", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('audit_evidence_validation: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('audit_evidence_validation rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/audit_evidence_validation", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('audit_evidence_validation list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('audit_evidence_validation list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('audit_evidence_validation accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/audit_evidence_validation/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('audit_evidence_validation get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/audit_evidence_validation/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('audit_evidence_validation missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'department': 'sample', 'document_type': 'invoice', 'question': 'sample', 'reference': 'sample', 'status': 'open', 'answer': 'sample', 'citations': 'sample', 'confidence': 'sample', 'document_path': 'sample'}
    resp = client.post("/v1/finance_document_knowledge", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('finance_document_knowledge: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('finance_document_knowledge rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/finance_document_knowledge", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('finance_document_knowledge list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('finance_document_knowledge list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('finance_document_knowledge accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/finance_document_knowledge/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('finance_document_knowledge get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/finance_document_knowledge/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('finance_document_knowledge missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    payload = {'department': 'sample', 'direction': 'inbound', 'integration': 'google_drive', 'reference': 'sample', 'status': 'open', 'detail': 'sample', 'external_reference': 'sample', 'last_sync_at': '2026-09-03T10:00:00', 'notes': 'sample'}
    resp = client.post("/v1/integrations_placeholders", json=payload, headers=AUTH)
    if resp.status_code != 200:
        failures.append('integrations_placeholders: HTTP ' + str(resp.status_code) + ': ' + resp.text[:200])
    elif resp.json().get("ok") is False:
        failures.append('integrations_placeholders rejected a payload built from its own schema: ' + str(resp.json().get('error')))
    else:
        listed = client.get("/v1/integrations_placeholders", headers=AUTH)
        listed_body = listed.json() if listed.content else {}
        if listed.status_code != 200:
            failures.append('integrations_placeholders list: HTTP ' + str(listed.status_code))
        elif isinstance(listed_body, dict) and listed_body.get("ok") is False:
            failures.append('integrations_placeholders list refused: ' + str(listed_body.get('error') or listed_body)[:200])
        else:
            rows = _listed(listed_body)
            if not rows:
                failures.append('integrations_placeholders accepted a record but persisted nothing')
            else:
                item_id = rows[0].get("id")
                got = client.get(f"/v1/integrations_placeholders/{item_id}", headers=AUTH)
                if got.status_code != 200:
                    failures.append('integrations_placeholders get: HTTP ' + str(got.status_code))
                missing = client.get("/v1/integrations_placeholders/999999", headers=AUTH)
                if missing.status_code != 404:
                    failures.append('integrations_placeholders missing id: HTTP ' + str(missing.status_code) + ' (expected 404)')

    assert not failures, "; ".join(failures)
