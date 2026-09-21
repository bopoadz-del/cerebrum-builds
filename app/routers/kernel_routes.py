"""The platform's own kernel surfaces: who built it and what it carries.

    GET /v1/jobs         the five factory kernels, their JD and their routes
    GET /v1/catalog      the block catalogue this build was assembled from
    GET /v1/inventory    the vendored blocks and the lock they came from
    GET /v1/capabilities the capability contract, exactly as served
    GET /v1/gates        which gates ran, and that they run in-process
    GET /v1/provenance   where this tree came from

These are the only ``/v1`` surfaces that answer without a bearer token, and
that is deliberate: they describe the build and its schema, never a tenant's
records. Nothing here reads or writes a record, so there is no tenant to
resolve one under -- and the acceptance floor's ``no_token_401`` probe, which
POSTs a capability, is untouched by them.

Written by the factory WRITER role (codewhale exec)
"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter

from app import dispatch
from app.authority import precedence_document
from app.jobs import CAPABILITIES, PLATFORM
from app.models import CAPABILITY_IDS, MODELS
from app.revision import current_app_mark, current_app_revision

router = APIRouter(tags=["kernel"])

#: The five factory kernels. Each entry is the job the kernel performs on a
#: build, the HTTP surface it owns here, and the agent that runs it -- the
#: operator can read who did what without opening the build ledger.
KERNEL_JOBS: List[Dict[str, Any]] = [
    {
        "kernel": "COLLECTOR",
        "title": "Binding surveyor",
        "mandate": (
            "survey the Store and bind the blocks a capability needs; report what "
            "is present and what is missing, and never assume an id exists"
        ),
        "http_routes": ["/v1/catalog", "/v1/capabilities", "/v1/blocks"],
        "agent": "collector",
    },
    {
        "kernel": "CLONER",
        "title": "Block stocker",
        "mandate": (
            "vendor the surveyed blocks into this repository and record the lock "
            "they were taken at, so the platform runs offline"
        ),
        "http_routes": ["/v1/inventory"],
        "agent": "cloner",
    },
    {
        "kernel": "WRITER",
        "title": "Platform manufacturer",
        "mandate": (
            "write the routes, handlers and schema for every capability, bind the "
            "vendored blocks, and persist through one tenant-scoped store"
        ),
        "http_routes": ["/v1/dial-queue", "/v1/leads/import", "/v1/blocks"],
        "agent": "writer",
    },
    {
        "kernel": "TESTER",
        "title": "Acceptance inspector",
        "mandate": (
            "measure the booted product against the brief's own counter-cases and "
            "report a red suite rather than a thin green one"
        ),
        "http_routes": ["/v1/gates", "/v1/ledger/verify"],
        "agent": "tester",
    },
    {
        "kernel": "STORE_MANAGER",
        "title": "Store registrar",
        "mandate": (
            "register the finished tree in the Store with its acceptance evidence "
            "and its provenance, and refuse to register a red one"
        ),
        "http_routes": ["/v1/provenance", "/v1/authority"],
        "agent": "store_manager",
    },
]


#: Every answer this platform gives carries the layer it came from. These
#: surfaces answer from the build itself, which is a procedure: the schema and
#: the roster are declared, not retrieved and not computed.
def _authority(label: str) -> Dict[str, Any]:
    return {
        "precedence": precedence_document()["id"],
        "layer": "procedures",
        "label": "procedures:" + label,
    }


def _capability_contracts() -> List[Dict[str, Any]]:
    return [MODELS[capability_id].to_contract() for capability_id in CAPABILITY_IDS]


@router.get("/v1/jobs")
def jobs() -> Dict[str, Any]:
    return {
        "ok": True,
        "kernel": "COLLECTOR",
        "product": PLATFORM["product"],
        "jobs": KERNEL_JOBS,
        "authority": _authority("kernel:jobs"),
    }


@router.get("/v1/catalog")
def catalog() -> Dict[str, Any]:
    return {
        "ok": True,
        "kernel": "COLLECTOR",
        "product": PLATFORM["product"],
        "capabilities": [
            {"id": item["id"], "entity": item["entity"], "blocks": item["blocks"]}
            for item in CAPABILITIES
        ],
        "blocks": dispatch.catalog(),
        "count": len(dispatch.catalog()),
        "authority": _authority("kernel:catalog"),
    }


@router.get("/v1/inventory")
def inventory() -> Dict[str, Any]:
    from pathlib import Path

    lock = Path(__file__).resolve().parents[2] / "blocks.lock.json"
    vendored = sorted(dispatch.vendored_block_paths())
    return {
        "ok": True,
        "kernel": "CLONER",
        "lock": {"path": str(lock), "present": lock.is_file()},
        "vendored": vendored,
        "composed": [item["block_id"] for item in dispatch.catalog()],
        "count": len(dispatch.catalog()),
        "authority": _authority("kernel:inventory"),
    }


@router.get("/v1/capabilities")
def capabilities() -> Dict[str, Any]:
    items = _capability_contracts()
    return {
        "ok": True,
        "kernel": "COLLECTOR",
        "product": PLATFORM["product"],
        "items": items,
        "capabilities": items,
        "count": len(items),
        "authority": _authority("kernel:capabilities"),
    }


@router.get("/v1/gates")
def gates() -> Dict[str, Any]:
    return {
        "ok": True,
        "kernel": "TESTER",
        "runs_over_http": False,
        "product": PLATFORM["product"],
        "gates": [
            {
                "id": "code_green",
                "runs": "pytest -m 'not pilot'",
                "where": "the checkout root",
            },
            {
                "id": "product",
                "runs": "pytest -m pilot against a booted TestClient",
                "where": "in-process, one record per capability",
            },
            {
                "id": "store",
                "runs": "scripts/acceptance.py inside the built image",
                "where": "the Store-built container",
            },
        ],
        "acceptance": {
            "round_trip": "POST creates, GET returns it, for every capability",
            "envelope": ["open", "in_progress", "closed"],
        },
        "authority": _authority("kernel:gates"),
    }


@router.get("/v1/provenance")
def provenance() -> Dict[str, Any]:
    return {
        "ok": True,
        "kernel": "STORE_MANAGER",
        "product": PLATFORM["product"],
        "vertical": PLATFORM["vertical"],
        "app_revision": current_app_revision(),
        "app_mark": current_app_mark(),
        "capability_count": PLATFORM["capability_count"],
        "sources": [
            "vendored Store blocks under vendor/blocks (read-only)",
            "local SQLite through the one STORAGE_PATH root",
        ],
        "authority": _authority("kernel:provenance"),
    }
