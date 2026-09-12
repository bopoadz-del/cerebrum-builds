"""CODE gate: imports, routes, handlers. pytest -m 'not pilot'."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from app.schema import REQUIRED_CAPABILITY_IDS, SPECS

pytestmark = pytest.mark.not_pilot


def test_workspace_imports() -> None:
    from app.main import app
    from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
    from app.store import COLUMNS, list_all, save

    assert app.title == "Product Platform"
    assert BLOCK_DEFAULT_ACTIONS["audit"] == "log"
    assert BLOCK_DEFAULT_ACTIONS["vector_search"] == "search"
    assert BLOCK_DEFAULT_ACTIONS["formula_executor"] == "execute"
    assert BLOCK_DEFAULT_ACTIONS["capture"] == "extract"
    assert "product_core" in COLUMNS
    assert "audit" in COLUMNS
    assert callable(execute)
    assert callable(save)
    assert callable(list_all)


def test_every_capability_has_handler_source() -> None:
    root = Path(__file__).resolve().parents[1] / "app" / "actions"
    for capability_id in REQUIRED_CAPABILITY_IDS:
        path = root / f"{capability_id}.py"
        assert path.is_file(), f"missing handler {capability_id}"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
        assert "handle" in names


def test_specs_envelope_vocabulary() -> None:
    for spec in SPECS.values():
        allowed = spec["CONSTRAINTS"]["status"]["allowed_values"]
        assert allowed == ["open", "in_progress", "closed"]
        assert "reference" in spec["FIELDS"]
        assert spec["entity"] == spec["id"]


def test_rag_paths_quoted_in_source() -> None:
    text = (Path(__file__).resolve().parents[1] / "app" / "rag_routes.py").read_text(
        encoding="utf-8"
    )
    assert "/v1/rag/ingest" in text
    assert "/v1/rag/query" in text
    assert "/v1/steward/rag/ingest" in text
    assert "/v1/steward/rag/query" in text


def test_actions_init_has_no_eager_reexport() -> None:
    text = (Path(__file__).resolve().parents[1] / "app" / "actions" / "__init__.py").read_text(
        encoding="utf-8"
    )
    assert "from app.actions import" not in text


def test_product_core_missing_amounts_stay_absent(isolated_storage: Path) -> None:
    from app.actions.product_core import handle

    result = handle(
        {
            "reference": "6100",
            "status": "open",
            "account_name": "opex payroll",
        }
    )
    assert result["ok"] is True
    bva = result["record"]["budget_vs_actual"]
    assert bva["budget"] is None
    assert bva["actual"] is None
    assert bva["variance"] is None
    assert bva["variance_pct"] is None
    assert bva["inputs_complete"] is False
    cash = result["record"]["cash_forecast"]
    assert cash["opening"] is None
    assert cash["outflows"] is None
    assert cash["closing"] is None


def test_product_core_computes_budget_variance(isolated_storage: Path) -> None:
    from app.actions.product_core import handle

    result = handle(
        {
            "reference": "6100",
            "status": "open",
            "account_name": "opex payroll",
            "period": "2026-09",
            "budget_amount": 100,
            "actual_amount": 80,
        }
    )
    assert result["ok"] is True
    bva = result["record"]["budget_vs_actual"]
    assert bva["variance"] == -20
    assert bva["direction"] == "favorable"
    assert bva["inputs_complete"] is True
    cash = result["record"]["cash_forecast"]
    assert cash["opening"] == 100
    assert cash["outflows"] == 80
    assert cash["closing"] == 20
    assert cash["inflows"] is None


def test_admin_export_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    monkeypatch.delenv("API_TOKEN", raising=False)
    monkeypatch.delenv("CEREBRUM_API_TOKEN", raising=False)
    with TestClient(app) as client:
        denied_missing = client.get("/v1/admin/export")
        denied_placeholder = client.get(
            "/v1/admin/export", headers={"x-api-token": "sample"}
        )
    assert denied_missing.status_code == 401
    assert denied_placeholder.status_code == 401

    monkeypatch.setenv("API_TOKEN", "financeops-admin")
    with TestClient(app) as client:
        denied_wrong = client.get("/v1/admin/export", headers={"x-api-token": "nope"})
        allowed = client.get("/v1/admin/export", headers={"x-api-token": "financeops-admin"})
    assert denied_wrong.status_code == 401
    assert allowed.status_code == 200
    assert allowed.json().get("ok") is True
    assert allowed.json().get("principal") == {"subject": "operator", "role": "admin"}


def test_mutating_routes_fail_closed(monkeypatch: pytest.MonkeyPatch, isolated_storage: Path) -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    monkeypatch.setenv("API_TOKEN", "financeops-admin")
    with TestClient(app) as client:
        denied = client.post("/v1/product_core", json={"reference": "sample", "status": "open"})
        denied_ingest = client.post(
            "/v1/rag/ingest",
            json={"layer": 1, "doc_id": "x", "title": "x", "text": "budget vs actual"},
        )
        allowed = client.post(
            "/v1/product_core",
            json={"reference": "sample", "status": "open"},
            headers={"x-api-token": "financeops-admin"},
        )
    assert denied.status_code == 401
    assert denied_ingest.status_code == 401
    assert allowed.status_code == 200
    assert allowed.json().get("ok") is not False
    assert allowed.json().get("actor") == "operator"


def test_cors_allowlist_refuses_wildcard(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.auth import cors_allowlist

    monkeypatch.delenv("CORS_ALLOWLIST", raising=False)
    assert cors_allowlist() == []

    monkeypatch.setenv("CORS_ALLOWLIST", "*,https://finance.example,http://localhost:8000")
    assert "*" not in cors_allowlist()
    assert cors_allowlist() == ["https://finance.example", "http://localhost:8000"]


def test_cors_preflight_empty_deny(monkeypatch: pytest.MonkeyPatch, isolated_storage: Path) -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    monkeypatch.delenv("CORS_ALLOWLIST", raising=False)
    with TestClient(app) as client:
        denied = client.options(
            "/v1/product_core",
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": "POST",
            },
        )
        listed = client.options(
            "/v1/product_core",
            headers={
                "Origin": "http://localhost:8000",
                "Access-Control-Request-Method": "POST",
            },
        )
    assert denied.headers.get("access-control-allow-origin") is None
    assert listed.headers.get("access-control-allow-origin") is None

    monkeypatch.setenv("CORS_ALLOWLIST", "http://localhost:8000")
    with TestClient(app) as client:
        allowed = client.options(
            "/v1/product_core",
            headers={
                "Origin": "http://localhost:8000",
                "Access-Control-Request-Method": "POST",
            },
        )
        starred = client.options(
            "/v1/product_core",
            headers={
                "Origin": "*",
                "Access-Control-Request-Method": "POST",
            },
        )
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:8000"
    assert starred.headers.get("access-control-allow-origin") is None


def test_audit_input_requires_principal() -> None:
    from app.auth import Principal, bind_principal, reset_principal
    from app.block_inputs import audit_input

    reset_principal()
    with pytest.raises(RuntimeError, match="authenticated principal required"):
        audit_input({"reference": "sample", "status": "open", "user_id": "attacker"})

    bind_principal(Principal(subject="operator", role="admin"))
    bound = audit_input({"reference": "sample", "status": "open", "user_id": "attacker"})
    assert bound["user_id"] == "operator"
    assert bound["details"]["actor"] == "operator"
    assert bound["details"]["claimed_actor"]["user_id"] == "attacker"
