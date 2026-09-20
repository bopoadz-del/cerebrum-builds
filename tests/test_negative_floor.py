"""Counter-cases: what each capability REFUSES.

Written by the factory TESTER role. The floor (negative_floor) requires four
per capability; these four are derived from each capability's own spec. Add
the domain cases the brief implies -- the boundary of a rule, a state machine
that must not skip a step -- they count toward the same floor.
"""

import os

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer " + os.environ.get("PLATFORM_TOKEN", "dev-local-token")}
OTHER_TENANT = {
    "Authorization": "Bearer " + os.environ.get("PLATFORM_TOKEN_B", "dev-local-token-b")
}

REFUSED = (400, 403, 404, 409, 422)


def _refused(response):
    """A refusal, by status or by the envelope's own ok:false."""
    if response.status_code in REFUSED:
        return True
    if response.status_code != 200:
        return False
    try:
        body = response.json()
    except Exception:
        return False
    return isinstance(body, dict) and body.get("ok") is False



# -- audit_trail -------------------------------------------------


def test_audit_trail_refuses_a_missing_required_field():
    """A partial record is refused, never completed by the handler."""
    body = {'capture': 'sample', 'evidence_verifier': 'sample', 'file_hasher': 'sample', 'reference': 'sample', 'status': 'open'}
    resp = client.post("/v1/audit_trail", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "audit_trail accepted a payload with no audit: " + resp.text[:200]
    )


def test_audit_trail_refuses_a_value_outside_its_vocabulary():
    """A column that accepts any string is not that column."""
    body = {'audit': 'sample', 'capture': 'sample', 'evidence_verifier': 'sample', 'file_hasher': 'sample', 'reference': 'sample', 'status': 'not-a-declared-value'}
    resp = client.post("/v1/audit_trail", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "audit_trail accepted an undeclared status: " + resp.text[:200]
    )


def test_audit_trail_does_not_leak_across_tenants():
    """404, never 403 and never the row: existence itself is private."""
    body = {'audit': 'sample', 'capture': 'sample', 'evidence_verifier': 'sample', 'file_hasher': 'sample', 'reference': 'sample', 'status': 'open'}
    made = client.post("/v1/audit_trail", json=body, headers=AUTH)
    if made.status_code != 200:
        pytest.skip("capability did not accept the sample record")
    try:
        record = made.json()
    except Exception:
        pytest.skip("capability did not answer JSON")
    rid = (record.get("id") or (record.get("result") or {}).get("id")
           if isinstance(record, dict) else None)
    if not rid:
        pytest.skip("capability returned no record id to read back")
    other = client.get("/v1/audit_trail/" + str(rid), headers=OTHER_TENANT)
    assert other.status_code == 404, (
        "audit_trail answered %s to another tenant, not 404" % other.status_code
    )


def test_audit_trail_refuses_a_malformed_payload():
    """Garbage in is a refusal, never a 500 and never a stored row."""
    for junk in ([], "", {"": None}, {"x" * 300: "y" * 2000}):
        resp = client.post("/v1/audit_trail", json=junk, headers=AUTH)
        assert resp.status_code != 500, (
            "audit_trail raised on malformed input: " + resp.text[:200]
        )
        assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
            "audit_trail accepted malformed input %r" % (junk,)
        )


# -- fleet_registry ----------------------------------------------


def test_fleet_registry_refuses_a_missing_required_field():
    """A partial record is refused, never completed by the handler."""
    body = {'database': 'sample', 'reference': 'sample', 'status': 'open', 'storage': 'sample', 'mileage': 'sample'}
    resp = client.post("/v1/fleet_registry", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "fleet_registry accepted a payload with no audit: " + resp.text[:200]
    )


def test_fleet_registry_refuses_a_value_outside_its_vocabulary():
    """A column that accepts any string is not that column."""
    body = {'audit': 'sample', 'database': 'sample', 'reference': 'sample', 'status': 'not-a-declared-value', 'storage': 'sample', 'mileage': 'sample'}
    resp = client.post("/v1/fleet_registry", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "fleet_registry accepted an undeclared status: " + resp.text[:200]
    )


