"""docs/openapi.json is committed and matches the routes actually served."""

from __future__ import annotations

import json
from pathlib import Path

from app.main import app

ROOT = Path(__file__).resolve().parents[1]


def test_the_committed_openapi_matches_the_served_routes():
    committed = json.loads((ROOT / "docs" / "openapi.json").read_text(encoding="utf-8"))
    served = app.openapi()
    assert committed["openapi"].startswith("3.")
    committed_paths = set(committed["paths"])
    served_paths = set(served["paths"])
    assert committed_paths == served_paths, (
        "committed openapi is stale: "
        f"only committed {sorted(committed_paths - served_paths)}; "
        f"only served {sorted(served_paths - committed_paths)}"
    )
    for path in ("/health", "/v1/rag/ingest", "/v1/rag/query", "/v1/capabilities", "/v1/{capability}"):
        assert path in committed_paths, path


def test_every_committed_post_path_documents_its_401_and_422():
    committed = json.loads((ROOT / "docs" / "openapi.json").read_text(encoding="utf-8"))
    for path, operations in committed["paths"].items():
        if not path.startswith("/v1/"):
            continue
        post = operations.get("post")
        if not post:
            continue
        responses = post.get("responses") or {}
        assert "401" in responses, f"{path} does not document its 401"
