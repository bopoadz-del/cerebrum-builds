"""Automotive Platform FastAPI entry. Bind 0.0.0.0:$PORT on Render."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.auth import install_cors
from app.health import evaluate_health
from app.observe import RequestIdMiddleware
from app.rag_routes import router as rag_router
from app.routes import router as capability_router
from app.store import reset_connection, storage_root

STATIC_DIR = Path(__file__).resolve().parent / "static"


def _run_migrations() -> None:
    reset_connection()
    try:
        from app.migrations import upgrade_head

        upgrade_head()
    except Exception:
        pass


@asynccontextmanager
async def lifespan(_app: FastAPI):
    storage_root()
    _run_migrations()
    yield


app = FastAPI(
    title="Automotive Platform",
    version="1.0.0",
    description=(
        "Cerebrum Automotive Platform — vehicle inventory, leads, test-drives, "
        "financing, and a sales-team dashboard. Mutations require a bearer operator token."
    ),
    lifespan=lifespan,
)
install_cors(app)
app.add_middleware(RequestIdMiddleware)
app.include_router(capability_router)
app.include_router(rag_router)

if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/health")
def health() -> JSONResponse:
    code, body = evaluate_health()
    return JSONResponse(status_code=code, content=body)


@app.get("/", response_class=HTMLResponse)
def ui_index() -> HTMLResponse:
    index = STATIC_DIR / "index.html"
    if index.is_file():
        return HTMLResponse(index.read_text(encoding="utf-8"))
    raise HTTPException(status_code=503, detail="ui missing")


@app.get("/ui", response_class=HTMLResponse)
def ui_alias() -> HTMLResponse:
    return ui_index()


@app.get("/openapi.json", include_in_schema=False)
def committed_openapi_fallback():
    docs_copy = Path(__file__).resolve().parents[1] / "docs" / "openapi.json"
    if docs_copy.is_file():
        return FileResponse(docs_copy)
    return app.openapi()
