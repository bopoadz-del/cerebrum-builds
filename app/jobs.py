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
CATALOG = {'kernel': 'COLLECTOR', 'title': 'Binding surveyor', 'mandate': "Emit intake_blueprint.v1 (COLLECTOR output IS that object — vertical, capabilities with customer words + normalized id, roles/users, data sources, integrations, constraints, done_when, each field carrying the chat turn it came from). Resolve each capability's declared block ids into harvestable contracts. Name every capability with no block as an explicit gap so the WRITER authors that logic — never drop it from the plan. Consult the coding agent for a report-only endorse/mismatch review of each binding. Do not invent block ids, do not mutate the plan, and write nothing.", 'agent': 'consult', 'resolved_blocks': ['analytics', 'audit', 'capture', 'dashboard', 'database', 'document_engine', 'estate_maintenance', 'estate_registry', 'event_bus', 'formula_executor', 'knowledge', 'memory', 'notification', 'portfolio_rollup', 'queue', 'readiness_engine', 'recommendation_template', 'spec_analyzer', 'storage', 'team', 'validation', 'vector_search', 'workflow'], 'gaps': [], 'bindings': [{'capability_id': 'branch_and_consolidated_operations', 'block_ids': ['dashboard', 'portfolio_rollup', 'analytics', 'team', 'database', 'storage'], 'gap': False}, {'capability_id': 'inventory_and_replenishment', 'block_ids': ['database', 'analytics', 'notification', 'workflow', 'estate_registry', 'readiness_engine'], 'gap': False}, {'capability_id': 'branch_books_and_accounting', 'block_ids': ['database', 'formula_executor', 'analytics', 'portfolio_rollup', 'document_engine', 'validation'], 'gap': False}, {'capability_id': 'delivery_and_dispatch', 'block_ids': ['workflow', 'queue', 'notification', 'capture', 'estate_maintenance', 'database', 'analytics'], 'gap': False}, {'capability_id': 'order_follow_up', 'block_ids': ['workflow', 'queue', 'notification', 'database', 'capture', 'audit'], 'gap': False}, {'capability_id': 'events_supply', 'block_ids': ['workflow', 'database', 'document_engine', 'notification', 'recommendation_template', 'analytics'], 'gap': False}, {'capability_id': 'document_grounded_knowledge', 'block_ids': ['knowledge', 'vector_search', 'document_engine', 'memory', 'spec_analyzer', 'validation'], 'gap': False}, {'capability_id': 'outlook_branch_messaging_integration', 'block_ids': ['event_bus', 'queue', 'notification', 'capture', 'audit'], 'gap': False}], 'agent_reviews': [], 'agent_model': ''}
CAPABILITIES = [{'id': 'branch_and_consolidated_operations', 'entity': 'branch_and_consolidated_operations', 'source': 'factory-grounded persist', 'http': {'create': 'POST /v1/branch_and_consolidated_operations', 'list': 'GET /v1/branch_and_consolidated_operations', 'get': 'GET /v1/branch_and_consolidated_operations/{id}'}}, {'id': 'inventory_and_replenishment', 'entity': 'inventory_and_replenishment', 'source': 'factory-grounded persist', 'http': {'create': 'POST /v1/inventory_and_replenishment', 'list': 'GET /v1/inventory_and_replenishment', 'get': 'GET /v1/inventory_and_replenishment/{id}'}}, {'id': 'branch_books_and_accounting', 'entity': 'branch_books_and_accounting', 'source': 'factory-grounded persist', 'http': {'create': 'POST /v1/branch_books_and_accounting', 'list': 'GET /v1/branch_books_and_accounting', 'get': 'GET /v1/branch_books_and_accounting/{id}'}}, {'id': 'delivery_and_dispatch', 'entity': 'delivery_and_dispatch', 'source': 'factory-grounded persist', 'http': {'create': 'POST /v1/delivery_and_dispatch', 'list': 'GET /v1/delivery_and_dispatch', 'get': 'GET /v1/delivery_and_dispatch/{id}'}}, {'id': 'order_follow_up', 'entity': 'order_follow_up', 'source': 'factory-grounded persist', 'http': {'create': 'POST /v1/order_follow_up', 'list': 'GET /v1/order_follow_up', 'get': 'GET /v1/order_follow_up/{id}'}}, {'id': 'events_supply', 'entity': 'events_supply', 'source': 'factory-grounded persist', 'http': {'create': 'POST /v1/events_supply', 'list': 'GET /v1/events_supply', 'get': 'GET /v1/events_supply/{id}'}}, {'id': 'document_grounded_knowledge', 'entity': 'document_grounded_knowledge', 'source': 'factory-grounded persist', 'http': {'create': 'POST /v1/document_grounded_knowledge', 'list': 'GET /v1/document_grounded_knowledge', 'get': 'GET /v1/document_grounded_knowledge/{id}'}}, {'id': 'outlook_branch_messaging_integration', 'entity': 'outlook_branch_messaging_integration', 'source': 'factory-grounded persist', 'http': {'create': 'POST /v1/outlook_branch_messaging_integration', 'list': 'GET /v1/outlook_branch_messaging_integration', 'get': 'GET /v1/outlook_branch_messaging_integration/{id}'}}]
GATES = {'kernel': 'TESTER', 'title': 'Acceptance inspector', 'mandate': "Write and run the code-phase suite against what the WRITER produced (imports, dispatch load, models, routes answer JSON, handle() returns a mapping) and bounce those failures for another writer pass. Store-backed execute-all is pilot coverage, not this gate. The harness's acceptance IS the tester — do not consult the coding agent for extra cases. Never patch app/. Never run the suite over HTTP — GET /v1/gates describes coverage only.", 'agent': 'none', 'runs_over_http': False, 'suite': []}


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
