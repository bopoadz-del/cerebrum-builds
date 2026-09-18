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
CATALOG = {'kernel': 'COLLECTOR', 'title': 'Binding surveyor', 'mandate': "Emit intake_blueprint.v1 (COLLECTOR output IS that object — vertical, capabilities with customer words + normalized id, roles/users, data sources, integrations, constraints, done_when, each field carrying the chat turn it came from). Resolve each capability's declared block ids into harvestable contracts. Name every capability with no block as an explicit gap so the WRITER authors that logic — never drop it from the plan. Consult the coding agent for a report-only endorse/mismatch review of each binding. Do not invent block ids, do not mutate the plan, and write nothing.", 'agent': 'consult', 'http_routes': ['GET /v1/catalog'], 'gate': 'every referenced block id is dual-registered; gaps enumerated', 'read_only': True, 'resolved_blocks': ['analytics', 'audit', 'capture', 'dashboard', 'database', 'event_bus', 'formula_executor', 'memory', 'queue', 'validation'], 'gaps': [], 'bindings': [{'capability_id': 'record_checkin', 'block_ids': ['capture', 'validation', 'database'], 'gap': False}, {'capability_id': 'todays_arrivals_board', 'block_ids': ['dashboard', 'database', 'analytics'], 'gap': False}, {'capability_id': 'room_availability_check', 'block_ids': ['validation', 'database', 'formula_executor'], 'gap': False}, {'capability_id': 'guest_notes_and_preferences', 'block_ids': ['database', 'memory'], 'gap': False}, {'capability_id': 'checkin_notifications', 'block_ids': ['event_bus', 'queue'], 'gap': False}, {'capability_id': 'daily_checkin_summary', 'block_ids': ['analytics', 'database', 'dashboard'], 'gap': False}, {'capability_id': 'audit_trail', 'block_ids': ['audit', 'database'], 'gap': False}], 'agent_reviews': [], 'agent_model': ''}
CAPABILITIES = [{'id': 'record_checkin', 'entity': 'record_checkin', 'source': 'kernel execute_action template', 'http': {'create': 'POST /v1/record_checkin', 'list': 'GET /v1/record_checkin', 'get': 'GET /v1/record_checkin/{id}', 'update': 'PUT /v1/record_checkin/{id}', 'delete': 'DELETE /v1/record_checkin/{id}'}}, {'id': 'todays_arrivals_board', 'entity': 'todays_arrivals_board', 'source': 'kernel execute_action template', 'http': {'create': 'POST /v1/todays_arrivals_board', 'list': 'GET /v1/todays_arrivals_board', 'get': 'GET /v1/todays_arrivals_board/{id}', 'update': 'PUT /v1/todays_arrivals_board/{id}', 'delete': 'DELETE /v1/todays_arrivals_board/{id}'}}, {'id': 'room_availability_check', 'entity': 'room_availability_check', 'source': 'kernel execute_action template', 'http': {'create': 'POST /v1/room_availability_check', 'list': 'GET /v1/room_availability_check', 'get': 'GET /v1/room_availability_check/{id}', 'update': 'PUT /v1/room_availability_check/{id}', 'delete': 'DELETE /v1/room_availability_check/{id}'}}, {'id': 'guest_notes_and_preferences', 'entity': 'guest_notes_and_preferences', 'source': 'kernel execute_action template', 'http': {'create': 'POST /v1/guest_notes_and_preferences', 'list': 'GET /v1/guest_notes_and_preferences', 'get': 'GET /v1/guest_notes_and_preferences/{id}', 'update': 'PUT /v1/guest_notes_and_preferences/{id}', 'delete': 'DELETE /v1/guest_notes_and_preferences/{id}'}}, {'id': 'checkin_notifications', 'entity': 'checkin_notifications', 'source': 'kernel execute_action template', 'http': {'create': 'POST /v1/checkin_notifications', 'list': 'GET /v1/checkin_notifications', 'get': 'GET /v1/checkin_notifications/{id}', 'update': 'PUT /v1/checkin_notifications/{id}', 'delete': 'DELETE /v1/checkin_notifications/{id}'}}, {'id': 'daily_checkin_summary', 'entity': 'daily_checkin_summary', 'source': 'kernel execute_action template', 'http': {'create': 'POST /v1/daily_checkin_summary', 'list': 'GET /v1/daily_checkin_summary', 'get': 'GET /v1/daily_checkin_summary/{id}', 'update': 'PUT /v1/daily_checkin_summary/{id}', 'delete': 'DELETE /v1/daily_checkin_summary/{id}'}}, {'id': 'audit_trail', 'entity': 'audit_trail', 'source': 'kernel execute_action template', 'http': {'create': 'POST /v1/audit_trail', 'list': 'GET /v1/audit_trail', 'get': 'GET /v1/audit_trail/{id}', 'update': 'PUT /v1/audit_trail/{id}', 'delete': 'DELETE /v1/audit_trail/{id}'}}]
GATES = {'kernel': 'TESTER', 'title': 'Acceptance inspector', 'mandate': "Write and run the code-phase suite against what the WRITER produced (imports, dispatch load, models, routes answer JSON, handle() returns a mapping) and bounce those failures for another writer pass. Store-backed execute-all is pilot coverage, not this gate. The harness's acceptance IS the tester — do not consult the coding agent for extra cases. Never patch app/. Never run the suite over HTTP — GET /v1/gates describes coverage only.", 'agent': 'none', 'http_routes': ['GET /v1/gates'], 'gate': "code-phase suite green (pytest -m 'not pilot')", 'read_only': False, 'runs_over_http': False, 'suite': [{'file': 'tests/test_smoke.py', 'covers': 'import, offline dispatch load, handle() returns a mapping', 'gated': True}, {'file': 'tests/test_models.py', 'covers': 'sqlite round-trip via store.save / store.get', 'gated': True}, {'file': 'tests/test_routes.py', 'covers': 'HTTP 200 JSON for /health, kernel jobs, and each capability POST', 'gated': True}, {'file': 'tests/test_routes.py', 'covers': 'Store-backed POST accepted (ok is not False) and persisted', 'marker': 'pilot', 'gated': False}, {'file': 'tests/test_hospitality_domain.py', 'covers': 'front-desk check-in, arrival board, double-booking refusal', 'gated': True}, {'file': 'tests/test_domain_acceptance.py', 'covers': 'Ten business outcomes through execute_action', 'marker': 'pilot', 'gated': False}]}


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
