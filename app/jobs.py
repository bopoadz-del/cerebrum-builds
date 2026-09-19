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

JOBS = [{'kernel': 'COLLECTOR', 'title': 'Binding surveyor', 'mandate': "Emit intake_blueprint.v1 (COLLECTOR output IS that object — vertical, capabilities with customer words + normalized id, roles/users, data sources, integrations, constraints, done_when, each field carrying the chat turn it came from). Resolve each capability's declared block ids into harvestable contracts. Name every capability with no block as an explicit gap so the WRITER authors that logic — never drop it from the plan. Consult the coding agent for a report-only endorse/mismatch review of each binding. Do not invent block ids, do not mutate the plan, and write nothing.", 'agent': 'consult', 'http_routes': ['GET /v1/catalog'], 'gate': 'every referenced block id is dual-registered; gaps enumerated', 'read_only': True}, {'kernel': 'CLONER', 'title': 'Block stocker', 'mandate': "Vendor each resolved block's source at a pinned commit, plus the local dispatch runtime those shims stand on, plus the kit packs the Factory shelf assigns those blocks to, so handlers import blocks instead of calling the store over HTTP. Write only vendor/**, kits/**, and blocks.lock.json. Exact answers — no agent.", 'agent': 'none', 'http_routes': ['GET /v1/inventory'], 'gate': 'every vendored block imports with no network configured', 'read_only': False}, {'kernel': 'WRITER', 'title': 'Platform manufacturer', 'mandate': "Manufacture the platform over the vendored stock: capability handlers, domain models, persistence, the HTTP surface (including each kernel's job routes), UI wiring, and GENERATE logic for the gaps the collector reported. The coding agent writes those artifacts inside WRITER lanes. Do not touch tests/ or vendor/.", 'agent': 'manufacture', 'http_routes': ['GET /v1/capabilities', 'POST /v1/{capability}', 'GET /v1/{capability}', 'GET /v1/{capability}/{id}', 'PUT /v1/{capability}/{id}', 'DELETE /v1/{capability}/{id}', 'POST /v1/rag/ingest', 'POST /v1/rag/query', 'GET /v1/rag/query', 'GET /v1/rag/documents', 'POST /v1/work_queue', 'POST /v1/work_queue/{id}/process', 'GET /v1/work_queue'], 'gate': 'workspace imports and type-checks clean', 'read_only': False}, {'kernel': 'TESTER', 'title': 'Acceptance inspector', 'mandate': "Write and run the code-phase suite against what the WRITER produced (imports, dispatch load, models, routes answer JSON, handle() returns a mapping) and bounce those failures for another writer pass. Store-backed execute-all is pilot coverage, not this gate. The harness's acceptance IS the tester — do not consult the coding agent for extra cases. Never patch app/. Never run the suite over HTTP — GET /v1/gates describes coverage only.", 'agent': 'none', 'http_routes': ['GET /v1/gates'], 'gate': "code-phase suite green (pytest -m 'not pilot')", 'read_only': False}, {'kernel': 'STORE_MANAGER', 'title': 'Store registrar', 'mandate': "Keep the store's books: register what this platform cloned and at which commit. This minimal form records the clone register and applies no store op. Harvesting improvements back upstream and admitting client-driven net-new capability remain unbuilt. Exact answers — no agent.", 'agent': 'none', 'http_routes': ['GET /v1/provenance'], 'gate': 'store_manager.assert_store_op_allowed passes for every op applied', 'read_only': False}]
CATALOG = {'kernel': 'COLLECTOR', 'title': 'Binding surveyor', 'mandate': "Emit intake_blueprint.v1 (COLLECTOR output IS that object — vertical, capabilities with customer words + normalized id, roles/users, data sources, integrations, constraints, done_when, each field carrying the chat turn it came from). Resolve each capability's declared block ids into harvestable contracts. Name every capability with no block as an explicit gap so the WRITER authors that logic — never drop it from the plan. Consult the coding agent for a report-only endorse/mismatch review of each binding. Do not invent block ids, do not mutate the plan, and write nothing.", 'agent': 'consult', 'resolved_blocks': ['analytics', 'audit', 'capture', 'dashboard', 'database', 'document_engine', 'event_bus', 'evidence_verifier', 'file_hasher', 'formula_executor', 'knowledge', 'notification', 'portfolio_rollup', 'queue', 'recommendation_template', 'spec_analyzer', 'storage', 'team', 'validation', 'vector_search', 'workflow'], 'gaps': [], 'bindings': [{'capability_id': 'budget_planning_tracking', 'block_ids': ['workflow', 'database', 'formula_executor', 'validation', 'notification'], 'gap': False}, {'capability_id': 'spend_capture_categorisation', 'block_ids': ['capture', 'database', 'file_hasher', 'document_engine', 'validation', 'event_bus'], 'gap': False}, {'capability_id': 'approval_workflow', 'block_ids': ['workflow', 'queue', 'notification', 'audit', 'team', 'event_bus'], 'gap': False}, {'capability_id': 'variance_analytics', 'block_ids': ['analytics', 'formula_executor', 'dashboard', 'portfolio_rollup', 'database'], 'gap': False}, {'capability_id': 'dashboard_portfolio_rollup', 'block_ids': ['dashboard', 'portfolio_rollup', 'analytics', 'recommendation_template'], 'gap': False}, {'capability_id': 'audit_evidence_validation', 'block_ids': ['audit', 'evidence_verifier', 'file_hasher', 'validation', 'storage', 'database'], 'gap': False}, {'capability_id': 'finance_document_knowledge', 'block_ids': ['document_engine', 'knowledge', 'vector_search', 'storage', 'spec_analyzer', 'capture'], 'gap': False}, {'capability_id': 'integrations_placeholders', 'block_ids': ['workflow', 'event_bus', 'notification', 'audit', 'storage'], 'gap': False}], 'agent_reviews': [], 'agent_model': ''}
CAPABILITIES = [{'id': 'budget_planning_tracking', 'entity': 'budget_planning_tracking', 'source': 'factory-grounded persist', 'http': {'create': 'POST /v1/budget_planning_tracking', 'list': 'GET /v1/budget_planning_tracking', 'get': 'GET /v1/budget_planning_tracking/{id}'}}, {'id': 'spend_capture_categorisation', 'entity': 'spend_capture_categorisation', 'source': 'factory-grounded persist', 'http': {'create': 'POST /v1/spend_capture_categorisation', 'list': 'GET /v1/spend_capture_categorisation', 'get': 'GET /v1/spend_capture_categorisation/{id}'}}, {'id': 'approval_workflow', 'entity': 'approval_workflow', 'source': 'factory-grounded persist', 'http': {'create': 'POST /v1/approval_workflow', 'list': 'GET /v1/approval_workflow', 'get': 'GET /v1/approval_workflow/{id}'}}, {'id': 'variance_analytics', 'entity': 'variance_analytics', 'source': 'factory-grounded persist', 'http': {'create': 'POST /v1/variance_analytics', 'list': 'GET /v1/variance_analytics', 'get': 'GET /v1/variance_analytics/{id}'}}, {'id': 'dashboard_portfolio_rollup', 'entity': 'dashboard_portfolio_rollup', 'source': 'factory-grounded persist', 'http': {'create': 'POST /v1/dashboard_portfolio_rollup', 'list': 'GET /v1/dashboard_portfolio_rollup', 'get': 'GET /v1/dashboard_portfolio_rollup/{id}'}}, {'id': 'audit_evidence_validation', 'entity': 'audit_evidence_validation', 'source': 'factory-grounded persist', 'http': {'create': 'POST /v1/audit_evidence_validation', 'list': 'GET /v1/audit_evidence_validation', 'get': 'GET /v1/audit_evidence_validation/{id}'}}, {'id': 'finance_document_knowledge', 'entity': 'finance_document_knowledge', 'source': 'factory-grounded persist', 'http': {'create': 'POST /v1/finance_document_knowledge', 'list': 'GET /v1/finance_document_knowledge', 'get': 'GET /v1/finance_document_knowledge/{id}'}}, {'id': 'integrations_placeholders', 'entity': 'integrations_placeholders', 'source': 'factory-grounded persist', 'http': {'create': 'POST /v1/integrations_placeholders', 'list': 'GET /v1/integrations_placeholders', 'get': 'GET /v1/integrations_placeholders/{id}'}}]
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
