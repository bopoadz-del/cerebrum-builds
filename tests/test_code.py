"""CODE gate: imports, routes, handlers. pytest -m 'not pilot'."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from app.schema import REQUIRED_CAPABILITY_IDS, SPECS

pytestmark = pytest.mark.not_pilot

EXPECTED = {
    "airport_readiness",
    "operational_dashboard",
    "ground_workflow_coordination",
    "regulatory_document_control",
    "incident_evidence_tracking",
    "flight_event_orchestration",
    "airport_knowledge_assistant",
}


def test_domain_kernel_is_not_a_stub() -> None:
    from app.domain import (
        crew_function,
        document_retention_days,
        evidence_severity,
        flight_cascade,
        knowledge_source_class,
        readiness_score,
        stand_is_degraded,
        work_order_stage,
    )

    assert readiness_score("open", "turnaround") == 0.45
    assert stand_is_degraded(0.45) is True
    assert readiness_score("closed", "day") == 0.7
    assert work_order_stage("in_progress") == "on_stand"
    assert crew_function("fuel bowser", "alpha") == "fueling"
    assert document_retention_days("certificate") == 1095
    assert evidence_severity("sensor") == "high"
    assert flight_cascade("arrival")["sla_minutes"] == 25
    assert knowledge_source_class("incident on stand", "") == "incident_record"


def test_workspace_imports() -> None:
    from app.main import app
    from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
    from app.store import COLUMNS, list_all, save

    assert app.title == "Airport Operations Platform"
    assert BLOCK_DEFAULT_ACTIONS["audit"] == "log"
    assert BLOCK_DEFAULT_ACTIONS["dashboard"] == "render"
    assert BLOCK_DEFAULT_ACTIONS["vector_search"] == "search"
    assert BLOCK_DEFAULT_ACTIONS["formula_executor"] == "execute"
    assert BLOCK_DEFAULT_ACTIONS["capture"] == "extract"
    assert BLOCK_DEFAULT_ACTIONS["file_hasher"] == "hash"
    assert BLOCK_DEFAULT_ACTIONS["memory"] == "get"
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


def test_full_pilot_authorship_floor() -> None:
    root = Path(__file__).resolve().parents[1] / "app" / "actions"
    authored = [p for p in root.glob("*.py") if p.name != "__init__.py"]
    assert len(authored) >= 5
    assert len(authored) == len(REQUIRED_CAPABILITY_IDS)
    assert {p.stem for p in authored} == EXPECTED
