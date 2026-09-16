"""Kernel job descriptions shipped with this platform.

Frozen at manufacture time from Factory RoleContract. HTTP routes
publish each kernel's job; they never re-run that job. Inventory and
provenance read lock/provenance files live so the register stays true
to the checkout.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

JOBS = [{'kernel': 'COLLECTOR', 'title': 'Binding surveyor', 'mandate': "Emit intake_blueprint.v1 (COLLECTOR output IS that object — vertical, capabilities with customer words + normalized id, roles/users, data sources, integrations, constraints, done_when, each field carrying the chat turn it came from). Resolve each capability's declared block ids into harvestable contracts. Name every capability with no block as an explicit gap so the WRITER authors that logic — never drop it from the plan. Consult the coding agent for a report-only endorse/mismatch review of each binding. Do not invent block ids, do not mutate the plan, and write nothing.", 'agent': 'consult', 'http_routes': ['GET /v1/catalog'], 'gate': 'every referenced block id is dual-registered; gaps enumerated', 'read_only': True}, {'kernel': 'CLONER', 'title': 'Block stocker', 'mandate': "Vendor each resolved block's source at a pinned commit, plus the local dispatch runtime those shims stand on, plus the kit packs the Factory shelf assigns those blocks to, so handlers import blocks instead of calling the store over HTTP. Write only vendor/**, kits/**, and blocks.lock.json. Exact answers — no agent.", 'agent': 'none', 'http_routes': ['GET /v1/inventory'], 'gate': 'every vendored block imports with no network configured', 'read_only': False}, {'kernel': 'WRITER', 'title': 'Platform manufacturer', 'mandate': "Manufacture the platform over the vendored stock: capability handlers, domain models, persistence, the HTTP surface (including each kernel's job routes), UI wiring, and GENERATE logic for the gaps the collector reported. The coding agent writes those artifacts inside WRITER lanes. Do not touch tests/ or vendor/.", 'agent': 'manufacture', 'http_routes': ['GET /v1/capabilities', 'POST /v1/{capability}', 'GET /v1/{capability}', 'GET /v1/{capability}/{id}', 'PUT /v1/{capability}/{id}', 'DELETE /v1/{capability}/{id}', 'POST /v1/work_queue', 'POST /v1/work_queue/{id}/process', 'GET /v1/work_queue'], 'gate': 'workspace imports and type-checks clean', 'read_only': False}, {'kernel': 'TESTER', 'title': 'Acceptance inspector', 'mandate': "Write and run the code-phase suite against what the WRITER produced (imports, dispatch load, models, routes answer JSON, handle() returns a mapping) and bounce those failures for another writer pass. Store-backed execute-all is pilot coverage, not this gate. The harness's acceptance IS the tester — do not consult the coding agent for extra cases. Never patch app/. Never run the suite over HTTP — GET /v1/gates describes coverage only.", 'agent': 'none', 'http_routes': ['GET /v1/gates'], 'gate': "code-phase suite green (pytest -m 'not pilot')", 'read_only': False}, {'kernel': 'STORE_MANAGER', 'title': 'Store registrar', 'mandate': "Keep the store's books: register what this platform cloned and at which commit. This minimal form records the clone register and applies no store op. Harvesting improvements back upstream and admitting client-driven net-new capability remain unbuilt. Exact answers — no agent.", 'agent': 'none', 'http_routes': ['GET /v1/provenance'], 'gate': 'store_manager.assert_store_op_allowed passes for every op applied', 'read_only': False}]
CATALOG = {'kernel': 'COLLECTOR', 'title': 'Binding surveyor', 'mandate': "Emit intake_blueprint.v1 (COLLECTOR output IS that object — vertical, capabilities with customer words + normalized id, roles/users, data sources, integrations, constraints, done_when, each field carrying the chat turn it came from). Resolve each capability's declared block ids into harvestable contracts. Name every capability with no block as an explicit gap so the WRITER authors that logic — never drop it from the plan. Consult the coding agent for a report-only endorse/mismatch review of each binding. Do not invent block ids, do not mutate the plan, and write nothing.", 'agent': 'consult', 'gaps': [], 'bindings': [{'capability_id': 'inventory_management', 'block_ids': ['database', 'workflow', 'notification', 'validation'], 'gap': False}, {'capability_id': 'sales_and_orders', 'block_ids': ['database', 'event_bus', 'workflow', 'queue'], 'gap': False}, {'capability_id': 'customer_insights', 'block_ids': ['database', 'analytics', 'vector_search', 'knowledge'], 'gap': False}, {'capability_id': 'analytics_dashboard', 'block_ids': ['dashboard', 'analytics', 'portfolio_rollup', 'storage'], 'gap': False}, {'capability_id': 'supplier_and_purchasing', 'block_ids': ['database', 'workflow', 'recommendation_template', 'notification'], 'gap': False}, {'capability_id': 'omnichannel_integration', 'block_ids': ['event_bus', 'workflow', 'queue', 'knowledge'], 'gap': False}, {'capability_id': 'compliance_and_audit', 'block_ids': ['audit', 'validation', 'file_hasher', 'evidence_verifier'], 'gap': False}], 'agent_reviews': [], 'agent_model': '', 'resolved_blocks': ['analytics', 'audit', 'dashboard', 'database', 'event_bus', 'evidence_verifier', 'file_hasher', 'knowledge', 'notification', 'portfolio_rollup', 'queue', 'recommendation_template', 'storage', 'validation', 'vector_search', 'workflow']}
CAPABILITIES = [{'id': 'inventory_management', 'entity': 'inventory_management', 'source': 'kernel execute_action template', 'http': {'create': 'POST /v1/inventory_management', 'list': 'GET /v1/inventory_management', 'get': 'GET /v1/inventory_management/{id}', 'update': 'PUT /v1/inventory_management/{id}', 'delete': 'DELETE /v1/inventory_management/{id}'}}, {'id': 'sales_and_orders', 'entity': 'sales_and_orders', 'source': 'kernel execute_action template', 'http': {'create': 'POST /v1/sales_and_orders', 'list': 'GET /v1/sales_and_orders', 'get': 'GET /v1/sales_and_orders/{id}', 'update': 'PUT /v1/sales_and_orders/{id}', 'delete': 'DELETE /v1/sales_and_orders/{id}'}}, {'id': 'customer_insights', 'entity': 'customer_insights', 'source': 'kernel execute_action template', 'http': {'create': 'POST /v1/customer_insights', 'list': 'GET /v1/customer_insights', 'get': 'GET /v1/customer_insights/{id}', 'update': 'PUT /v1/customer_insights/{id}', 'delete': 'DELETE /v1/customer_insights/{id}'}}, {'id': 'analytics_dashboard', 'entity': 'analytics_dashboard', 'source': 'kernel execute_action template', 'http': {'create': 'POST /v1/analytics_dashboard', 'list': 'GET /v1/analytics_dashboard', 'get': 'GET /v1/analytics_dashboard/{id}', 'update': 'PUT /v1/analytics_dashboard/{id}', 'delete': 'DELETE /v1/analytics_dashboard/{id}'}}, {'id': 'supplier_and_purchasing', 'entity': 'supplier_and_purchasing', 'source': 'kernel execute_action template', 'http': {'create': 'POST /v1/supplier_and_purchasing', 'list': 'GET /v1/supplier_and_purchasing', 'get': 'GET /v1/supplier_and_purchasing/{id}', 'update': 'PUT /v1/supplier_and_purchasing/{id}', 'delete': 'DELETE /v1/supplier_and_purchasing/{id}'}}, {'id': 'omnichannel_integration', 'entity': 'omnichannel_integration', 'source': 'kernel execute_action template', 'http': {'create': 'POST /v1/omnichannel_integration', 'list': 'GET /v1/omnichannel_integration', 'get': 'GET /v1/omnichannel_integration/{id}', 'update': 'PUT /v1/omnichannel_integration/{id}', 'delete': 'DELETE /v1/omnichannel_integration/{id}'}}, {'id': 'compliance_and_audit', 'entity': 'compliance_and_audit', 'source': 'kernel execute_action template', 'http': {'create': 'POST /v1/compliance_and_audit', 'list': 'GET /v1/compliance_and_audit', 'get': 'GET /v1/compliance_and_audit/{id}', 'update': 'PUT /v1/compliance_and_audit/{id}', 'delete': 'DELETE /v1/compliance_and_audit/{id}'}}]
GATES = {'kernel': 'TESTER', 'title': 'Acceptance inspector', 'mandate': "Write and run the code-phase suite against what the WRITER produced (imports, dispatch load, models, routes answer JSON, handle() returns a mapping) and bounce those failures for another writer pass. Store-backed execute-all is pilot coverage, not this gate. The harness's acceptance IS the tester — do not consult the coding agent for extra cases. Never patch app/. Never run the suite over HTTP — GET /v1/gates describes coverage only.", 'agent': 'none', 'runs_over_http': False, 'suite': [{'file': 'tests/test_smoke.py', 'covers': 'import, offline dispatch load, handle() returns a mapping', 'gated': True}, {'file': 'tests/test_smoke.py', 'covers': 'Store-backed handle() ok and nested error scan', 'marker': 'pilot', 'gated': False}, {'file': 'tests/test_models.py', 'covers': 'sqlite round-trip via store.save / store.get', 'gated': True}, {'file': 'tests/test_data_lifecycle.py', 'covers': 'Alembic up/down on populated v1, restore drill, parallel writes', 'gated': True}, {'file': 'tests/test_deploy.py', 'covers': 'Fail-closed /health, correlation logs, revision rollback identity', 'gated': True}, {'file': 'tests/test_domain_acceptance.py', 'covers': 'Ten business outcomes through execute_action', 'marker': 'pilot', 'gated': False}, {'file': 'tests/test_routes.py', 'covers': 'HTTP 200 JSON for /health, kernel jobs, and each capability POST', 'gated': True}, {'file': 'tests/test_routes.py', 'covers': 'Store-backed POST accepted (ok is not False) and persisted', 'marker': 'pilot', 'gated': False}, {'file': 'tests/agent_domain_cases.py', 'covers': 'optional coding-agent domain mutations of spec payloads', 'optional': True, 'gated': False}]}


def _read_workspace_json(relative: str) -> Optional[Dict[str, Any]]:
    path = Path(__file__).resolve().parents[1] / relative
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _job(kernel: str) -> Dict[str, Any]:
    for item in JOBS:
        if item['kernel'] == kernel:
            return dict(item)
    return {'kernel': kernel}


def inventory() -> Dict[str, Any]:
    payload = _job('CLONER')
    payload['lock'] = _read_workspace_json('blocks.lock.json') or {
        'schema': 'blocks.lock.v1',
        'blocks': {},
    }
    return payload


def provenance() -> Dict[str, Any]:
    payload = _job('STORE_MANAGER')
    payload['build'] = _read_workspace_json('docs/build_provenance.json') or {}
    lock = _read_workspace_json('blocks.lock.json') or {}
    payload['clones'] = lock.get('blocks') or {}
    payload['store_ops'] = []
    return payload
