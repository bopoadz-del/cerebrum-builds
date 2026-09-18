"""Every block this platform binds loads; the recorded defects are honest."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

from app.vendor_health import KNOWN_DEFECTS, probe_block, report

ROOT = Path(__file__).resolve().parents[1]


def bound_blocks():
    from app.models import MODELS

    blocks = []
    for capability_id in MODELS:
        module = importlib.import_module("app.actions." + capability_id)
        for block_id in getattr(module, "BLOCK_IDS", ()) or ():
            if block_id not in blocks:
                blocks.append(block_id)
    return sorted(blocks)


def test_every_bound_block_is_available():
    body = report(bound_blocks())
    assert body["unavailable"] == []
    for probe in body["blocks"]:
        assert probe["available"], probe


def test_defect_registry_matches_the_blockers_document():
    document = json.loads((ROOT / "docs" / "blockers.json").read_text(encoding="utf-8"))
    recorded = {item["block_id"] for item in document["blockers"]}
    assert recorded == set(KNOWN_DEFECTS), (recorded, set(KNOWN_DEFECTS))
    for item in document["blockers"]:
        assert item["evidence"] and item["mitigation"] and item["owner_action"]


def test_no_defective_block_is_bound():
    assert not (set(KNOWN_DEFECTS) & set(bound_blocks()))


def test_probe_names_the_defect_rather_than_raising():
    for block_id in KNOWN_DEFECTS:
        probe = probe_block(block_id)
        assert probe["available"] is False
        assert probe["error"]
        assert probe["defect"] == KNOWN_DEFECTS[block_id]


def test_health_endpoint_reports_the_same_defects():
    from fastapi.testclient import TestClient

    from app.main import app
    from tests.helpers import AUTH

    with TestClient(app) as client:
        resp = client.get("/v1/vendor_health", headers=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    assert body["unavailable"] == []
    assert set(body["known_defects_not_bound"]) == set(KNOWN_DEFECTS)
