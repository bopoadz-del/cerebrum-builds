"""Productivity Platform FastAPI entry. Bind 0.0.0.0:$PORT on Render."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.auth import install_cors
from app.health import evaluate_health
from app.migrations import upgrade_head
from app.observe import RequestIdMiddleware, configure_request_logging
from app.rag_routes import router as rag_router
from app.routes import router as capability_router
from app.store import reset_connection, storage_path

STATIC_DIR = Path(__file__).resolve().parent / "static"


def _run_migrations() -> None:
    reset_connection()
    try:
        upgrade_head()
    except Exception:
        reset_connection()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_request_logging()
    if storage_path().exists() and storage_path().is_dir():
        _run_migrations()
    elif not storage_path().exists():
        try:
            storage_path().mkdir(parents=True, exist_ok=True)
            _run_migrations()
        except OSError:
            pass
    yield


app = FastAPI(
    title="Productivity Platform",
    version="1.0.0",
    description=(
        "Cerebrum Productivity Platform — a tiny notes app: save a note with a "
        "title and body, list notes, search notes by keyword, delete a note. "
        "Mutations require a bearer operator token."
    ),
    lifespan=lifespan,
)
install_cors(app)
app.add_middleware(RequestIdMiddleware)
app.include_router(rag_router)
app.include_router(capability_router)

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
    # BA jail: committed spec lives only at docs/openapi.json.
    docs_copy = Path(__file__).resolve().parents[1] / "docs" / "openapi.json"
    if docs_copy.is_file():
        return FileResponse(docs_copy)
    root_copy = Path(__file__).resolve().parents[1] / "openapi.json"
    if root_copy.is_file():
        return FileResponse(root_copy)
    return app.openapi()
