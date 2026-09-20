"""Models must survive a round trip through sqlite."""

from app import store
from app.models import MODELS


#: Tenant the generated tests act as (the platform token's tenant).
TENANT = 'local'


def test_every_model_round_trips():
    record = {'audit': 'sample', 'capture': 'sample', 'evidence_verifier': 'sample', 'file_hasher': 'sample', 'reference': 'sample', 'status': 'open'}
    saved = store.save('audit_trail', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for audit_trail'
    fetched = store.get('audit_trail', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'audit_trail did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('audit_trail', tenant_id=TENANT))
    record = {'audit': 'sample', 'database': 'sample', 'reference': 'sample', 'status': 'open', 'storage': 'sample', 'mileage': 'sample'}
    saved = store.save('fleet_registry', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for fleet_registry'
    fetched = store.get('fleet_registry', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'fleet_registry did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('fleet_registry', tenant_id=TENANT))
    record = {'analytics': 'sample', 'audit': 'sample', 'database': 'sample', 'reference': 'sample', 'status': 'open', 'workflow': 'sample', 'amount_due': 'sample', 'deposit_held': 'sample', 'balance_due': 'sample'}
    saved = store.save('invoicing_and_deposits', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for invoicing_and_deposits'
    fetched = store.get('invoicing_and_deposits', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'invoicing_and_deposits did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('invoicing_and_deposits', tenant_id=TENANT))
    record = {'reference': 'sample', 'status': 'open', 'title': 'sample', 'schedule_kind': 'date', 'due_date': '2026-09-03', 'due_mileage': 'sample', 'downtime_days': 'sample', 'estimated_cost': 'sample'}
    saved = store.save('maintenance_scheduling', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for maintenance_scheduling'
    fetched = store.get('maintenance_scheduling', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'maintenance_scheduling did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('maintenance_scheduling', tenant_id=TENANT))
    record = {'analytics': 'sample', 'dashboard': 'sample', 'estate_registry': 'sample', 'portfolio_rollup': 'sample', 'reference': 'sample', 'status': 'open', 'fleet_utilisation': 'sample', 'revenue': 'sample', 'cost': 'sample'}
    saved = store.save('multi_branch_rollup', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for multi_branch_rollup'
    fetched = store.get('multi_branch_rollup', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'multi_branch_rollup did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('multi_branch_rollup', tenant_id=TENANT))
    record = {'analytics': 'sample', 'audit': 'sample', 'formula_executor': 'sample', 'reference': 'sample', 'status': 'open', 'validation': 'sample', 'duration_days': 'sample', 'base_rate': 'sample', 'mileage_charge': 'sample', 'fuel_charge': 'sample', 'late_return_charge': 'sample', 'extras_charge': 'sample', 'deposit_amount': 'sample'}
    saved = store.save('pricing_and_rate_cards', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for pricing_and_rate_cards'
    fetched = store.get('pricing_and_rate_cards', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'pricing_and_rate_cards did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('pricing_and_rate_cards', tenant_id=TENANT))
    record = {'reference': 'sample', 'status': 'open', 'pickup_date': '2026-09-03', 'return_date': '2026-09-03', 'extension_days': 'sample', 'daily_rate': 'sample', 'deposit_amount': 'sample'}
    saved = store.save('rental_contract_management', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for rental_contract_management'
    fetched = store.get('rental_contract_management', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'rental_contract_management did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('rental_contract_management', tenant_id=TENANT))
    record = {'analytics': 'sample', 'dashboard': 'sample', 'memory': 'sample', 'reference': 'sample', 'status': 'open', 'vector_search': 'sample', 'value': 'sample'}
    saved = store.save('reporting_analytics', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for reporting_analytics'
    fetched = store.get('reporting_analytics', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'reporting_analytics did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('reporting_analytics', tenant_id=TENANT))


def test_models_expose_their_fields():
    assert MODELS, 'no models were generated'
    for cap_id, cls in MODELS.items():
        instance = cls.from_dict({})
        assert instance.to_dict()['id'] is None
        assert cls.FIELDS, cap_id


def test_audit_reads_are_unscoped_while_caller_reads_are_not():
    """Two callers, two shapes, and the difference is the whole tenancy claim.

    The deployment's own audit read (the factory's one-record round-trip
    probe, scripts/acceptance.py) has no principal to resolve, so it omits
    the tenant and sees the table. Anything a request drives always names
    the principal's tenant, and another tenant's row then disappears —
    store.get answers None so the route can answer 404, never the record.
    """
    mine = store.save(
        "fleet_registry",
        {"reference": "audit-scope", "status": "open"},
        tenant_id="tenant-audit-a",
    )
    theirs = store.save(
        "fleet_registry",
        {"reference": "audit-scope", "status": "open"},
        tenant_id="tenant-audit-b",
    )
    everything = {row["id"] for row in store.list_all("fleet_registry")}
    assert {mine["id"], theirs["id"]} <= everything

    scoped = {row["id"] for row in store.list_all("fleet_registry", tenant_id="tenant-audit-a")}
    assert mine["id"] in scoped
    assert theirs["id"] not in scoped

    assert store.get("fleet_registry", mine["id"], "tenant-audit-b") is None
    assert store.get("fleet_registry", theirs["id"]) is not None
