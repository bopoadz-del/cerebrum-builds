"""CODE gate: imports, routes, handlers. pytest -m 'not pilot'."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from app.schema import REQUIRED_CAPABILITY_IDS, SPECS

pytestmark = pytest.mark.not_pilot

EXPECTED = {
    "productivity_core",
    "audit",
}


def test_domain_kernel_is_not_a_stub() -> None:
    from app.domain import (
        allowed_next_status,
        audit_category,
        matches_keyword,
        note_summary,
        preview,
        word_count,
    )

    assert word_count("save a note") == 3
    assert word_count("sample", "sample") == 2
    assert preview("short") == "short"
    assert preview("x" * 80).endswith("…")
    assert matches_keyword("Meeting notes", "keyword search body", "keyword")
    assert not matches_keyword("Meeting notes", "nothing here", "invoice")
    assert "status=open" in note_summary("stand-up", "talking points", "open")
    assert allowed_next_status("open") == ("in_progress",)
    assert audit_category("bogus") == "data_access"
    assert audit_category("auth") == "auth"


def test_workspace_imports() -> None:
    from app.main import app
    from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
    from app.store import COLUMNS, list_all, save

    assert app.title == "Productivity Platform"
    assert BLOCK_DEFAULT_ACTIONS["audit"] == "log"
    assert BLOCK_DEFAULT_ACTIONS["workflow"] == "run"
    assert BLOCK_DEFAULT_ACTIONS["event_bus"] == "publish"
    assert BLOCK_DEFAULT_ACTIONS["vector_search"] == "search"
    assert BLOCK_DEFAULT_ACTIONS["formula_executor"] == "execute"
    assert BLOCK_DEFAULT_ACTIONS["capture"] == "extract"
    assert BLOCK_DEFAULT_ACTIONS["storage"] == "store"
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
    assert SPECS["productivity_core"]["BLOCK_IDS"] == []
    assert SPECS["audit"]["BLOCK_IDS"] == ["audit"]


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
    assert len(authored) >= 2
    assert len(authored) == len(REQUIRED_CAPABILITY_IDS)
    assert {p.stem for p in authored} == EXPECTED
