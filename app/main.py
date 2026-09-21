"""CallOps application factory.

One place assembles the platform: the observability substrate (metrics,
Sentry, auth rate limiting), the specific routers before the generic
capability envelope, the console the operators use, and the fail-closed
health check. Migrations run at startup against the one storage root, so a
container that cannot migrate refuses to serve rather than answering 200
over a schema it never applied.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app import config
from app.health import health_response
from app.observability import mount_observability
from app.observe import REQUEST_ID_HEADER
from app.revision import current_app_mark, current_app_revision
from app.routers import domain_routers
from app.routes import router as capability_router

logger = logging.getLogger("callops")

ROOT = Path(__file__).resolve().parents[1]

#: The retrieval surface this product serves, named here as well as in
#: app/routers/retrieval_routes.py so the platform's entry point states what
#: it can answer from: PSI project sheets are ingested at /v1/rag/ingest and
#: quoted at /v1/rag/query and /v1/rag/ground.
RETRIEVAL_SURFACE = ("/v1/rag/ingest", "/v1/rag/query", "/v1/rag/ground", "/v1/rag/corpus")
STATIC_DIR = Path(__file__).resolve().parent / "static"
CONSOLE_INDEX = STATIC_DIR / "index.html"
FRONTEND_DIST = ROOT / "frontend-dist"


def run_migrations() -> str | None:
    from app.migrations import upgrade_head

    return upgrade_head()


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    config.validate_boot()
    revision = run_migrations()
    logger.info(
        json.dumps(
            {
                "event": "startup",
                "revision": revision,
                "app_revision": current_app_revision(),
                "mark": current_app_mark(),
                "storage": config.storage_path(),
            }
        )
    )
    yield


def _document_shared_responses(application: FastAPI) -> None:
    """Document the platform-wide contract in one place.

    Every ``/v1`` route refuses an anonymous caller (401) and refuses a
    malformed or incomplete record (422); the record paths also refuse a
    handler-level decision (409). Writing that into each decorator would be
    twelve copies of the same contract, so it is stated once here and merged
    into the generated document.
    """
    default_openapi = application.openapi

    def openapi() -> Dict[str, Any]:
        document = default_openapi()
        shared = {
            "401": {"description": "no token, or a token bound to no tenant"},
            "422": {"description": "missing required field, value outside a vocabulary, or malformed body"},
        }
        for path, operations in (document.get("paths") or {}).items():
            if not str(path).startswith("/v1/"):
                continue
            for method, operation in operations.items():
                if method not in ("get", "post", "put", "delete", "patch"):
                    continue
                responses = operation.setdefault("responses", {})
                for code, spec in shared.items():
                    responses.setdefault(code, dict(spec))
                if method in ("post", "put") and any(
                    token in str(path) for token in ("{capability}",)
                ):
                    responses.setdefault("409", {"description": "the capability refused the record on domain grounds"})
                if method in ("get", "put", "delete") and "{" in str(path):
                    responses.setdefault("404", {"description": "not this tenant's record"})
        return document

    application.openapi = openapi  # type: ignore[assignment]


def _console_html() -> str:
    if CONSOLE_INDEX.is_file():
        return CONSOLE_INDEX.read_text(encoding="utf-8")
    return (
        "<!doctype html><html><body><h1>CallOps</h1>"
        "<p>The console file app/static/index.html is missing from this build.</p>"
        "</body></html>"
    )


def create_app() -> FastAPI:
    application = FastAPI(
        title=config.PRODUCT_NAME,
        version="1.0.0",
        description=(
            "Outbound AI voice calling for a real-estate brokerage: lead intake "
            "and dial pacing, project-sheet grounded pitches under cite-or-refuse, "
            "the Twilio voice edge, warm transfer to a broker, and the outcome "
            "ledger behind the dashboard."
        ),
        lifespan=lifespan,
    )

    # Substrate first: /metrics, SENTRY_DSN and the auth route rate limit.
    mount_observability(application)

    @application.middleware("http")
    async def correlate(request: Request, call_next):
        """Every response carries a correlation id; every log line too."""
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex[:16]
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        logger.info(
            json.dumps(
                {"event": "request", "request_id": request_id, "path": request.url.path,
                 "method": request.method, "status": response.status_code}
            )
        )
        return response

    @application.get("/health")
    def health() -> JSONResponse:
        return health_response()

    @application.get("/", include_in_schema=False)
    def console() -> HTMLResponse:
        return HTMLResponse(_console_html())

    @application.get("/openapi.json", include_in_schema=False)
    def openapi_mirror() -> Dict[str, Any]:
        """The API description, next to /health rather than under /v1.

        Every ``/v1`` path is authenticated; serving the document from there
        would make one of them open without saying so.
        """
        return application.openapi()

    for router in domain_routers():
        application.include_router(router)
    # The generic envelope goes last so a literal path is never swallowed.
    application.include_router(capability_router)

    _document_shared_responses(application)

    if FRONTEND_DIST.is_dir():
        application.mount("/console", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="console")
    if STATIC_DIR.is_dir():
        application.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @application.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception) -> JSONResponse:  # pragma: no cover
        from app.security import scrub

        logger.exception("unhandled error on %s", request.url.path)
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": scrub(f"{type(exc).__name__}")},
        )

    return application


app = create_app()
