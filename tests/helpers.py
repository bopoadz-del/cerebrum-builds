"""Shared helpers for the code-phase suite.

Written by the factory WRITER role (codewhale exec)
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import store  # noqa: E402
from app.main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

TOKEN = "dev-local-token"
AUTH = {"Authorization": "Bearer " + TOKEN}

#: A record built from each capability's own FIELDS + CONSTRAINTS, the same
#: sampling rule the factory's writer-behaviour gate uses.
SAMPLES: Dict[str, Dict[str, Any]] = {
    "record_check_in": {'reference': 'sample', 'guest_name': 'sample', 'room_number': 'sample', 'checked_in_at': '2026-09-03T10:00:00', 'guests_count': 1, 'status': 'open', 'notes': 'sample'},
    "list_todays_check_ins": {'reference': 'sample', 'check_in_date': '2026-09-03', 'room_number': 'sample', 'guest_name': 'sample', 'check_in_count': 0, 'status': 'open', 'notes': 'sample'},
}


def client() -> TestClient:
    """A client that enters lifespan, so migrations and preconditions run."""
    return TestClient(app)


def entity_of(capability_id: str) -> str:
    from app.models import MODELS

    cls = MODELS[capability_id]
    return str(getattr(cls, "ENTITY", capability_id))


def rows(capability_id: str) -> List[Dict[str, Any]]:
    return store.list_all(entity_of(capability_id))
