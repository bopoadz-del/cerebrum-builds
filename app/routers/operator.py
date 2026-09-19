"""Operator surfaces: tenant-scoped retrieval and precedence.v1 resolution.

Both routes authenticate with the platform token and resolve the tenant from
the authenticated principal (never from the payload). Neither makes an
outbound call: retrieval reads the practice's own sqlite rows, and authority
resolution is pure ranking over the claims the caller supplies.
"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Request

from app import retrieval
from app.authority import AuthorityError, resolve
from app.security import authenticate, assert_no_tenant_keys

router = APIRouter()


@router.get("/retrieval")
def retrieval_query(request: Request, q: str = "", limit: int = 10) -> Dict[str, Any]:
    """Rank the tenant's own records against ``q``."""
    tenant = authenticate(request)
    try:
        return retrieval.query(q, token="", entities=None, limit=limit)
    except retrieval.RetrievalError as exc:
        return {"ok": False, "error": str(exc)}
    except retrieval.TenantRefused as exc:  # pragma: no cover - defensive
        return {"ok": False, "tenant_id": tenant.tenant_id, "error": str(exc)}


@router.post("/authority/resolve")
def authority_resolve(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """Resolve ranked claims for one subject under precedence.v1."""
    authenticate(request)
    assert_no_tenant_keys(payload)
    subject = str((payload or {}).get("subject") or "").strip()
    claims: List[Dict[str, Any]] = list((payload or {}).get("claims") or [])
    if not subject:
        return {"ok": False, "error": "subject required"}
    if not claims:
        return {"ok": False, "error": "claims required"}
    try:
        resolution = resolve(subject, claims)
    except (AuthorityError, TypeError, ValueError) as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    return {"ok": True, "resolution": resolution.to_dict()}