def test_fleet_registry_does_not_leak_across_tenants():
    """404, never 403 and never the row: existence itself is private."""
    body = {'audit': 'sample', 'database': 'sample', 'reference': 'sample', 'status': 'open', 'storage': 'sample', 'mileage': 'sample'}
    made = client.post("/v1/fleet_registry", json=body, headers=AUTH)
    if made.status_code != 200:
        pytest.skip("capability did not accept the sample record")
    try:
        record = made.json()
    except Exception:
        pytest.skip("capability did not answer JSON")
    rid = (record.get("id") or (record.get("result") or {}).get("id")
           if isinstance(record, dict) else None)
    if not rid:
        pytest.skip("capability returned no record id to read back")
    other = client.get("/v1/fleet_registry/" + str(rid), headers=OTHER_TENANT)
    assert other.status_code == 404, (
        "fleet_registry answered %s to another tenant, not 404" % other.status_code
    )


def test_fleet_registry_refuses_a_malformed_payload():
    """Garbage in is a refusal, never a 500 and never a stored row."""
    for junk in ([], "", {"": None}, {"x" * 300: "y" * 2000}):
        resp = client.post("/v1/fleet_registry", json=junk, headers=AUTH)
        assert resp.status_code != 500, (
            "fleet_registry raised on malformed input: " + resp.text[:200]
        )
        assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
            "fleet_registry accepted malformed input %r" % (junk,)
        )


# -- invoicing_and_deposits --------------------------------------


def test_invoicing_and_deposits_refuses_a_missing_required_field():
    """A partial record is refused, never completed by the handler."""
    body = {'audit': 'sample', 'database': 'sample', 'reference': 'sample', 'status': 'open', 'workflow': 'sample', 'amount_due': 'sample', 'deposit_held': 'sample', 'balance_due': 'sample'}
    resp = client.post("/v1/invoicing_and_deposits", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "invoicing_and_deposits accepted a payload with no analytics: " + resp.text[:200]
    )


def test_invoicing_and_deposits_refuses_a_value_outside_its_vocabulary():
    """A column that accepts any string is not that column."""
    body = {'analytics': 'sample', 'audit': 'sample', 'database': 'sample', 'reference': 'sample', 'status': 'not-a-declared-value', 'workflow': 'sample', 'amount_due': 'sample', 'deposit_held': 'sample', 'balance_due': 'sample'}
    resp = client.post("/v1/invoicing_and_deposits", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "invoicing_and_deposits accepted an undeclared status: " + resp.text[:200]
    )


def test_invoicing_and_deposits_does_not_leak_across_tenants():
    """404, never 403 and never the row: existence itself is private."""
    body = {'analytics': 'sample', 'audit': 'sample', 'database': 'sample', 'reference': 'sample', 'status': 'open', 'workflow': 'sample', 'amount_due': 'sample', 'deposit_held': 'sample', 'balance_due': 'sample'}
    made = client.post("/v1/invoicing_and_deposits", json=body, headers=AUTH)
    if made.status_code != 200:
        pytest.skip("capability did not accept the sample record")
    try:
        record = made.json()
    except Exception:
        pytest.skip("capability did not answer JSON")
    rid = (record.get("id") or (record.get("result") or {}).get("id")
           if isinstance(record, dict) else None)
    if not rid:
        pytest.skip("capability returned no record id to read back")
    other = client.get("/v1/invoicing_and_deposits/" + str(rid), headers=OTHER_TENANT)
    assert other.status_code == 404, (
        "invoicing_and_deposits answered %s to another tenant, not 404" % other.status_code
    )


def test_invoicing_and_deposits_refuses_a_malformed_payload():
    """Garbage in is a refusal, never a 500 and never a stored row."""
    for junk in ([], "", {"": None}, {"x" * 300: "y" * 2000}):
        resp = client.post("/v1/invoicing_and_deposits", json=junk, headers=AUTH)
        assert resp.status_code != 500, (
            "invoicing_and_deposits raised on malformed input: " + resp.text[:200]
        )
        assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
            "invoicing_and_deposits accepted malformed input %r" % (junk,)
        )


# -- maintenance_scheduling --------------------------------------


def test_maintenance_scheduling_refuses_a_missing_required_field():
    """A partial record is refused, never completed by the handler."""
    body = {'status': 'open', 'title': 'sample', 'schedule_kind': 'date', 'due_date': '2026-09-03', 'due_mileage': 'sample', 'downtime_days': 'sample', 'estimated_cost': 'sample'}
    resp = client.post("/v1/maintenance_scheduling", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "maintenance_scheduling accepted a payload with no reference: " + resp.text[:200]
    )


