"""The project-sheet corpus: what PSI's uploads become.

    POST /v1/rag/ingest   a price list / payment plan / handover sheet
    GET  /v1/rag/ingest   the ingest register: which sheet, from where, digest
    POST /v1/rag/query    passages that support a claim
    GET  /v1/rag/query    the same retrieval as a query string (console-friendly)
    POST /v1/rag/ground   the answered turn, cited or withheld
    GET  /v1/rag/ground   cite-or-refuse posture: what the corpus can support
                           (``?project_tag=`` narrows it to one project)
    POST /v1/rag/forget   remove one document
    GET  /v1/rag/corpus   what this tenant has ingested

Every response carries the authority envelope, so an operator can see whether
an answer came from a certified sheet, an ordinary document or nothing at
all (in which case the claim is withheld).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from app import retrieval
from app.auth import int_query, json_object, optional_int, require_permission, resolve_principal
from app.tenancy import Tenant

router = APIRouter(tags=["retrieval"])


def _first(body: Dict[str, Any], *names: str) -> Optional[str]:
    for name in names:
        value = body.get(name)
        if isinstance(value, str) and value.strip():
            return value
    return None


@router.get("/v1/rag/ingest")
def ingest_register(request: Request, tenant: Tenant = Depends(resolve_principal)) -> Dict[str, Any]:
    """The provenance of every ingested sheet: source, project, digest.

    ``/v1/rag/corpus`` lists the documents; this is the ingest register an
    operator needs before a campaign — which file each project's numbers
    came from, whether it was certified, and the digest that identifies the
    revision of the sheet those numbers were quoted out of. It also states
    the body this endpoint accepts, so an uploader can be wired without
    reading the source. An empty register answers 200: no sheets ingested
    is a state, not a missing resource.
    """
    require_permission(tenant, "read")
    stats = retrieval.corpus_stats(tenant.tenant_id)
    sources: Dict[str, Dict[str, Any]] = {}
    for document in stats["documents"]:
        source = str(document.get("source") or document.get("title") or "unnamed source")
        entry = sources.setdefault(
            source, {"source": source, "documents": [], "projects": [], "certified": 0}
        )
        entry["documents"].append(
            {
                "document_id": document.get("document_id"),
                "title": document.get("title"),
                "project_tag": document.get("project_tag"),
                "certified": bool(document.get("certified")),
                "digest": document.get("digest"),
            }
        )
        entry["certified"] += 1 if document.get("certified") else 0
        project = str(document.get("project_tag") or "")
        if project and project not in entry["projects"]:
            entry["projects"].append(project)
    register = [
        {**entry, "document_count": len(entry["documents"]), "projects": sorted(entry["projects"])}
        for entry in sorted(sources.values(), key=lambda item: item["source"])
    ]
    return {
        "ok": True,
        "tenant": tenant.to_dict(),
        "sources": register,
        "source_count": len(register),
        "document_count": stats["document_count"],
        "chunk_count": stats["chunk_count"],
        "projects": stats["projects"],
        "accepts": {
            "required": ["text"],
            "aliases": ["content", "paragraph", "body", "paragraphs", "passages", "rows"],
            "optional": ["title", "name", "project_tag", "project", "source", "source_file", "certified", "document_id"],
            "note": "an ingest without a source names the document as its own source; a claim is only pitched from what was ingested here",
        },
        "authority": {
            "precedence": "precedence.v1",
            "layer": "documents",
            "label": "documents:retrieval.ingest_register",
            "claim_labels": [],
            "divergence": [],
        },
    }


@router.post("/v1/rag/ingest")
async def ingest(request: Request, tenant: Tenant = Depends(resolve_principal)) -> Dict[str, Any]:
    require_permission(tenant, "write")
    body = await json_object(request)
    text = _first(body, "text", "content", "paragraph", "body")
    if not text:
        for key in ("paragraphs", "passages", "rows"):
            values = body.get(key)
            if isinstance(values, list) and values:
                text = "\n\n".join(str(item) for item in values)
                break
    if not text:
        raise HTTPException(status_code=422, detail="Missing required field: text")
    try:
        result = retrieval.ingest(
            tenant.tenant_id,
            text=str(text),
            title=str(body.get("title") or body.get("name") or ""),
            project_tag=str(body.get("project_tag") or body.get("project") or ""),
            source=str(body.get("source") or body.get("source_file") or ""),
            certified=bool(body.get("certified")),
            document_id=body.get("document_id"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True, "tenant": tenant.to_dict(), **result}


@router.get("/v1/rag/query")
def query_get(request: Request, tenant: Tenant = Depends(resolve_principal)) -> Dict[str, Any]:
    """The same retrieval as the POST, addressed by query string.

    An operator following a citation in a browser tab, or a console that
    cannot POST, still gets the tenant-scoped passages — under the same
    guards: the corpus is resolved from the authenticated principal, and a
    query with no question is refused by name rather than answered with
    nothing.
    """
    require_permission(tenant, "read")
    params = request.query_params
    question = _first(dict(params), "question", "query", "q", "text")
    if not question:
        raise HTTPException(status_code=422, detail="Missing required field: question")
    result = retrieval.query(
        tenant.tenant_id,
        question,
        project_tag=params.get("project_tag") or params.get("project"),
        top_k=optional_int(params.get("top_k"), "top_k", minimum=1, maximum=50),
        claim_type=params.get("claim_type"),
    )
    return {"ok": True, "tenant": tenant.to_dict(), **result}


@router.post("/v1/rag/query")
async def query(request: Request, tenant: Tenant = Depends(resolve_principal)) -> Dict[str, Any]:
    require_permission(tenant, "read")
    body = await json_object(request)
    question = _first(body, "question", "query", "q", "text")
    if not question:
        raise HTTPException(status_code=422, detail="Missing required field: question")
    result = retrieval.query(
        tenant.tenant_id,
        question,
        project_tag=body.get("project_tag") or body.get("project"),
        top_k=optional_int(body.get("top_k"), "top_k", minimum=1, maximum=50),
        claim_type=body.get("claim_type"),
    )
    return {"ok": True, "tenant": tenant.to_dict(), **result}


#: The liability-bearing claims the brief says may never be improvised,
#: each with the question an operator would ask to see whether the corpus
#: can carry it. Cite-or-refuse applied to the corpus itself.
POSTURE_PROBES = (
    ("price", "What is the starting price of this project?"),
    ("payment_plan", "What is the payment plan for this project?"),
    ("handover_date", "When is the handover date for this project?"),
)


@router.get("/v1/rag/ground")
def ground_posture(request: Request, tenant: Tenant = Depends(resolve_principal)) -> Dict[str, Any]:
    """Cite-or-refuse posture: per project, which claims retrieval can carry.

    For every ingested project this asks the corpus the three questions that
    create liability — price, payment plan, handover date — and reports
    which of them has a retrieved passage behind it. A claim with no
    passage is the one the live call will withhold, so an operator can see
    that before a dial rather than after a complaint. Projects with nothing
    ingested report as ungrounded, never as answered.
    """
    require_permission(tenant, "read")
    stats = retrieval.corpus_stats(tenant.tenant_id)
    wanted = str(request.query_params.get("project_tag") or "").strip()
    projects = sorted(tag for tag in stats["projects"] if not wanted or tag == wanted)
    posture: List[Dict[str, Any]] = []
    grounded = 0
    withheld = 0
    for project in projects:
        claims: List[Dict[str, Any]] = []
        for claim_type, question in POSTURE_PROBES:
            found = retrieval.query(
                tenant.tenant_id, question, project_tag=project, claim_type=claim_type
            )
            supported = bool(found["hits"])
            grounded += 1 if supported else 0
            withheld += 0 if supported else 1
            claims.append(
                {
                    "claim_type": claim_type,
                    "grounded": supported,
                    "citations": found["citations"],
                    "layer": (found["authority"] or {}).get("layer") if supported else None,
                }
            )
        posture.append({"project_tag": project, "claims": claims})
    return {
        "ok": True,
        "tenant": tenant.to_dict(),
        "project_tag": wanted or None,
        "projects": posture,
        "project_count": len(posture),
        "claim_probes": [claim_type for claim_type, _ in POSTURE_PROBES],
        "grounded_claims": grounded,
        "withheld_claims": withheld,
        "ungrounded": not stats["document_count"],
        "note": (
            "no project sheet has been ingested for this tenant, so every "
            "liability claim is withheld until one is"
            if not stats["document_count"]
            else (
                "no ingested sheet carries this project tag, so every claim "
                "about it is withheld"
                if wanted and not posture
                else "a claim is pitched only from a passage retrieved here; the rest are withheld"
            )
        ),
        "authority": {
            "precedence": "precedence.v1",
            "layer": "documents",
            "label": "documents:retrieval.ground_posture",
            "claim_labels": [],
            "divergence": [],
        },
    }


@router.post("/v1/rag/ground")
async def ground(request: Request, tenant: Tenant = Depends(resolve_principal)) -> Dict[str, Any]:
    require_permission(tenant, "read")
    body = await json_object(request)
    question = _first(body, "question", "query", "q")
    if not question:
        raise HTTPException(status_code=422, detail="Missing required field: question")
    result = retrieval.grounded_answer(
        tenant.tenant_id,
        project_tag=str(body.get("project_tag") or ""),
        question=question,
        claim_type=body.get("claim_type"),
        language=str(body.get("language") or "en"),
    )
    return {"ok": True, "tenant": tenant.to_dict(), **result}


@router.get("/v1/rag/corpus")
def corpus(request: Request, tenant: Tenant = Depends(resolve_principal)) -> Dict[str, Any]:
    require_permission(tenant, "read")
    stats = retrieval.corpus_stats(tenant.tenant_id)
    return {
        "ok": True,
        "tenant": tenant.to_dict(),
        **stats,
        "authority": {
            "precedence": "precedence.v1",
            "layer": "documents",
            "label": "documents:corpus",
            "claim_labels": [],
            "divergence": [],
        },
    }


@router.post("/v1/rag/forget")
async def forget(request: Request, tenant: Tenant = Depends(resolve_principal)) -> Dict[str, Any]:
    require_permission(tenant, "write")
    body = await json_object(request)
    document_id = str((body or {}).get("document_id") or "")
    if not document_id:
        raise HTTPException(status_code=422, detail="Missing required field: document_id")
    removed = retrieval.forget(tenant.tenant_id, document_id)
    if not removed:
        raise HTTPException(status_code=404, detail="document not found")
    return {"ok": True, "document_id": document_id, "removed": True}
