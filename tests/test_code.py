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
