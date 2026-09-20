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
CATALOG = {'kernel': 'COLLECTOR', 'title': 'Binding surveyor', 'mandate': 'intake_blueprint.v1 for the Dubai schools estate', 'agent': 'consult', 'resolved_blocks': ['analytics', 'audit', 'capture', 'dashboard', 'event_bus', 'formula_executor', 'notification', 'portfolio_rollup', 'queue', 'recommendation_template', 'team', 'validation', 'workflow'], 'gaps': [], 'bindings': [{'capability_id': 'complaints_management', 'block_ids': [], 'gap': False}, {'capability_id': 'auto_assignment', 'block_ids': [], 'gap': False}, {'capability_id': 'workforce_management', 'block_ids': [], 'gap': False}, {'capability_id': 'management_dashboards', 'block_ids': [], 'gap': False}, {'capability_id': 'reporting', 'block_ids': [], 'gap': False}, {'capability_id': 'role_based_access', 'block_ids': [], 'gap': False}, {'capability_id': 'erp_integration', 'block_ids': [], 'gap': False}, {'capability_id': 'booking_system_integration', 'block_ids': [], 'gap': False}], 'agent_reviews': [], 'agent_model': ''}
CAPABILITIES = [{'id': 'complaints_management', 'entity': 'complaints_management', 'source': 'REUSE + factory-grounded persist', 'http': {'create': 'POST /v1/complaints_management', 'list': 'GET /v1/complaints_management', 'get': 'GET /v1/complaints_management/{id}', 'update': 'PUT /v1/complaints_management/{id}', 'delete': 'DELETE /v1/complaints_management/{id}'}}, {'id': 'auto_assignment', 'entity': 'auto_assignment', 'source': 'REUSE + factory-grounded persist', 'http': {'create': 'POST /v1/auto_assignment', 'list': 'GET /v1/auto_assignment', 'get': 'GET /v1/auto_assignment/{id}', 'update': 'PUT /v1/auto_assignment/{id}', 'delete': 'DELETE /v1/auto_assignment/{id}'}}, {'id': 'workforce_management', 'entity': 'workforce_management', 'source': 'REUSE + factory-grounded persist', 'http': {'create': 'POST /v1/workforce_management', 'list': 'GET /v1/workforce_management', 'get': 'GET /v1/workforce_management/{id}', 'update': 'PUT /v1/workforce_management/{id}', 'delete': 'DELETE /v1/workforce_management/{id}'}}, {'id': 'management_dashboards', 'entity': 'management_dashboards', 'source': 'REUSE + factory-grounded persist', 'http': {'create': 'POST /v1/management_dashboards', 'list': 'GET /v1/management_dashboards', 'get': 'GET /v1/management_dashboards/{id}', 'update': 'PUT /v1/management_dashboards/{id}', 'delete': 'DELETE /v1/management_dashboards/{id}'}}, {'id': 'reporting', 'entity': 'reporting', 'source': 'REUSE + factory-grounded persist', 'http': {'create': 'POST /v1/reporting', 'list': 'GET /v1/reporting', 'get': 'GET /v1/reporting/{id}', 'update': 'PUT /v1/reporting/{id}', 'delete': 'DELETE /v1/reporting/{id}'}}, {'id': 'role_based_access', 'entity': 'role_based_access', 'source': 'REUSE + factory-grounded persist', 'http': {'create': 'POST /v1/role_based_access', 'list': 'GET /v1/role_based_access', 'get': 'GET /v1/role_based_access/{id}', 'update': 'PUT /v1/role_based_access/{id}', 'delete': 'DELETE /v1/role_based_access/{id}'}}, {'id': 'erp_integration', 'entity': 'erp_integration', 'source': 'REUSE + factory-grounded persist', 'http': {'create': 'POST /v1/erp_integration', 'list': 'GET /v1/erp_integration', 'get': 'GET /v1/erp_integration/{id}', 'update': 'PUT /v1/erp_integration/{id}', 'delete': 'DELETE /v1/erp_integration/{id}'}}, {'id': 'booking_system_integration', 'entity': 'booking_system_integration', 'source': 'REUSE + factory-grounded persist', 'http': {'create': 'POST /v1/booking_system_integration', 'list': 'GET /v1/booking_system_integration', 'get': 'GET /v1/booking_system_integration/{id}', 'update': 'PUT /v1/booking_system_integration/{id}', 'delete': 'DELETE /v1/booking_system_integration/{id}'}}]
GATES = {'kernel': 'TESTER', 'title': 'Acceptance inspector', 'mandate': 'code + pilot suites over the booted product', 'agent': 'consult', 'runs_over_http': False, 'suite': [{'file': 'tests/test_smoke.py', 'covers': 'import + dispatch load'}, {'file': 'tests/test_models.py', 'covers': 'store round-trip'}, {'file': 'tests/test_routes.py', 'covers': 'kernel + capability HTTP'}]}


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
