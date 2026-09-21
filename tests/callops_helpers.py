"""Shared test helpers: one isolated storage root, one migrated schema, two tenants.

This lives beside conftest.py rather than inside it on purpose. The factory's
own TESTER role may rewrite ``tests/conftest.py`` when it emits the code-phase
suite; a helper module the product owns survives that, so the platform's own
tests keep measuring a migrated schema instead of an empty directory.

The platform's single storage root is ``STORAGE_PATH``, so the suite points
it at a temporary directory *before* ``app`` is imported and migrates once.
No test writes to the developer's ``./data`` and no test shares state with
the next one through an unexpected file.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

#: Set before app import: app/store.py reads STORAGE_PATH at call time, but
#: alembic.ini and app/db.py must agree from the first connection.
_TMP = Path(tempfile.mkdtemp(prefix="callops-tests-"))
os.environ.setdefault("STORAGE_PATH", str(_TMP / "data"))
os.environ.setdefault("PLATFORM_TOKEN", "dev-local-token")
os.environ.setdefault("PLATFORM_TOKEN_B", "dev-local-token-b")
os.environ.setdefault("PLATFORM_TENANT", "psi")
os.environ.setdefault("PLATFORM_TENANT_B", "other-brokerage")
os.environ.setdefault("SALES_CHANNEL_WEBHOOK", "")

from app.migrations import upgrade_head  # noqa: E402
from app import store  # noqa: E402
from app.models import CAPABILITY_IDS, MODELS  # noqa: E402

upgrade_head()

TENANT = os.environ["PLATFORM_TENANT"]
OTHER_TENANT = os.environ["PLATFORM_TENANT_B"]
AUTH = {"Authorization": "Bearer " + os.environ["PLATFORM_TOKEN"]}
OTHER_AUTH = {"Authorization": "Bearer " + os.environ["PLATFORM_TOKEN_B"]}


@pytest.fixture(scope="session")
def storage_root() -> Path:
    return Path(os.environ["STORAGE_PATH"])


@pytest.fixture()
def client():
    """A TestClient over the app, entering its lifespan (migrations included)."""
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


def payload_for(capability_id: str, **overrides) -> dict:
    """A valid record for one capability, from its own contract."""
    from app.domain_ops import sample_payload

    body = sample_payload(capability_id)
    body.update(overrides)
    return body


def required_of(capability_id: str) -> list:
    return list(MODELS[capability_id].REQUIRED)


def vocab_of(capability_id: str) -> tuple:
    for name, values in MODELS[capability_id].ALLOWED_VALUES.items():
        return name, list(values)
    return "", []
