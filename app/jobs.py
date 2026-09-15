"""Kernel job roster published over HTTP. TESTER does not run over HTTP."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from app.schema import REQUIRED_CAPABILITY_IDS

ROOT = Path(__file__).resolve().parents[1]

JOBS: List[Dict[str, Any]] = [
    {
        "kernel": "COLLECTOR",
        "title": "Binding surveyor",
        "mandate": "Inventory Store blocks and name GENERATE gaps before WRITER.",
        "http_routes": ["/v1/catalog", "/v1/capabilities"],
        "agent": "collector",
    },
    {
        "kernel": "CLONER",
        "title": "Block stocker",
        "mandate": "Vendor verified Store blocks and pin blocks.lock.json.",
        "http_routes": ["/v1/inventory"],
        "agent": "cloner",
    },
    {
        "kernel": "WRITER",
        "title": "Platform manufacturer",
        "mandate": "Author keep-path handlers, schema, and persist envelopes.",
        "http_routes": ["/v1/automotive_core", "/v1/dashboard", "/v1/team", "/v1/audit"],
        "agent": "writer",
    },
    {
        "kernel": "TESTER",
        "title": "Acceptance inspector",
        "mandate": "CODE then PRODUCT gates. Does not run the suite over HTTP.",
        "http_routes": ["/v1/gates"],
        "agent": "tester",
    },
    {
        "kernel": "STORE_MANAGER",
        "title": "Store registrar",
        "mandate": "Receipt, provenance, and Store Docker acceptance.",
        "http_routes": ["/v1/provenance"],
        "agent": "store_manager",
    },
]


def jobs_payload() -> Dict[str, Any]:
    return {"ok": True, "jobs": JOBS}


def catalog_payload() -> Dict[str, Any]:
    return {
        "ok": True,
        "kernel": "COLLECTOR",
        "product": "Automotive Platform",
        "capabilities": list(REQUIRED_CAPABILITY_IDS),
    }


def inventory_payload() -> Dict[str, Any]:
    lock_path = ROOT / "blocks.lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8")) if lock_path.is_file() else {}
    return {
        "ok": True,
        "kernel": "CLONER",
        "lock": lock,
        "blocks": list((lock.get("blocks") or {}).keys()),
    }


def capabilities_payload() -> Dict[str, Any]:
    items = [{"id": cap_id, "entity": cap_id} for cap_id in REQUIRED_CAPABILITY_IDS]
    return {"ok": True, "items": items, "count": len(items)}


def gates_payload() -> Dict[str, Any]:
    return {
        "ok": True,
        "kernel": "TESTER",
        "runs_over_http": False,
        "suites": ["pytest -m 'not pilot'", "pytest -m pilot"],
    }


def provenance_payload() -> Dict[str, Any]:
    receipt_path = ROOT / "receipt.json"
    receipt = {}
    if receipt_path.is_file():
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    return {
        "ok": True,
        "kernel": "STORE_MANAGER",
        "receipt": receipt,
        "product": "Automotive Platform",
    }