def test_maintenance_scheduling_refuses_a_value_outside_its_vocabulary():
    """A column that accepts any string is not that column."""
    body = {'reference': 'sample', 'status': 'not-a-declared-value', 'title': 'sample', 'schedule_kind': 'date', 'due_date': '2026-09-03', 'due_mileage': 'sample', 'downtime_days': 'sample', 'estimated_cost': 'sample'}
    resp = client.post("/v1/maintenance_scheduling", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "maintenance_scheduling accepted an undeclared status: " + resp.text[:200]
    )


def test_maintenance_scheduling_does_not_leak_across_tenants():
    """404, never 403 and never the row: existence itself is private."""
    body = {'reference': 'sample', 'status': 'open', 'title': 'sample', 'schedule_kind': 'date', 'due_date': '2026-09-03', 'due_mileage': 'sample', 'downtime_days': 'sample', 'estimated_cost': 'sample'}
    made = client.post("/v1/maintenance_scheduling", json=body, headers=AUTH)
    if made.status_code != 200:
        pytest.skip("capability did not accept the sample record")
    try:
        record = made.json()
    except Exception:
        pytest.skip("capability did not answer JSON")
    rid = (record.get("id") or (record.get("result") or {}).get("id")
           if isinstance(record, dict) else None)
    if not rid:
        pytest.skip("capability returned no record id to read back")
    other = client.get("/v1/maintenance_scheduling/" + str(rid), headers=OTHER_TENANT)
    assert other.status_code == 404, (
        "maintenance_scheduling answered %s to another tenant, not 404" % other.status_code
    )


def test_maintenance_scheduling_refuses_a_malformed_payload():
    """Garbage in is a refusal, never a 500 and never a stored row."""
    for junk in ([], "", {"": None}, {"x" * 300: "y" * 2000}):
        resp = client.post("/v1/maintenance_scheduling", json=junk, headers=AUTH)
        assert resp.status_code != 500, (
            "maintenance_scheduling raised on malformed input: " + resp.text[:200]
        )
        assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
            "maintenance_scheduling accepted malformed input %r" % (junk,)
        )


# -- multi_branch_rollup -----------------------------------------


def test_multi_branch_rollup_refuses_a_missing_required_field():
    """A partial record is refused, never completed by the handler."""
    body = {'dashboard': 'sample', 'estate_registry': 'sample', 'portfolio_rollup': 'sample', 'reference': 'sample', 'status': 'open', 'fleet_utilisation': 'sample', 'revenue': 'sample', 'cost': 'sample'}
    resp = client.post("/v1/multi_branch_rollup", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "multi_branch_rollup accepted a payload with no analytics: " + resp.text[:200]
    )


def test_multi_branch_rollup_refuses_a_value_outside_its_vocabulary():
    """A column that accepts any string is not that column."""
    body = {'analytics': 'sample', 'dashboard': 'sample', 'estate_registry': 'sample', 'portfolio_rollup': 'sample', 'reference': 'sample', 'status': 'not-a-declared-value', 'fleet_utilisation': 'sample', 'revenue': 'sample', 'cost': 'sample'}
    resp = client.post("/v1/multi_branch_rollup", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "multi_branch_rollup accepted an undeclared status: " + resp.text[:200]
    )


def test_multi_branch_rollup_does_not_leak_across_tenants():
    """404, never 403 and never the row: existence itself is private."""
    body = {'analytics': 'sample', 'dashboard': 'sample', 'estate_registry': 'sample', 'portfolio_rollup': 'sample', 'reference': 'sample', 'status': 'open', 'fleet_utilisation': 'sample', 'revenue': 'sample', 'cost': 'sample'}
    made = client.post("/v1/multi_branch_rollup", json=body, headers=AUTH)
    if made.status_code != 200:
        pytest.skip("capability did not accept the sample record")
    try:
        record = made.json()
    except Exception:
        pytest.skip("capability did not answer JSON")
    rid = (record.get("id") or (record.get("result") or {}).get("id")
           if isinstance(record, dict) else None)
    if not rid:
        pytest.skip("capability returned no record id to read back")
    other = client.get("/v1/multi_branch_rollup/" + str(rid), headers=OTHER_TENANT)
    assert other.status_code == 404, (
        "multi_branch_rollup answered %s to another tenant, not 404" % other.status_code
    )


