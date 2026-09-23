"""HTTP routers over the capability handlers.

Specific paths are registered before the generic ``/v1/{capability}``
envelope in ``app/routes.py``, so a literal route such as
``/v1/rag/ingest`` is never swallowed by the parameterised one.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter

from app.routers import (
    dashboard_routes,
    kernel_routes,
    leads_routes,
    platform_routes,
    retrieval_routes,
    voice_routes,
)

ROUTERS: List[APIRouter] = [
    # Kernel surfaces first: /v1/jobs, /v1/catalog, /v1/inventory,
    # /v1/capabilities, /v1/gates and /v1/provenance are literal paths that
    # must never fall through to the generic /v1/{capability} envelope.
    kernel_routes.router,
    platform_routes.router,
    retrieval_routes.router,
    voice_routes.router,
    leads_routes.router,
    dashboard_routes.router,
]


def domain_routers() -> List[APIRouter]:
    return list(ROUTERS)
