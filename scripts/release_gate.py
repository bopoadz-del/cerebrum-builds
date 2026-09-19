#!/usr/bin/env python3
"""Release gate: run before packaging or deploying.

Written by the factory WRITER role (codewhale exec)

The gate is fail-closed: it refuses to report a shippable tree when the health
surface is degraded, a capability's handler or entity is missing, the authorship
stamp is absent from fewer than five handlers, or the acceptance harness is not
committed. It runs in-process and needs no network.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    import os

    os.environ.setdefault("STORAGE_PATH", tempfile.mkdtemp(prefix="bakery-gate-"))
    os.environ.setdefault("PLATFORM_TOKEN", "dev-local-token")

    from app import store
    from app.actions import CAPABILITY_IDS
    from app.models import ENTITIES, MODELS
    from app.migrations import upgrade_head

    findings = []
    upgrade_head()

    for capability_id in CAPABILITY_IDS:
        if capability_id not in MODELS:
            findings.append(f"{capability_id}: no model")
        if capability_id not in store.COLUMNS:
            findings.append(f"{capability_id}: no store columns")
        if ENTITIES.get(capability_id) not in store.TABLES:
            findings.append(f"{capability_id}: entity not migrated")
        handler = ROOT / "app" / "actions" / f"{capability_id}.py"
        if not handler.is_file():
            findings.append(f"{capability_id}: handler missing")
        elif "Written by the factory WRITER role" not in handler.read_text(encoding="utf-8"):
            findings.append(f"{capability_id}: authorship stamp missing")

    stamped = sum(
        1
        for path in (ROOT / "app" / "actions").glob("*.py")
        if "Written by the factory WRITER role" in path.read_text(encoding="utf-8")
    )
    if stamped < 5:
        findings.append(f"authorship floor: {stamped} stamped handler(s), need 5")

    if not (ROOT / "scripts" / "acceptance.py").is_file():
        findings.append("scripts/acceptance.py missing")
    if not (ROOT / "docs" / "openapi.json").is_file():
        findings.append("docs/openapi.json missing")

    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        health = client.get("/health")
        if health.status_code != 200:
            findings.append(f"/health answered HTTP {health.status_code}")

    payload = {"ok": not findings, "findings": findings, "capabilities": len(CAPABILITY_IDS)}
    print(json.dumps(payload, indent=2))
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