def test_multi_branch_rollup_refuses_a_malformed_payload():
    """Garbage in is a refusal, never a 500 and never a stored row."""
    for junk in ([], "", {"": None}, {"x" * 300: "y" * 2000}):
        resp = client.post("/v1/multi_branch_rollup", json=junk, headers=AUTH)
        assert resp.status_code != 500, (
            "multi_branch_rollup raised on malformed input: " + resp.text[:200]
        )
        assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
            "multi_branch_rollup accepted malformed input %r" % (junk,)
        )


# -- pricing_and_rate_cards --------------------------------------


def test_pricing_and_rate_cards_refuses_a_missing_required_field():
    """A partial record is refused, never completed by the handler."""
    body = {'audit': 'sample', 'formula_executor': 'sample', 'reference': 'sample', 'status': 'open', 'validation': 'sample', 'duration_days': 'sample', 'base_rate': 'sample', 'mileage_charge': 'sample', 'fuel_charge': 'sample', 'late_return_charge': 'sample', 'extras_charge': 'sample', 'deposit_amount': 'sample'}
    resp = client.post("/v1/pricing_and_rate_cards", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "pricing_and_rate_cards accepted a payload with no analytics: " + resp.text[:200]
    )


def test_pricing_and_rate_cards_refuses_a_value_outside_its_vocabulary():
    """A column that accepts any string is not that column."""
    body = {'analytics': 'sample', 'audit': 'sample', 'formula_executor': 'sample', 'reference': 'sample', 'status': 'not-a-declared-value', 'validation': 'sample', 'duration_days': 'sample', 'base_rate': 'sample', 'mileage_charge': 'sample', 'fuel_charge': 'sample', 'late_return_charge': 'sample', 'extras_charge': 'sample', 'deposit_amount': 'sample'}
    resp = client.post("/v1/pricing_and_rate_cards", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "pricing_and_rate_cards accepted an undeclared status: " + resp.text[:200]
    )


def test_pricing_and_rate_cards_does_not_leak_across_tenants():
    """404, never 403 and never the row: existence itself is private."""
    body = {'analytics': 'sample', 'audit': 'sample', 'formula_executor': 'sample', 'reference': 'sample', 'status': 'open', 'validation': 'sample', 'duration_days': 'sample', 'base_rate': 'sample', 'mileage_charge': 'sample', 'fuel_charge': 'sample', 'late_return_charge': 'sample', 'extras_charge': 'sample', 'deposit_amount': 'sample'}
    made = client.post("/v1/pricing_and_rate_cards", json=body, headers=AUTH)
    if made.status_code != 200:
        pytest.skip("capability did not accept the sample record")
    try:
        record = made.json()
    except Exception:
        pytest.skip("capability did not answer JSON")
    rid = (record.get("id") or (record.get("result") or {}).get("id")
           if isinstance(record, dict) else None)
    if not rid:
        pytest.skip("capability returned no record id to read back")
    other = client.get("/v1/pricing_and_rate_cards/" + str(rid), headers=OTHER_TENANT)
    assert other.status_code == 404, (
        "pricing_and_rate_cards answered %s to another tenant, not 404" % other.status_code
    )


def test_pricing_and_rate_cards_refuses_a_malformed_payload():
    """Garbage in is a refusal, never a 500 and never a stored row."""
    for junk in ([], "", {"": None}, {"x" * 300: "y" * 2000}):
        resp = client.post("/v1/pricing_and_rate_cards", json=junk, headers=AUTH)
        assert resp.status_code != 500, (
            "pricing_and_rate_cards raised on malformed input: " + resp.text[:200]
        )
        assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
            "pricing_and_rate_cards accepted malformed input %r" % (junk,)
        )


# -- rental_contract_management ----------------------------------


def test_rental_contract_management_refuses_a_missing_required_field():
    """A partial record is refused, never completed by the handler."""
    body = {'status': 'open', 'pickup_date': '2026-09-03', 'return_date': '2026-09-03', 'extension_days': 'sample', 'daily_rate': 'sample', 'deposit_amount': 'sample'}
    resp = client.post("/v1/rental_contract_management", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "rental_contract_management accepted a payload with no reference: " + resp.text[:200]
    )


