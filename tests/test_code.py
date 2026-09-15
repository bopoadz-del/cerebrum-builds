"""CODE gate: imports, routes, handlers. pytest -m 'not pilot'."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from app.schema import REQUIRED_CAPABILITY_IDS, SPECS

pytestmark = pytest.mark.not_pilot

EXPECTED = {
    "automotive_core",
    "dashboard",
    "team",
    "audit",
}


def test_domain_kernel_is_not_a_stub() -> None:
    from app.domain import (
        branch_stock,
        close_rate,
        lead_score,
        list_price,
        monthly_payment,
        odometer_miles,
        seat_count,
        testdrive_hold_minutes,
        units_on_lot,
    )

    assert list_price("new", "open") == 42000.0
    assert list_price("used", "closed") == 22785.0
    assert monthly_payment("new", "open") == 829.67
    assert testdrive_hold_minutes("certified") == 40
    assert odometer_miles("used") == 28400
    assert lead_score("new") == 0.82
    assert branch_stock("sample") == 14
    assert units_on_lot("week") == 31
    assert close_rate("in_progress") == 0.41
    assert seat_count("finance") == 4


def test_workspace_imports() -> None:
    from app.main import app
    from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
    from app.store import COLUMNS, list_all, save

    assert app.title == "Automotive Platform"
    assert BLOCK_DEFAULT_ACTIONS["dashboard"] == "render"
    assert BLOCK_DEFAULT_ACTIONS["team"] == "create_team"
    assert BLOCK_DEFAULT_ACTIONS["audit"] == "log"
    assert BLOCK_DEFAULT_ACTIONS["vector_search"] == "search"
    assert BLOCK_DEFAULT_ACTIONS["formula_executor"] == "execute"
    assert BLOCK_DEFAULT_ACTIONS["capture"] == "extract"
    assert BLOCK_DEFAULT_ACTIONS["storage"] == "store"
    assert BLOCK_DEFAULT_ACTIONS["workflow"] == "run"
    for capability_id in REQUIRED_CAPABILITY_IDS:
        assert capability_id in COLUMNS
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


def test_no_airport_or_retail_product_ids() -> None:
    root = Path(__file__).resolve().parents[1]
    forbidden = (
        "airport_readiness",
        "inventory_tracking",
        "Retail Ops Tracker",
        "Airport Operations Platform",
        "Hotel Booking Platform",
        "Veterinary Care Platform",
    )
    app_text = (root / "app" / "main.py").read_text(encoding="utf-8")
    for token in forbidden:
        assert token not in app_text
    leftover = [
        p.name
        for p in (root / "app" / "actions").glob("*.py")
        if p.stem.startswith("airport")
        or p.stem
        in {
            "inventory_tracking",
            "order_management",
            "booking_management",
            "property_management",
        }
    ]
    assert leftover == []


def test_full_pilot_authorship_floor() -> None:
    root = Path(__file__).resolve().parents[1] / "app" / "actions"
    authored = [p for p in root.glob("*.py") if p.name != "__init__.py"]
    assert len(authored) >= 4
    assert len(authored) == len(REQUIRED_CAPABILITY_IDS)
    assert {p.stem for p in authored} == EXPECTED
