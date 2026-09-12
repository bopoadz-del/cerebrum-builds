from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def isolated_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "storage"
    root.mkdir()
    monkeypatch.setenv("STORAGE_PATH", str(root))
    monkeypatch.delenv("VECTOR_DB_URL", raising=False)
    monkeypatch.setenv("VECTOR_DB_URL", "")
    from app.store import reset_connection

    reset_connection()
    return root


@pytest.fixture
def client(isolated_storage: Path) -> TestClient:
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
