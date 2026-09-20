"""HTTP routers for the construction platform.

``app/routes.py`` owns the capability surface (one POST/GET/GET-id/PUT/DELETE
per capability plus the kernel job routes). This package is the single mount
point: it composes that capability router with the practice's read-only
operator surfaces, so ``app/main.py`` includes exactly one router at ``/v1``.

The operator surfaces are real HTTP over the same tenant boundary:
``GET /v1/retrieval`` (tenant-scoped search of the practice's own records) and
``POST /v1/authority/resolve`` (precedence.v1 resolution against ranked
claims).
"""

from __future__ import annotations

from fastapi import APIRouter

from app.routes import router as capability_router
from app.routers.operator import router as operator_router

router = APIRouter()
router.include_router(capability_router)
router.include_router(operator_router)

__all__ = ["router"]
