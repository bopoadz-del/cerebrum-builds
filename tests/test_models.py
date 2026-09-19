"""Models must survive a round trip through sqlite."""

from app import store
from app.models import MODELS


#: Tenant the generated tests act as (the platform token's tenant).
TENANT = 'local'


def test_every_model_round_trips():
    record = {}
    saved = store.save('delivery_dispatch_tracking', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for delivery_dispatch_tracking'
    fetched = store.get('delivery_dispatch_tracking', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'delivery_dispatch_tracking did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('delivery_dispatch_tracking', tenant_id=TENANT))
    record = {}
    saved = store.save('document_knowledge_qa', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for document_knowledge_qa'
    fetched = store.get('document_knowledge_qa', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'document_knowledge_qa did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('document_knowledge_qa', tenant_id=TENANT))
    record = {}
    saved = store.save('fleet_cost_tracking', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for fleet_cost_tracking'
    fetched = store.get('fleet_cost_tracking', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'fleet_cost_tracking did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('fleet_cost_tracking', tenant_id=TENANT))
    record = {}
    saved = store.save('management_reporting_dashboard', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for management_reporting_dashboard'
    fetched = store.get('management_reporting_dashboard', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'management_reporting_dashboard did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('management_reporting_dashboard', tenant_id=TENANT))
    record = {}
    saved = store.save('procedures_readiness_and_audit_trail', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for procedures_readiness_and_audit_trail'
    fetched = store.get('procedures_readiness_and_audit_trail', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'procedures_readiness_and_audit_trail did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('procedures_readiness_and_audit_trail', tenant_id=TENANT))
    record = {}
    saved = store.save('product_pricing', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for product_pricing'
    fetched = store.get('product_pricing', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'product_pricing did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('product_pricing', tenant_id=TENANT))
    record = {}
    saved = store.save('stock_inventory_management', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for stock_inventory_management'
    fetched = store.get('stock_inventory_management', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'stock_inventory_management did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('stock_inventory_management', tenant_id=TENANT))
    record = {}
    saved = store.save('user_roles_workforce', record, tenant_id=TENANT)
    assert saved['id'] is not None, 'no id assigned for user_roles_workforce'
    fetched = store.get('user_roles_workforce', saved['id'], tenant_id=TENANT)
    assert fetched is not None, 'user_roles_workforce did not persist'
    for key, value in record.items():
        assert fetched[key] == value, (key, fetched[key], value)
    assert any(r['id'] == saved['id'] for r in store.list_all('user_roles_workforce', tenant_id=TENANT))


def test_models_expose_their_fields():
    assert MODELS, 'no models were generated'
    for cap_id, cls in MODELS.items():
        instance = cls.from_dict({})
        assert instance.to_dict()['id'] is None
        assert cls.FIELDS, cap_id
