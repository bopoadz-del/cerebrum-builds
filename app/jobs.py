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
CATALOG = {'kernel': 'COLLECTOR', 'title': 'Binding surveyor', 'mandate': 'Emit intake_blueprint.v1 and resolve declared block ids.', 'resolved_blocks': ['analytics', 'audit', 'capture', 'dashboard', 'database', 'document_engine', 'estate_maintenance', 'estate_registry', 'event_bus', 'evidence_verifier', 'file_hasher', 'formula_executor', 'knowledge', 'memory', 'notification', 'portfolio_rollup', 'queue', 'readiness_engine', 'storage', 'validation', 'vector_search', 'workflow'], 'gaps': [], 'bindings': [{'capability_id': 'fleet_registry', 'block_ids': ['database', 'knowledge', 'document_engine', 'storage', 'audit'], 'gap': False}, {'capability_id': 'rental_contract_management', 'block_ids': ['workflow', 'validation', 'event_bus', 'queue', 'audit', 'notification'], 'gap': False}, {'capability_id': 'maintenance_scheduling', 'block_ids': ['estate_maintenance', 'readiness_engine', 'notification', 'analytics', 'audit'], 'gap': False}, {'capability_id': 'pricing_and_rate_cards', 'block_ids': ['formula_executor', 'validation', 'audit', 'analytics'], 'gap': False}, {'capability_id': 'invoicing_and_deposits', 'block_ids': ['database', 'workflow', 'analytics', 'audit', 'notification'], 'gap': False}, {'capability_id': 'multi_branch_rollup', 'block_ids': ['portfolio_rollup', 'dashboard', 'analytics', 'estate_registry'], 'gap': False}, {'capability_id': 'reporting_analytics', 'block_ids': ['analytics', 'dashboard', 'memory', 'vector_search'], 'gap': False}, {'capability_id': 'audit_trail', 'block_ids': ['audit', 'evidence_verifier', 'file_hasher', 'capture'], 'gap': False}], 'agent_reviews': [], 'agent_model': ''}
CAPABILITIES = [{'id': 'fleet_registry', 'entity': 'fleet_registry', 'source': 'kernel execute_action template', 'http': {'create': 'POST /v1/fleet_registry', 'list': 'GET /v1/fleet_registry', 'get': 'GET /v1/fleet_registry/{id}', 'update': 'PUT /v1/fleet_registry/{id}', 'delete': 'DELETE /v1/fleet_registry/{id}'}}, {'id': 'rental_contract_management', 'entity': 'rental_contract_management', 'source': 'kernel execute_action template', 'http': {'create': 'POST /v1/rental_contract_management', 'list': 'GET /v1/rental_contract_management', 'get': 'GET /v1/rental_contract_management/{id}', 'update': 'PUT /v1/rental_contract_management/{id}', 'delete': 'DELETE /v1/rental_contract_management/{id}'}}, {'id': 'maintenance_scheduling', 'entity': 'maintenance_scheduling', 'source': 'kernel execute_action template', 'http': {'create': 'POST /v1/maintenance_scheduling', 'list': 'GET /v1/maintenance_scheduling', 'get': 'GET /v1/maintenance_scheduling/{id}', 'update': 'PUT /v1/maintenance_scheduling/{id}', 'delete': 'DELETE /v1/maintenance_scheduling/{id}'}}, {'id': 'pricing_and_rate_cards', 'entity': 'pricing_and_rate_cards', 'source': 'kernel execute_action template', 'http': {'create': 'POST /v1/pricing_and_rate_cards', 'list': 'GET /v1/pricing_and_rate_cards', 'get': 'GET /v1/pricing_and_rate_cards/{id}', 'update': 'PUT /v1/pricing_and_rate_cards/{id}', 'delete': 'DELETE /v1/pricing_and_rate_cards/{id}'}}, {'id': 'invoicing_and_deposits', 'entity': 'invoicing_and_deposits', 'source': 'kernel execute_action template', 'http': {'create': 'POST /v1/invoicing_and_deposits', 'list': 'GET /v1/invoicing_and_deposits', 'get': 'GET /v1/invoicing_and_deposits/{id}', 'update': 'PUT /v1/invoicing_and_deposits/{id}', 'delete': 'DELETE /v1/invoicing_and_deposits/{id}'}}, {'id': 'multi_branch_rollup', 'entity': 'multi_branch_rollup', 'source': 'kernel execute_action template', 'http': {'create': 'POST /v1/multi_branch_rollup', 'list': 'GET /v1/multi_branch_rollup', 'get': 'GET /v1/multi_branch_rollup/{id}', 'update': 'PUT /v1/multi_branch_rollup/{id}', 'delete': 'DELETE /v1/multi_branch_rollup/{id}'}}, {'id': 'reporting_analytics', 'entity': 'reporting_analytics', 'source': 'kernel execute_action template', 'http': {'create': 'POST /v1/reporting_analytics', 'list': 'GET /v1/reporting_analytics', 'get': 'GET /v1/reporting_analytics/{id}', 'update': 'PUT /v1/reporting_analytics/{id}', 'delete': 'DELETE /v1/reporting_analytics/{id}'}}, {'id': 'audit_trail', 'entity': 'audit_trail', 'source': 'kernel execute_action template', 'http': {'create': 'POST /v1/audit_trail', 'list': 'GET /v1/audit_trail', 'get': 'GET /v1/audit_trail/{id}', 'update': 'PUT /v1/audit_trail/{id}', 'delete': 'DELETE /v1/audit_trail/{id}'}}]
GATES = {'kernel': 'TESTER', 'title': 'Acceptance inspector', 'mandate': "Write and run the code-phase suite against what the WRITER produced (imports, dispatch load, models, routes answer JSON, handle() returns a mapping) and bounce those failures for another writer pass. Store-backed execute-all is pilot coverage, not this gate. The harness's acceptance IS the tester — do not consult the coding agent for extra cases. Never patch app/. Never run the suite over HTTP — GET /v1/gates describes coverage only.", 'agent': 'none', 'runs_over_http': False, 'suite': [{'file': 'tests/test_smoke.py', 'covers': 'import, offline dispatch load, handle() returns a mapping', 'gated': True}, {'file': 'tests/test_smoke.py', 'covers': 'Store-backed handle() ok and nested error scan', 'marker': 'pilot', 'gated': False}, {'file': 'tests/test_models.py', 'covers': 'sqlite round-trip via store.save / store.get', 'gated': True}, {'file': 'tests/test_data_lifecycle.py', 'covers': 'Alembic up/down on populated v1, restore drill, parallel writes', 'gated': True}, {'file': 'tests/test_deploy.py', 'covers': 'Fail-closed /health, correlation logs, revision rollback identity', 'gated': True}, {'file': 'tests/test_domain_acceptance.py', 'covers': 'Ten business outcomes through execute_action', 'marker': 'pilot', 'gated': False}, {'file': 'tests/test_routes.py', 'covers': 'HTTP 200 JSON for /health, kernel jobs, and each capability POST', 'gated': True}, {'file': 'tests/test_routes.py', 'covers': 'Store-backed POST accepted (ok is not False) and persisted', 'marker': 'pilot', 'gated': False}]}


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
