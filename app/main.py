"""Entrypoint for the generated platform.

Runs standalone: uvicorn app.main:app. No factory, no block store, no
outbound dependency at runtime (P1: Delivered platforms run in-process against vendored blocks; local/scripted OCR only; no Store URL, no cloud LLM, no Ollama, no outbound HTTP at runtime.).
Kernel jobs are at GET /v1/jobs.
GET /health is fail-closed (process, disk, DB, Alembic head).

RAG surface (tenant-scoped, in-process): POST /v1/rag/ingest and
POST|GET /v1/rag/query, served by app/rag_routes.py over app/retrieval.py.
Capability coverage: app/routers/capabilities.py.

Written by the factory WRITER role (codewhale exec)
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse

from app.health import health_response
from app.observe import install_observability
from app.paths import ensure_runtime_paths
from app.routes import router

# One persistence root, and the sealed-vendor substitution, before any route
# can be called: the vendored Store runtime is deliberately untouched, so the
# platform binds DATA_DIR to STORAGE_PATH and adopts an offline adapter only
# for a sealed module that cannot be imported (app/offline_blocks.py).
ensure_runtime_paths()
from app.offline_blocks import install_offline_block_adapters

install_offline_block_adapters()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Fail-closed: a revision behind head refuses boot.
    from app.migrations import upgrade_head
    from app.observe import configure_logging

    upgrade_head()
    # Platform preconditions, BEFORE any capability can be called
    # (R1c). A block that mints its own id needs that id to exist
    # first; leaving it to each handler is how residential-lettings
    # answered 'Team access denied' from a handler whose calling
    # convention was correct. Never raises: a platform that cannot
    # reach a block at boot still starts and reports the fact.
    try:
        from app.preconditions import ensure_all

        ensure_all()
    except Exception:  # noqa: BLE001 - boot must not die here
        import logging

        logging.getLogger(__name__).exception(
            'platform preconditions did not run'
        )
    # Uvicorn configures logging after import; win it back for JSON lines.
    configure_logging()
    yield


app = FastAPI(title="LexManage", lifespan=lifespan)
install_observability(app)
app.include_router(router, prefix="/v1")
try:
    from app.routers.capabilities import router as capability_router

    app.include_router(capability_router)
except ImportError:  # pragma: no cover - router is part of the delivered tree
    pass
try:
    from app.rag_routes import router as rag_router

    app.include_router(rag_router)
except ImportError:
    pass


@app.get("/")
def ui_root():
    here = Path(__file__).resolve().parent
    for candidate in (here / 'static' / 'index.html', here.parent / 'frontend' / 'index.html'):
        if candidate.is_file():
            return FileResponse(candidate, media_type='text/html')
    return HTMLResponse("<!doctype html><html><body><h1>LexManage</h1></body></html>")


@app.get("/health")
def health():
    return health_response()
