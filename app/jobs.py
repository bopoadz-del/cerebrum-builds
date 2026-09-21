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
CATALOG = {'kernel': 'COLLECTOR', 'title': 'Binding surveyor', 'mandate': "Confirm every capability's block bindings against the Store registry before a line of the platform is written.", 'agent': 'collector', 'resolved_blocks': ['billing', 'channel_router', 'dashboard', 'document_engine', 'estate_maintenance', 'estate_registry', 'guest_rfm_segmentation', 'hospitality_connectors', 'hotel_v2', 'multi_tenant_rbac', 'notification', 'workflow'], 'gaps': [], 'bindings': [{'capability_id': 'property_and_room_registry', 'block_ids': ['estate_registry', 'hotel_v2'], 'gap': False}, {'capability_id': 'front_desk_and_guest_stay', 'block_ids': ['hotel_v2', 'workflow'], 'gap': False}, {'capability_id': 'housekeeping_and_maintenance', 'block_ids': ['estate_maintenance', 'workflow'], 'gap': False}, {'capability_id': 'guest_engagement_and_segmentation', 'block_ids': ['guest_rfm_segmentation', 'channel_router', 'notification'], 'gap': False}, {'capability_id': 'document_and_knowledge_answers', 'block_ids': ['document_engine', 'hotel_v2'], 'gap': False}, {'capability_id': 'operations_billing', 'block_ids': ['billing', 'hotel_v2'], 'gap': False}, {'capability_id': 'operations_oversight_dashboard', 'block_ids': ['dashboard', 'multi_tenant_rbac'], 'gap': False}, {'capability_id': 'external_integration_adapter', 'block_ids': ['hospitality_connectors'], 'gap': False}], 'agent_reviews': [], 'agent_model': ''}
CAPABILITIES = [{'id': 'property_and_room_registry', 'entity': 'property_and_room_registry', 'source': 'factory-grounded persist', 'blocks': ['estate_registry', 'hotel_v2'], 'http': {'create': 'POST /v1/property_and_room_registry', 'list': 'GET /v1/property_and_room_registry', 'get': 'GET /v1/property_and_room_registry/{id}', 'update': 'PUT /v1/property_and_room_registry/{id}', 'delete': 'DELETE /v1/property_and_room_registry/{id}'}}, {'id': 'front_desk_and_guest_stay', 'entity': 'front_desk_and_guest_stay', 'source': 'factory-grounded persist', 'blocks': ['hotel_v2', 'workflow'], 'http': {'create': 'POST /v1/front_desk_and_guest_stay', 'list': 'GET /v1/front_desk_and_guest_stay', 'get': 'GET /v1/front_desk_and_guest_stay/{id}', 'update': 'PUT /v1/front_desk_and_guest_stay/{id}', 'delete': 'DELETE /v1/front_desk_and_guest_stay/{id}'}}, {'id': 'housekeeping_and_maintenance', 'entity': 'housekeeping_and_maintenance', 'source': 'factory-grounded persist', 'blocks': ['estate_maintenance', 'workflow'], 'http': {'create': 'POST /v1/housekeeping_and_maintenance', 'list': 'GET /v1/housekeeping_and_maintenance', 'get': 'GET /v1/housekeeping_and_maintenance/{id}', 'update': 'PUT /v1/housekeeping_and_maintenance/{id}', 'delete': 'DELETE /v1/housekeeping_and_maintenance/{id}'}}, {'id': 'guest_engagement_and_segmentation', 'entity': 'guest_engagement_and_segmentation', 'source': 'factory-grounded persist', 'blocks': ['guest_rfm_segmentation', 'channel_router', 'notification'], 'http': {'create': 'POST /v1/guest_engagement_and_segmentation', 'list': 'GET /v1/guest_engagement_and_segmentation', 'get': 'GET /v1/guest_engagement_and_segmentation/{id}', 'update': 'PUT /v1/guest_engagement_and_segmentation/{id}', 'delete': 'DELETE /v1/guest_engagement_and_segmentation/{id}'}}, {'id': 'document_and_knowledge_answers', 'entity': 'document_and_knowledge_answers', 'source': 'factory-grounded persist', 'blocks': ['knowledge', 'document_engine'], 'http': {'create': 'POST /v1/document_and_knowledge_answers', 'list': 'GET /v1/document_and_knowledge_answers', 'get': 'GET /v1/document_and_knowledge_answers/{id}', 'update': 'PUT /v1/document_and_knowledge_answers/{id}', 'delete': 'DELETE /v1/document_and_knowledge_answers/{id}'}}, {'id': 'operations_billing', 'entity': 'operations_billing', 'source': 'factory-grounded persist', 'blocks': ['billing', 'hotel_v2'], 'http': {'create': 'POST /v1/operations_billing', 'list': 'GET /v1/operations_billing', 'get': 'GET /v1/operations_billing/{id}', 'update': 'PUT /v1/operations_billing/{id}', 'delete': 'DELETE /v1/operations_billing/{id}'}}, {'id': 'operations_oversight_dashboard', 'entity': 'operations_oversight_dashboard', 'source': 'factory-grounded persist', 'blocks': ['dashboard', 'multi_tenant_rbac'], 'http': {'create': 'POST /v1/operations_oversight_dashboard', 'list': 'GET /v1/operations_oversight_dashboard', 'get': 'GET /v1/operations_oversight_dashboard/{id}', 'update': 'PUT /v1/operations_oversight_dashboard/{id}', 'delete': 'DELETE /v1/operations_oversight_dashboard/{id}'}}, {'id': 'external_integration_adapter', 'entity': 'external_integration_adapter', 'source': 'factory-grounded persist', 'blocks': ['mcp_adapter', 'hospitality_connectors'], 'http': {'create': 'POST /v1/external_integration_adapter', 'list': 'GET /v1/external_integration_adapter', 'get': 'GET /v1/external_integration_adapter/{id}', 'update': 'PUT /v1/external_integration_adapter/{id}', 'delete': 'DELETE /v1/external_integration_adapter/{id}'}}]
GATES = {'kernel': 'TESTER', 'title': 'Acceptance inspector', 'mandate': 'Own the acceptance suite; publish coverage; never run the suite over HTTP.', 'agent': 'tester', 'runs_over_http': False, 'suite': [{'file': 'tests/test_smoke.py', 'covers': 'import, offline dispatch load, handle() returns a mapping', 'gated': True}, {'file': 'tests/test_routes.py', 'covers': 'HTTP 200 JSON for /health, kernel jobs, and each capability POST', 'gated': True}, {'file': 'tests/test_models.py', 'covers': 'store round-trip per entity', 'gated': True}, {'file': 'tests/test_domain_acceptance.py', 'covers': 'ten business outcomes through execute_action', 'marker': 'pilot', 'gated': False}]}


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
