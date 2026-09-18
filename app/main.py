"""Entrypoint for the generated platform.

Runs standalone: uvicorn app.main:app. No factory, no block store, no
outbound dependency at runtime (P1: Delivered platforms run in-process against vendored blocks; local/scripted OCR only; no Store URL, no cloud LLM, no Ollama, no outbound HTTP at runtime.).
Kernel jobs are at GET /v1/jobs.
GET /health is fail-closed (process, disk, DB, Alembic head).
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse

from app.health import health_response
from app.observe import install_observability
from app.routes import router


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


app = FastAPI(title="Boutique Front Desk", lifespan=lifespan)
install_observability(app)
app.include_router(router, prefix="/v1")
try:
    from app.rag_routes import router as rag_router

    app.include_router(rag_router)
except ImportError:
    pass
# Phase 2 client ingestion (chunker + tenant-resolved routes).
try:
    from app.cerebrum_product_kernel.ingestion.router import router as product_ingestion_router

    app.include_router(product_ingestion_router)
except ImportError:
    pass


@app.get("/")
def ui_root():
    here = Path(__file__).resolve().parent
    for candidate in (here / 'static' / 'index.html', here.parent / 'frontend' / 'index.html'):
        if candidate.is_file():
            return FileResponse(candidate, media_type='text/html')
    return HTMLResponse("<!doctype html><html><body><h1>Boutique Front Desk</h1></body></html>")


@app.get("/health")
def health():
    return health_response()