def test_rental_contract_management_refuses_a_value_outside_its_vocabulary():
    """A column that accepts any string is not that column."""
    body = {'reference': 'sample', 'status': 'not-a-declared-value', 'pickup_date': '2026-09-03', 'return_date': '2026-09-03', 'extension_days': 'sample', 'daily_rate': 'sample', 'deposit_amount': 'sample'}
    resp = client.post("/v1/rental_contract_management", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "rental_contract_management accepted an undeclared status: " + resp.text[:200]
    )


def test_rental_contract_management_does_not_leak_across_tenants():
    """404, never 403 and never the row: existence itself is private."""
    body = {'reference': 'sample', 'status': 'open', 'pickup_date': '2026-09-03', 'return_date': '2026-09-03', 'extension_days': 'sample', 'daily_rate': 'sample', 'deposit_amount': 'sample'}
    made = client.post("/v1/rental_contract_management", json=body, headers=AUTH)
    if made.status_code != 200:
        pytest.skip("capability did not accept the sample record")
    try:
        record = made.json()
    except Exception:
        pytest.skip("capability did not answer JSON")
    rid = (record.get("id") or (record.get("result") or {}).get("id")
           if isinstance(record, dict) else None)
    if not rid:
        pytest.skip("capability returned no record id to read back")
    other = client.get("/v1/rental_contract_management/" + str(rid), headers=OTHER_TENANT)
    assert other.status_code == 404, (
        "rental_contract_management answered %s to another tenant, not 404" % other.status_code
    )


def test_rental_contract_management_refuses_a_malformed_payload():
    """Garbage in is a refusal, never a 500 and never a stored row."""
    for junk in ([], "", {"": None}, {"x" * 300: "y" * 2000}):
        resp = client.post("/v1/rental_contract_management", json=junk, headers=AUTH)
        assert resp.status_code != 500, (
            "rental_contract_management raised on malformed input: " + resp.text[:200]
        )
        assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
            "rental_contract_management accepted malformed input %r" % (junk,)
        )


# -- reporting_analytics -----------------------------------------


def test_reporting_analytics_refuses_a_missing_required_field():
    """A partial record is refused, never completed by the handler."""
    body = {'dashboard': 'sample', 'memory': 'sample', 'reference': 'sample', 'status': 'open', 'vector_search': 'sample', 'value': 'sample'}
    resp = client.post("/v1/reporting_analytics", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "reporting_analytics accepted a payload with no analytics: " + resp.text[:200]
    )


def test_reporting_analytics_refuses_a_value_outside_its_vocabulary():
    """A column that accepts any string is not that column."""
    body = {'analytics': 'sample', 'dashboard': 'sample', 'memory': 'sample', 'reference': 'sample', 'status': 'not-a-declared-value', 'vector_search': 'sample', 'value': 'sample'}
    resp = client.post("/v1/reporting_analytics", json=body, headers=AUTH)
    assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
        "reporting_analytics accepted an undeclared status: " + resp.text[:200]
    )


def test_reporting_analytics_does_not_leak_across_tenants():
    """404, never 403 and never the row: existence itself is private."""
    body = {'analytics': 'sample', 'dashboard': 'sample', 'memory': 'sample', 'reference': 'sample', 'status': 'open', 'vector_search': 'sample', 'value': 'sample'}
    made = client.post("/v1/reporting_analytics", json=body, headers=AUTH)
    if made.status_code != 200:
        pytest.skip("capability did not accept the sample record")
    try:
        record = made.json()
    except Exception:
        pytest.skip("capability did not answer JSON")
    rid = (record.get("id") or (record.get("result") or {}).get("id")
           if isinstance(record, dict) else None)
    if not rid:
        pytest.skip("capability returned no record id to read back")
    other = client.get("/v1/reporting_analytics/" + str(rid), headers=OTHER_TENANT)
    assert other.status_code == 404, (
        "reporting_analytics answered %s to another tenant, not 404" % other.status_code
    )


def test_reporting_analytics_refuses_a_malformed_payload():
    """Garbage in is a refusal, never a 500 and never a stored row."""
    for junk in ([], "", {"": None}, {"x" * 300: "y" * 2000}):
        resp = client.post("/v1/reporting_analytics", json=junk, headers=AUTH)
        assert resp.status_code != 500, (
            "reporting_analytics raised on malformed input: " + resp.text[:200]
        )
        assert resp.status_code in (400, 403, 404, 409, 422) or _refused(resp), (
            "reporting_analytics accepted malformed input %r" % (junk,)
        )
