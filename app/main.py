"""Cerebrum Car Dealership FastAPI entry. Bind 0.0.0.0:$PORT on Render."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.routes import router as capability_router
from app.store import db_path, ensure_schema, reset_connection, storage_root

STATIC_DIR = Path(__file__).resolve().parent / "static"


def _run_migrations() -> None:
    reset_connection()
    ensure_schema()
    try:
        from alembic import command
        from alembic.config import Config

        ini = Path(__file__).resolve().parents[1] / "alembic.ini"
        if ini.is_file():
            cfg = Config(str(ini))
            cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path()}")
            command.upgrade(cfg, "head")
    except Exception:
        ensure_schema()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    storage_root()
    _run_migrations()
    yield


app = FastAPI(
    title="Car Dealership Platform",
    version="1.0.0",
    description="Cerebrum Car Dealership — vehicle inventory, pipeline, quotes, service, CRM, deal packs",
    lifespan=lifespan,
)
app.include_router(capability_router)


@app.get("/health")
def health() -> dict:
    root = storage_root()
    if not os.access(root, os.W_OK):
        raise HTTPException(status_code=503, detail="storage not writable")
    try:
        ensure_schema()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"schema unavailable: {exc}") from exc
    return {"ok": True, "status": "ok", "storage": str(root), "db": str(db_path())}
