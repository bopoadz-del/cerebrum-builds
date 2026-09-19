"""Entrypoint for the Bakery Chain Operations & Delivery Platform.

Written by the factory WRITER role (codewhale exec)

Runs standalone: ``uvicorn app.main:app``. No factory, no block store, no
outbound dependency at runtime — blocks execute in-process from the source
vendored at build time.

* ``GET /health`` is fail-closed (process, disk, database, migrations, blocks)
  and carries the revision/mark this process is actually running as.
* every answered request is logged as one JSON line carrying its correlation id
  (``X-Request-Id``), minted when the caller did not send one.
* ``GET /`` serves the operator console (static HTML when the frontend build is
  not present, the console summary otherwise).

Scope
-----
READS  ``STORAGE_PATH``, ``vendor/blocks/**`` (import only), ``app/static``,
       the request headers.
WRITES the database through ``app.store``; the log stream.
NEVER  network, HTTP store callbacks.
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse

from app.health import health_response
from app.observe import REQUEST_ID_HEADER, configure_logging, log_request
from app.routers.capabilities import router

PRODUCT_NAME = "Bakery Chain Operations & Delivery Platform"

configure_logging()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Fail-closed boot: the schema must reach head before a route is served."""
    from app.migrations import upgrade_head

    upgrade_head()
    yield


app = FastAPI(title=PRODUCT_NAME, version="1.0.0", lifespan=lifespan)


@app.middleware("http")
async def correlate_requests(request: Request, call_next):
    """One correlation id per request: echoed, logged, never invented twice."""
    request_id = (request.headers.get(REQUEST_ID_HEADER) or "").strip() or uuid.uuid4().hex[:12]
    response = await call_next(request)
    response.headers[REQUEST_ID_HEADER] = request_id
    log_request(request_id, request.method, request.url.path, response.status_code)
    return response


app.include_router(router, prefix="/v1")

# The RAG surface is its own module (ingest/query over the vendored vector
# search runtime). Kept optional so a stripped tree still boots.
try:
    from app.rag_routes import router as rag_router

    app.include_router(rag_router)
except ImportError:  # pragma: no cover - only when the surface is stripped
    pass


@app.get("/")
def ui_root():
    here = Path(__file__).resolve().parent
    for candidate in (
        here / "static" / "index.html",
        here.parent / "frontend" / "index.html",
    ):
        if candidate.is_file():
            return FileResponse(candidate, media_type="text/html")
    return HTMLResponse(
        "<!doctype html><html><body><h1>"
        + PRODUCT_NAME
        + "</h1><p>Operator console not built; the API is at /v1.</p></body></html>"
    )


@app.get("/health")
def health():
    return health_response()
