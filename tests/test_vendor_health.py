"""Every block this platform binds loads; the recorded defects are honest.

Written by the factory WRITER role (codewhale exec)
"""

from __future__ import annotations

import json
from pathlib import Path

from app.vendor_health import KNOWN_DEFECTS, probe_block, report

ROOT = Path(__file__).resolve().parents[1]


def bound_blocks():
    import importlib

    from app.actions import __all__ as capability_names

    blocks = []
    for name in capability_names:
        module = importlib.import_module("app.actions." + name)
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
