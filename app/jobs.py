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
        "mandate": "Survey Store registry bindings and capability roster for this product.",
        "http_routes": ["/v1/catalog", "/v1/capabilities"],
        "agent": "collector",
    },
    {
        "kernel": "CLONER",
        "title": "Block stocker",
        "mandate": "Stock verified Store blocks into vendor/ and publish the lock.",
        "http_routes": ["/v1/inventory"],
        "agent": "cloner",
    },
    {
        "kernel": "WRITER",
        "title": "Platform manufacturer",
        "mandate": "Author handlers, routes, and the notes kernel for required capabilities.",
        "http_routes": ["/v1/productivity_core", "/v1/audit"],
        "agent": "writer",
    },
    {
        "kernel": "TESTER",
        "title": "Acceptance inspector",
        "mandate": "Run CODE and PRODUCT gates. Does not execute the suite over HTTP.",
        "http_routes": ["/v1/gates"],
        "agent": "tester",
    },
    {
        "kernel": "STORE_MANAGER",
        "title": "Store registrar",
        "mandate": "Record provenance and register the booted store artifact.",
        "http_routes": ["/v1/provenance"],
        "agent": "store_manager",
    },
]


def catalog() -> Dict[str, Any]:
    return {
        "ok": True,
        "kernel": "COLLECTOR",
        "product": "Productivity Platform",
        "capabilities": list(REQUIRED_CAPABILITY_IDS),
    }


def inventory() -> Dict[str, Any]:
    lock_path = ROOT / "blocks.lock.json"
    lock: Dict[str, Any] = {}
    if lock_path.is_file():
        try:
            lock = json.loads(lock_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            lock = {}
    return {
        "ok": True,
        "kernel": "CLONER",
        "lock": lock,
        "blocks": list((lock.get("blocks") or {}).keys()),
    }


def capabilities() -> Dict[str, Any]:
    return {
        "ok": True,
        "items": [{"id": cap_id} for cap_id in REQUIRED_CAPABILITY_IDS],
    }


def gates() -> Dict[str, Any]:
    return {
        "ok": True,
        "kernel": "TESTER",
        "runs_over_http": False,
        "suites": ["pytest -m 'not pilot'", "pytest -m pilot"],
    }


def provenance() -> Dict[str, Any]:
    return {
        "ok": True,
        "kernel": "STORE_MANAGER",
        "product": "Productivity Platform",
        "capabilities": list(REQUIRED_CAPABILITY_IDS),
    }
