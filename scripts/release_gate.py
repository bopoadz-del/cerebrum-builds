#!/usr/bin/env python3
"""Release gate: a red build must not become a deployable image.

Run from the repository root, and again inside the image (the Dockerfile does
both). It checks the things that are cheap here and expensive in production:

* the app imports, migrations apply against a throwaway storage root, and
  ``/health`` answers 200 with a real database behind it;
* the entity tables and the handlers agree with ``app/models.py``;
* the console is present and drives routes that exist;
* the committed OpenAPI document matches the routes actually served;
* the deploy contract holds: the image runs the entrypoint, the entrypoint
  migrates before it serves, the healthcheck follows ``$PORT``, the React
  console stage is bundling and its bundle is copied where the app mounts it,
  and no operator ``.env`` can be baked into a layer;
* the code-phase suite is green (``pytest -m "not pilot"``).

Exit code 0 means go. Anything else names what failed.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class Failed(Exception):
    """A gate that did not pass, with the reason the operator needs."""


def check_layout() -> None:
    required = [
        "app/main.py",
        "app/models.py",
        "app/store.py",
        "app/db.py",
        "app/actions",
        "app/routers",
        "app/static/index.html",
        "alembic/versions/0001_baseline.py",
        "docs/openapi.json",
        "tests",
        ".github/workflows/ci.yml",
        "README.md",
        "requirements.txt",
    ]
    missing = [rel for rel in required if not (ROOT / rel).exists()]
    if missing:
        raise Failed("missing: " + ", ".join(missing))


def check_console_drives_routes() -> None:
    html = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
    routes = set(re.findall(r'"(/v1/[^"?]+)', html))
    if len(routes) < 3:
        raise Failed("the console calls fewer than three routes: it is a facade")
    openapi = json.loads((ROOT / "docs" / "openapi.json").read_text(encoding="utf-8"))
    served = set(openapi.get("paths") or {})
    for route in routes:
        cleaned = route.rstrip("/")
        if cleaned.startswith("/v1/formulas/"):
            cleaned = "/v1/formulas/{name}"
        if cleaned in served or f"{cleaned}/" in served:
            continue
        # A capability route is one of the twelve behind the envelope.
        tail = cleaned.rsplit("/", 1)[-1]
        if f"/v1/{{capability}}" in served and cleaned.startswith("/v1/") and tail not in (
            "auth",
            "rag",
            "voice",
            "leads",
            "dial-queue",
            "dashboard",
            "metrics",
            "connectors",
            "authority",
            "settings",
            "blocks",
            "mcp",
            "calls",
            "ledger",
            "formulas",
            "capabilities",
        ):
            continue
        raise Failed(f"the console calls {route}, which is not in docs/openapi.json")


def check_boot() -> None:
    storage = Path(tempfile.mkdtemp(prefix="callops-release-gate-"))
    os.environ["STORAGE_PATH"] = str(storage)
    from app.migrations import current_revision, head_revision, upgrade_head

    upgrade_head()
    assert current_revision() == head_revision(), "migrations did not reach head"
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        health = client.get("/health")
        if health.status_code != 200:
            raise Failed(f"/health answered {health.status_code}: {health.text[:200]}")
        if client.get("/metrics").status_code != 200:
            raise Failed("/metrics did not answer 200")
        if client.get("/").status_code != 200:
            raise Failed("the console did not answer 200")
        if client.post("/v1/lead_intake_and_dial_queue", json={}).status_code != 401:
            raise Failed("an unauthenticated write was not refused with 401")
    from app.models import CAPABILITY_IDS, MODELS

    conn_entities = {model.ENTITY for model in MODELS.values()}
    if conn_entities != set(CAPABILITY_IDS):
        raise Failed("an entity's name is not its capability id")


def check_openapi_matches_served() -> None:
    """The committed document is the one the app serves.

    README points an integrator at ``docs/openapi.json``. A document that has
    drifted from the mounted routes is a description of a platform nobody is
    running, so the two path sets are compared here.
    """
    os.environ.setdefault(
        "STORAGE_PATH", str(Path(tempfile.mkdtemp(prefix="callops-openapi-")))
    )
    committed = json.loads((ROOT / "docs" / "openapi.json").read_text(encoding="utf-8"))
    from app.main import app

    served = set((app.openapi().get("paths") or {}))
    documented = set((committed.get("paths") or {}))
    if served != documented:
        raise Failed(
            "docs/openapi.json is not the document the app serves: "
            f"served-but-undocumented={sorted(served - documented)[:5]} "
            f"documented-but-unserved={sorted(documented - served)[:5]}"
        )


def check_console_bundle() -> None:
    """When a bundle was built, it is a real bundle.

    A bare checkout has no ``frontend-dist`` and says so; the image always
    has one, because the console stage copies it in before the gate runs.
    An empty one means ``/console`` ships broken while ``/`` looks fine.
    """
    bundle = ROOT / "frontend-dist"
    if not bundle.is_dir():
        print("    (no frontend-dist here: the React console is not built in this tree)")
        return
    if not (bundle / "index.html").is_file():
        raise Failed(
            "frontend-dist has no index.html: app/main.py mounts it at /console")
    assets = [p for p in bundle.rglob("*") if p.is_file() and p.name != "index.html"]
    if not assets:
        raise Failed("frontend-dist holds no assets: the console stage did not bundle")
    html = (bundle / "index.html").read_text(encoding="utf-8")
    referenced = re.findall(r'(?:src|href)="([^"]+)"', html)
    if not referenced:
        raise Failed("frontend-dist/index.html references no assets: /console would render nothing")
    off_root = [
        ref
        for ref in referenced
        if re.match(r"https?://", ref) is None and not ref.startswith("/console/")
    ]
    if off_root:
        # Vite's default base is "/": the bundle would ask the root for
        # /assets/*.js, which nothing serves, and /console would load blank.
        raise Failed(
            "frontend-dist/index.html asks for "
            f"{off_root[0]} but the bundle is mounted at /console"
        )


def check_packaging() -> None:
    """The deploy contract, asserted where a red build costs nothing.

    A DevOps team receives this repository and must deploy it without its
    author. Every fact below is silent when it breaks — the container starts
    and serves a stale or empty asset — so each one is written down.
    """
    dockerfile = ROOT / "Dockerfile"
    if not dockerfile.is_file():
        raise Failed("Dockerfile is missing: there is no image to deploy")
    docker = dockerfile.read_text(encoding="utf-8")

    if not re.search(r"ENTRYPOINT\s*\[[^\]]*scripts/entrypoint\.sh", docker):
        raise Failed("scripts/entrypoint.sh is not the image ENTRYPOINT")
    if not re.search(r"^FROM\s+node:", docker, re.MULTILINE):
        raise Failed("no console stage in the Dockerfile: frontend/ is never bundled")
    if "vite build" not in docker:
        raise Failed("the console stage never runs vite build: /console would ship empty")
    if not any(
        dest.rstrip("/").endswith("frontend-dist")
        for _stage, _src, dest in re.findall(
            r"COPY\s+--from=(\S+)\s+(\S+)\s+(\S+)", docker
        )
    ):
        raise Failed(
            "the bundled console is never copied into the runtime image: "
            "app/main.py mounts ROOT/frontend-dist at /console"
        )
    if not (ROOT / "app" / "static" / "index.html").is_file():
        raise Failed("app/static/index.html is missing: / would serve the fallback page")

    entrypoint = ROOT / "scripts" / "entrypoint.sh"
    if not entrypoint.is_file():
        raise Failed("scripts/entrypoint.sh is missing")
    commands = [
        line.strip()
        for line in entrypoint.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    migrated = next((i for i, line in enumerate(commands) if "alembic upgrade head" in line), None)
    serving = next((i for i, line in enumerate(commands) if "uvicorn" in line), None)
    if migrated is None:
        raise Failed("the entrypoint never applies migrations (alembic upgrade head)")
    if serving is None:
        raise Failed("the entrypoint never starts a server")
    if migrated > serving:
        raise Failed("the entrypoint binds the port before the migrations are applied")

    probe = re.search(r"HEALTHCHECK[\s\S]*?(?=\nFROM |\nENTRYPOINT|\n[A-Z]+ENV|\Z)", docker)
    if not probe:
        raise Failed("no HEALTHCHECK: the platform cannot tell ready from running")
    if "PORT" not in probe.group(0):
        raise Failed(
            "the HEALTHCHECK probes a fixed port while the entrypoint binds $PORT: "
            "a container that is serving would be reported unhealthy"
        )
    if "/health" not in probe.group(0):
        raise Failed("the HEALTHCHECK does not probe /health")

    ignore = ROOT / ".dockerignore"
    if not ignore.is_file():
        raise Failed(".dockerignore is missing: COPY . . ships the whole working tree")
    patterns = {
        line.strip()
        for line in ignore.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith(("#", "!"))
    }
    if ".env" not in patterns:
        raise Failed(".dockerignore does not exclude .env: secrets would land in an image layer")
    for folder in ("data", "frontend/node_modules"):
        if folder not in patterns:
            raise Failed(f".dockerignore does not exclude {folder}")
    if (ROOT / ".env").is_file():
        print("    (.env is in this tree; .dockerignore keeps it out of the image — never commit it)")



def check_models_match_tables() -> None:
    from app.store import COLUMNS
    from app.models import MODELS

    for capability, model in MODELS.items():
        if list(COLUMNS.get(capability, [])) != list(model.FIELDS):
            raise Failed(f"{capability}: store columns and model fields disagree")


def check_suite() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-m", "not pilot", "-q"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        tail = (result.stdout or "")[-1500:]
        raise Failed("the code-phase suite is red:\n" + tail)


def main() -> int:
    checks = [
        ("layout", check_layout),
        ("console", check_console_drives_routes),
        ("packaging", check_packaging),
        ("bundle", check_console_bundle),
        ("models", check_models_match_tables),
        ("boot", check_boot),
        ("openapi", check_openapi_matches_served),
        ("suite", check_suite),
    ]
    for name, fn in checks:
        try:
            fn()
        except Failed as exc:
            print(f"RELEASE GATE FAILED [{name}]: {exc}")
            return 1
        except Exception as exc:  # noqa: BLE001 - a gate failure is the report
            print(f"RELEASE GATE FAILED [{name}]: {type(exc).__name__}: {exc}")
            return 1
        print(f"ok [{name}]")
    print("RELEASE GATE: all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
