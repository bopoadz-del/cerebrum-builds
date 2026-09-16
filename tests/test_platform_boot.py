"""The platform boots, and it boots offline.

Written by the factory WRITER role (codewhale exec)
"""

from __future__ import annotations

import os

from app.actions import (
        record_guest_check_in,
        list_todays_check_ins,
)
from helpers import AUTH, client

CAPABILITY_MODULES = (
        record_guest_check_in,
        list_todays_check_ins,
)


def test_capabilities_import():
    for module in CAPABILITY_MODULES:
        assert module.CAPABILITY_ID
    assert {module.CAPABILITY_ID for module in CAPABILITY_MODULES} == {"record_guest_check_in", "list_todays_check_ins"}


def test_health_reports_process_disk_database_and_migrations():
    with client() as api:
        resp = api.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        names = {check["name"] for check in body["checks"]}
        assert {"process", "persistent_disk", "database", "migrations"} <= names
        assert all(check["ok"] for check in body["checks"])


def test_kernel_jobs_roster():
    with client() as api:
        resp = api.get("/v1/jobs")
        assert resp.status_code == 200
        jobs = resp.json()["jobs"]
        by_kernel = {job["kernel"]: job for job in jobs}
        assert set(by_kernel) == {
            "COLLECTOR",
            "CLONER",
            "WRITER",
            "TESTER",
            "STORE_MANAGER",
        }
        for job in jobs:
            assert job["mandate"] and job["http_routes"] and job["agent"]


def test_kernel_http_surfaces_answer():
    with client() as api:
        assert api.get("/v1/catalog").json()["kernel"] == "COLLECTOR"
        inventory = api.get("/v1/inventory")
        assert inventory.status_code == 200
        assert inventory.json()["kernel"] == "CLONER"
        assert "lock" in inventory.json()
        capabilities = api.get("/v1/capabilities")
        assert capabilities.status_code == 200
        assert isinstance(capabilities.json()["items"], list)
        gates = api.get("/v1/gates")
        assert gates.json()["kernel"] == "TESTER"
        assert gates.json()["runs_over_http"] is False
        provenance = api.get("/v1/provenance")
        assert provenance.json()["kernel"] == "STORE_MANAGER"


def test_ui_is_served():
    with client() as api:
        resp = api.get("/")
        assert resp.status_code == 200
        assert "<html" in resp.text.lower() or "<!doctype" in resp.text.lower()


def test_offline_dispatch_loads_every_bound_block():
    """No store env, no network: every bound block loads and executes locally."""
    for var in ("CEREBRUM_API_URL", "CEREBRUM_API_KEY", "CEREBRUM_API_TOKEN"):
        os.environ.pop(var, None)
    from app.dispatch import load_block

    bound = sorted({block for module in CAPABILITY_MODULES for block in module.BLOCK_IDS})
    assert bound
    for block_id in bound:
        load_block(block_id)


def test_every_capability_declares_its_default_actions():
    for module in CAPABILITY_MODULES:
        for block_id in module.BLOCK_IDS:
            assert module.BLOCK_DEFAULT_ACTIONS.get(block_id)
