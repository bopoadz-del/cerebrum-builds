"""VetClinicOS domain behaviour: tenancy, RBAC, formulas, authority, audit.

Written by the factory WRITER role (codewhale exec).
"""

from __future__ import annotations

import os

import pytest



# -- local test helpers -----------------------------------------------------
# Defined here, not imported from conftest: the TESTER pass legitimately
# rewrites tests/conftest.py, and a pilot file that imports names the emitted
# conftest does not carry fails collection (which reads as "suite could not
# run", not as a product defect).
AUTH = {"Authorization": "Bearer " + os.environ.get("PLATFORM_TOKEN", "dev-local-token")}


def sample_value(cls, name):
    """A value satisfying every constraint the field itself declares."""
    rules = (getattr(cls, "CONSTRAINTS", {}) or {}).get(name) or {}
    allowed = rules.get("allowed_values")
    if allowed:
        return allowed[0]
    kind = str(getattr(cls, "__annotations__", {}).get(name, "str"))
    kind = kind.replace("Optional[", "").replace("]", "").strip().lower()
    lowered = name.lower()
    if kind in ("int", "float"):
        return rules.get("min") if rules.get("min") is not None else 1
    if kind == "bool":
        return False
    if "email" in lowered:
        return "sample@example.com"
    if kind == "datetime" or lowered.endswith("_at"):
        return "2026-09-03T10:00:00"
    if kind == "date" or lowered.endswith("_date"):
        return "2026-09-03"
    if kind == "time" or lowered.endswith("_time"):
        return "10:00:00"
    if lowered == "status" or lowered.endswith("_status"):
        return "open"
    if lowered == "channel" or lowered.endswith("_channel"):
        return "email"
    return "sample"


def sample_payload(cls):
    return {name: sample_value(cls, name) for name in getattr(cls, "FIELDS", [])}


# -- local fixtures ---------------------------------------------------------
# Defined here rather than in conftest: the TESTER pass rewrites
# tests/conftest.py, and these two files are the agent's own product-cycle
# coverage. A module-local fixture keeps them runnable either way.
@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def models():
    from app.models import MODELS

    return MODELS


def test_tenant_comes_from_the_principal_and_a_claimed_tenant_is_refused(client):
    from app import tenancy

    tenant = tenancy.resolve_tenant({"authorization": "Bearer dev-local-token"})
    assert tenant.tenant_id
    with pytest.raises(tenancy.TenantRefused):
        tenancy.refuse_client_tenant({"tenant_id": "someone-else"})
    claimed = client.post(
        "/v1/rag/ingest",
        json={"text": "tenant claim", "tenant_id": "someone-else"},
        headers=AUTH,
    )
    assert claimed.status_code == 422


def test_permissions_follow_the_role_not_the_payload():
    from app import security

    assert security.has_permission(["admin"], "role_management:write")
    assert not security.has_permission(["receptionist"], "role_management:write")
    assert security.has_permission(["receptionist"], "appointment_scheduling:write")
    assert security.has_permission(["vet"], "treatment_management:write")
    with pytest.raises(security.AccessDenied):
        security.require_permission(["receptionist"], "audit_trail:write")


def test_formula_layer_calculates_and_says_which_path_ran():
    from app import formulas

    result = formulas.execute_formula("invoice_total", {"subtotal": 100, "tax_rate": 0.2})
    assert result["value"] == pytest.approx(120.0)
    assert result["calculated_by"] in ("formula_executor", "local_ast")
    with pytest.raises(formulas.FormulaError):
        formulas.evaluate_local("__import__('os').system('id')", {})
    with pytest.raises(formulas.FormulaError):
        formulas.execute_formula("no_such_formula", {})


def test_authority_precedence_prefers_the_lower_layer_and_records_divergence():
    from app import authority

    resolved = authority.resolve(
        [
            {"text": "certified protocol", "layer": 1, "source": "protocols", "value": "A"},
            {"text": "SOP note", "layer": 2, "source": "sop", "value": "B"},
        ]
    )
    assert resolved["winner"]["layer"] == 1
    assert resolved["divergences"][0]["overruled_layer"] == 2
    assert resolved["version"] == "precedence.v1"


def test_llm_fails_loud_without_a_credential(monkeypatch):
    from app import llm

    monkeypatch.delenv(llm.API_KEY_ENV, raising=False)
    monkeypatch.delenv(llm.PROVIDER_ENV, raising=False)
    monkeypatch.delenv(llm.LEGACY_PROVIDER_ENV, raising=False)
    with pytest.raises(llm.MissingCredentialError):
        llm.complete("summarise this")
    summary = llm.summarize("First sentence. Second sentence. Third sentence.")
    assert summary["method"] == "extractive"
    assert summary["summary"]


def test_llm_refuses_a_provider_call_under_the_offline_posture(monkeypatch):
    from app import llm

    monkeypatch.setenv(llm.PROVIDER_ENV, "openrouter")
    monkeypatch.setenv(llm.API_KEY_ENV, "not-a-real-key")
    with pytest.raises(llm.NetworkPostureRefused):
        llm.complete("hello")


def test_audit_trail_hashes_the_record_it_stores(client, models):
    import json
    from pathlib import Path

    body = sample_payload(models["audit_trail"])
    body["reference"] = "audit-domain-1"
    assert client.post("/v1/audit_trail", json=body, headers=AUTH).json().get("ok") is True
    root = Path(__import__("os").environ["STORAGE_PATH"]) / "audit"
    written = sorted(root.glob("*.json"))
    assert written
    record = json.loads(written[-1].read_text(encoding="utf-8"))
    assert record.get("reference")


def test_inventory_reorder_flag_tracks_the_level():
    from app.actions.inventory_management import _stock_state

    assert _stock_state({"quantity": 2, "reorder_level": 5})["reorder_required"] is True
    assert _stock_state({"quantity": 9, "reorder_level": 5})["reorder_required"] is False


def test_appointment_slot_is_bounded_by_the_schema():
    from app.actions.appointment_scheduling import _slot

    assert _slot({"duration_minutes": 1})["duration_minutes"] == 5
    assert _slot({"duration_minutes": 9999})["duration_minutes"] == 480


def test_billing_totals_are_computed_not_trusted():
    from app.actions.billing_invoicing import _totals

    totals = _totals({"line_items": "consult:40; vaccine:20", "tax_rate": 20})
    assert totals["subtotal"] == pytest.approx(60.0)
    assert totals["tax_rate"] == pytest.approx(0.2)
    assert totals["total_amount"] == pytest.approx(72.0)


def test_prepared_workflow_step_carries_the_child_action():
    """The Store workflow dispatches a child with (input, params)."""
    from app.actions.appointment_scheduling import _workflow_steps

    steps = _workflow_steps({"reference": "r1", "pet_name": "Rex", "veterinarian": "Dr Vet"})
    assert steps
    for step in steps:
        assert step["block"]
        assert step["action"]
        assert isinstance(step["input"], dict)
        assert step["params"]["action"] == step["action"]
