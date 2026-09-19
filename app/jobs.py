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
CATALOG = {'kernel': 'COLLECTOR', 'title': 'Binding surveyor', 'mandate': "Emit intake_blueprint.v1 and resolve each capability's declared block ids into harvestable contracts. Name every capability with no block as an explicit gap; never drop it from the plan. Do not invent block ids and write nothing.", 'agent': 'consult', 'resolved_blocks': ['analytics', 'audit', 'capture', 'dashboard', 'database', 'event_bus', 'notification', 'queue', 'team', 'validation', 'workflow'], 'gaps': [], 'bindings': [{'capability_id': 'patient_visit_records', 'block_ids': ['capture', 'database', 'validation', 'audit']}, {'capability_id': 'appointment_scheduling', 'block_ids': ['workflow', 'database', 'validation', 'audit']}, {'capability_id': 'todays_appointment_list', 'block_ids': ['dashboard', 'database', 'workflow']}, {'capability_id': 'day_before_email_reminders', 'block_ids': ['notification', 'queue', 'event_bus', 'audit']}, {'capability_id': 'patient_directory', 'block_ids': ['database', 'capture', 'validation']}, {'capability_id': 'clinical_history_search', 'block_ids': ['database', 'analytics']}, {'capability_id': 'role_based_access', 'block_ids': ['team', 'audit']}], 'vertical': 'dental_clinic'}
CAPABILITIES = [{'id': 'patient_visit_records', 'entity': 'patient_visit_records', 'source': 'kernel execute_action template', 'http': {'create': 'POST /v1/patient_visit_records', 'list': 'GET /v1/patient_visit_records', 'get': 'GET /v1/patient_visit_records/{id}', 'update': 'PUT /v1/patient_visit_records/{id}', 'delete': 'DELETE /v1/patient_visit_records/{id}'}}, {'id': 'appointment_scheduling', 'entity': 'appointment_scheduling', 'source': 'kernel execute_action template', 'http': {'create': 'POST /v1/appointment_scheduling', 'list': 'GET /v1/appointment_scheduling', 'get': 'GET /v1/appointment_scheduling/{id}', 'update': 'PUT /v1/appointment_scheduling/{id}', 'delete': 'DELETE /v1/appointment_scheduling/{id}'}}, {'id': 'todays_appointment_list', 'entity': 'todays_appointment_list', 'source': 'kernel execute_action template', 'http': {'create': 'POST /v1/todays_appointment_list', 'list': 'GET /v1/todays_appointment_list', 'get': 'GET /v1/todays_appointment_list/{id}', 'update': 'PUT /v1/todays_appointment_list/{id}', 'delete': 'DELETE /v1/todays_appointment_list/{id}'}}, {'id': 'day_before_email_reminders', 'entity': 'day_before_email_reminders', 'source': 'kernel execute_action template', 'http': {'create': 'POST /v1/day_before_email_reminders', 'list': 'GET /v1/day_before_email_reminders', 'get': 'GET /v1/day_before_email_reminders/{id}', 'update': 'PUT /v1/day_before_email_reminders/{id}', 'delete': 'DELETE /v1/day_before_email_reminders/{id}'}}, {'id': 'patient_directory', 'entity': 'patient_directory', 'source': 'kernel execute_action template', 'http': {'create': 'POST /v1/patient_directory', 'list': 'GET /v1/patient_directory', 'get': 'GET /v1/patient_directory/{id}', 'update': 'PUT /v1/patient_directory/{id}', 'delete': 'DELETE /v1/patient_directory/{id}'}}, {'id': 'clinical_history_search', 'entity': 'clinical_history_search', 'source': 'kernel execute_action template', 'http': {'create': 'POST /v1/clinical_history_search', 'list': 'GET /v1/clinical_history_search', 'get': 'GET /v1/clinical_history_search/{id}', 'update': 'PUT /v1/clinical_history_search/{id}', 'delete': 'DELETE /v1/clinical_history_search/{id}'}}, {'id': 'role_based_access', 'entity': 'role_based_access', 'source': 'kernel execute_action template', 'http': {'create': 'POST /v1/role_based_access', 'list': 'GET /v1/role_based_access', 'get': 'GET /v1/role_based_access/{id}', 'update': 'PUT /v1/role_based_access/{id}', 'delete': 'DELETE /v1/role_based_access/{id}'}}]
GATES = {'kernel': 'TESTER', 'title': 'Acceptance inspector', 'mandate': "Write and run the code-phase suite against what the WRITER produced (imports, dispatch load, models, routes answer JSON, handle() returns a mapping) and bounce those failures for another writer pass. Store-backed execute-all is pilot coverage, not this gate. The harness's acceptance IS the tester. Never patch app/. Never run the suite over HTTP — GET /v1/gates describes coverage only.", 'agent': 'none', 'runs_over_http': False, 'suite': [{'file': 'tests/test_smoke.py', 'covers': 'import, offline dispatch load, handle() returns a mapping', 'gated': True}, {'file': 'tests/test_smoke.py', 'covers': 'Store-backed handle() ok and nested error scan', 'marker': 'pilot', 'gated': False}, {'file': 'tests/test_models.py', 'covers': 'sqlite round-trip via store.save / store.get', 'gated': True}, {'file': 'tests/test_data_lifecycle.py', 'covers': 'Alembic up/down on populated v1, restore drill, parallel writes', 'gated': True}, {'file': 'tests/test_deploy.py', 'covers': 'Fail-closed /health, correlation logs, revision rollback identity', 'gated': True}, {'file': 'tests/test_domain_acceptance.py', 'covers': 'Ten business outcomes through the kernel path', 'marker': 'pilot', 'gated': False}, {'file': 'tests/test_routes.py', 'covers': 'HTTP 200 JSON for /health, kernel jobs, and each capability POST', 'gated': True}, {'file': 'tests/test_routes.py', 'covers': 'Store-backed POST accepted (ok is not False) and persisted', 'marker': 'pilot', 'gated': False}]}


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
