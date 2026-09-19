"""Kernel job descriptions shipped with the Bakery Chain Operations & Delivery Platform.

Written by the factory WRITER role (codewhale exec)

Frozen at manufacture time. The HTTP routes publish each kernel's job; they
never re-run it. Inventory and provenance read the lock/provenance files live so
the register stays true to the checkout.

Scope
-----
READS  ``blocks.lock.json``, ``docs/build_provenance.json``.
WRITES nothing.
NEVER  network, ``vendor/**``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

CAPABILITIES: List[Dict[str, Any]] = [
    {"id": "stock_inventory_management", "entity": "stock_inventory_management",
     "blocks": ['database', 'workflow', 'validation', 'notification', 'analytics']},
    {"id": "product_pricing", "entity": "product_pricing",
     "blocks": ['database', 'formula_executor', 'validation', 'analytics']},
    {"id": "delivery_dispatch_tracking", "entity": "delivery_dispatch_tracking",
     "blocks": ['database', 'workflow', 'event_bus', 'queue', 'notification', 'analytics']},
    {"id": "fleet_cost_tracking", "entity": "fleet_cost_tracking",
     "blocks": ['database', 'validation', 'dashboard', 'analytics']},
    {"id": "management_reporting_dashboard", "entity": "management_reporting_dashboard",
     "blocks": ['dashboard', 'analytics', 'portfolio_rollup']},
    {"id": "user_roles_workforce", "entity": "user_roles_workforce",
     "blocks": ['team', 'database', 'workflow', 'audit']},
    {"id": "document_knowledge_qa", "entity": "document_knowledge_qa",
     "blocks": ['document_engine', 'knowledge', 'vector_search', 'storage', 'capture']},
    {"id": "procedures_readiness_and_audit_trail", "entity": "procedures_readiness_and_audit_trail",
     "blocks": ['audit', 'evidence_verifier', 'file_hasher', 'readiness_engine', 'spec_analyzer', 'workflow']},
]

CATALOG: Dict[str, Any] = {
    "kernel": "COLLECTOR",
    "title": "Binding surveyor",
    "product": "Bakery Chain Operations & Delivery Platform",
    "vertical": "bakery_management",
    "capabilities": [item["id"] for item in CAPABILITIES],
    "roles": ["operator", "admin"],
    "runtime": "offline / in-process vendored blocks",
}

JOBS: List[Dict[str, Any]] = [
    {"kernel": "COLLECTOR", "title": "Binding surveyor",
     "agent": "read-only binding survey",
     "http_routes": ["/v1/catalog", "/v1/capabilities"],
     "mandate": "Emit the intake blueprint (vertical, capabilities, roles, data sources, constraints, done_when)."},
    {"kernel": "CLONER", "title": "Block stocker",
     "agent": "read-only block stocking",
     "http_routes": ["/v1/inventory"],
     "mandate": "Vendor every resolved block's real source under vendor/blocks and pin it in blocks.lock.json."},
    {"kernel": "WRITER", "title": "Platform manufacturer",
     "agent": "one FACTORY_CODE_CLI writer",
     "http_routes": ["/v1/{capability}"],
     "mandate": "Author routes, handlers, schema, UI and packaging for each capability."},
    {"kernel": "TESTER", "title": "Acceptance inspector",
     "agent": "harness-owned suite (no extra model role)",
     "http_routes": ["/v1/gates"],
     "mandate": "Run the code-phase suite, the pilot suite and the one-record round-trip per capability."},
    {"kernel": "STORE_MANAGER", "title": "Store registrar",
     "agent": "harness-owned store gate",
     "http_routes": ["/v1/provenance"],
     "mandate": "Run scripts/acceptance.py inside the built image and register provenance."},
]

GATES: Dict[str, Any] = {
    "kernel": "TESTER",
    "agent": "none",
    "runs_over_http": False,
    "suite": [
        {"file": "tests/test_smoke.py", "covers": "import, dispatch load, handle() returns a mapping", "gated": True},
        {"file": "tests/test_models.py", "covers": "sqlite round-trip via store.save / store.get", "gated": True},
        {"file": "tests/test_routes.py", "covers": "HTTP 200 JSON for /health, kernel jobs, each capability POST", "gated": True},
        {"file": "tests/test_data_lifecycle.py", "covers": "schema up/down over populated v1, backup/restore drill, parallel writes", "gated": True},
        {"file": "tests/test_deploy.py", "covers": "fail-closed /health, request correlation id, revision mark rollback", "gated": True},
        {"file": "tests/test_domain_acceptance.py", "covers": "the ten named business outcomes through execute_action", "gated": True},
        {"file": "tests/test_kernel.py", "covers": "capability registry, lifecycle actions, isolation guards, formulas, provenance", "gated": True},
        {"file": "tests/test_pilot_round_trip.py", "covers": "one-record round-trip per capability", "marker": "pilot", "gated": False},
    ],
}


def _read_workspace_json(relative: str) -> Optional[Dict[str, Any]]:
    path = Path(__file__).resolve().parents[1] / relative
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _job(kernel: str) -> Dict[str, Any]:
    for item in JOBS:
        if item["kernel"] == kernel:
            return dict(item)
    return {"kernel": kernel}


def inventory() -> Dict[str, Any]:
    payload = _job("CLONER")
    payload["lock"] = _read_workspace_json("blocks.lock.json") or {
        "schema": "blocks.lock.v1",
        "blocks": {},
    }
    return payload


def provenance() -> Dict[str, Any]:
    payload = _job("STORE_MANAGER")
    payload["build"] = _read_workspace_json("docs/build_provenance.json") or {}
    lock = _read_workspace_json("blocks.lock.json") or {}
    payload["clones"] = lock.get("blocks") or {}
    payload["store_ops"] = []
    return payload
