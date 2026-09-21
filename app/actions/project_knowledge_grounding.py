"""Handler for capability project_knowledge_grounding.

Written by the factory WRITER role (codewhale exec)

Authored by the coder CLI (codewhale exec) — the factory WRITER coding
agent — against the vendored blocks, in this repository.

Answers a question about a PSI project (price, payment plan, handover date)
from the tenant's own ingested project sheets and nothing else. Retrieval is
app.retrieval against the tenant corpus with the precedence ladder attached,
plus the vendored ``vector_search`` block; every claim is judged by the
vendored ``evidence_or_refuse`` block before it is spoken, and the vendored
``ingestion_provenance`` block records which document the claim came from. A
claim the corpus cannot support is withheld -- cite-or-refuse is the point of
this capability, because an invented price or handover date is the liability.

Scope
-----
READS  this capability's own columns from the caller's record; app.retrieval
       and app.authority (the tenant corpus and precedence.v1); app.llm (the
       offline drafter); app.dispatch (the local offline block runtime);
       app.block_inputs (block input construction); app.store (the
       ``project_knowledge_grounding`` table, through the route's
       tenant-scoped save).
WRITES app.dispatch.execute() results; exactly one row in
       ``project_knowledge_grounding`` via the ROUTE's ``store.save(entity,
       record, tenant_id)`` -- this handler has no tenant and never persists
       directly.
NEVER  unguarded network egress; a claim the corpus does not support;
       ``vendor/**`` (sealed, read-only); another capability's table;
       ``tests/**``.

Blocks are action-dispatched: ``action=`` is a keyword on
``app.dispatch.execute`` (via app.block_run), never a key inside the domain
payload. Block-contract keys are constructed by
``app.block_inputs.prepare_block_input`` from this record.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app import authority, llm, retrieval
from app.block_run import block_runner, probe_block
from app.security import InputRefused, clean_text

CAPABILITY_ID = "project_knowledge_grounding"
ENTITY = "project_knowledge_grounding"
BLOCK_IDS = ['knowledge', 'vector_search', 'ingestion_provenance',
             'evidence_or_refuse', 'llm_enhancer']
#: Each block's declared action (block.json / the Store map). Blocks are
#: action-dispatched; calling one with no action answers "Unknown action".
BLOCK_DEFAULT_ACTIONS = {
    'knowledge': 'search',
    'vector_search': 'search',
    'ingestion_provenance': 'list_labels',
    'evidence_or_refuse': 'judge',
    'llm_enhancer': 'status',
}
#: This capability's own domain columns.
CAPABILITY_FIELDS = [
    'reference', 'status', 'project_tag', 'claim_type', 'question',
    'document_name', 'document_text', 'citation', 'authority_label',
    'grounded', 'answer', 'notes',
]

EDGE_CONSTRAINTS = {
    'reference': {'required': True},
    'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True},
    'project_tag': {'required': True},
    'claim_type': {'allowed_values': ['price', 'payment_plan', 'handover_date', 'other'],
                   'required': True},
    'authority_label': {'allowed_values': list(authority.LABELS), 'required': False},
}

#: A claim type that is a number about money or a date a buyer will rely on.
CLAIM_TYPES = ('price', 'payment_plan', 'handover_date', 'other')


def _text(data: Dict[str, Any], name: str, limit: int = 20000) -> str:
    return clean_text(data.get(name), field=name, limit=limit)


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(payload or {}) if isinstance(payload, dict) else {}
    runner = block_runner(entity=ENTITY, roster=BLOCK_IDS, default_actions=BLOCK_DEFAULT_ACTIONS)

    try:
        reference = _text(data, "reference", 120) or "grounding"
        project_tag = _text(data, "project_tag", 120)
        claim_type = _text(data, "claim_type", 40).lower() or "other"
        question = _text(data, "question", 1000)
        document_name = _text(data, "document_name", 300)
        document_text = _text(data, "document_text", 20000)
        if claim_type not in CLAIM_TYPES:
            return {
                "ok": False,
                "capability": CAPABILITY_ID,
                "error": "claim_type must be one of: " + ", ".join(CLAIM_TYPES),
            }
        if not (question or document_text):
            return {
                "ok": False,
                "capability": CAPABILITY_ID,
                "error": "question or document_text is required: nothing to ground",
            }
    except InputRefused as exc:
        return {"ok": False, "capability": CAPABILITY_ID, "error": str(exc)}

    # 1. the tenant's own corpus, precedence.v1 attached.
    query = question or f"{project_tag} {claim_type}"
    ingest_state = "skipped"
    if document_text:
        # A sheet handed in with the record is ingested before the claim is
        # judged, so the citation can point at it. When the corpus is not
        # migrated yet (a handler called outside a booted product) the ingest
        # is reported as deferred instead of being claimed as done.
        try:
            retrieval.ingest(
                name=document_name or f"{project_tag}-{claim_type}",
                text=document_text,
                authority=authority.HIGHEST,
                project_tag=project_tag,
            )
            ingest_state = "ingested"
        except Exception as exc:  # noqa: BLE001 - the named reason travels
            ingest_state = f"deferred: {type(exc).__name__}: {exc}"[:200]
    hits = (retrieval.search(query, project_tag=project_tag, limit=5) or {}).get("hits") or []

    # 2. the vendored retrieval blocks over the same collection.
    vectors = runner(
        "vector_search",
        {"query": query, "collection": project_tag or "psi_projects", "top_k": 5},
        action="search",
    )
    # 3. provenance for the document the claim would be drawn from.
    provenance = runner(
        "ingestion_provenance",
        {
            "source_name": document_name,
            "source_label": "project_sheet",
            "claim": query,
            "text": document_text[:4000],
        },
        action="list_labels",
    )
    # 4. the knowledge block is the delivery's cited-answer path. Where the
    #    delivered runtime slice cannot load it (see docs/blockers.json) the
    #    capability says so by name and grounds on app.retrieval instead of
    #    pretending the block answered.
    knowledge = probe_block(
        "knowledge",
        {"query": query, "text": document_text[:4000], "top_k": 5},
        action="search",
        entity=ENTITY,
        roster=BLOCK_IDS,
        default_actions=BLOCK_DEFAULT_ACTIONS,
    )
    unavailable: Dict[str, str] = {}
    if not knowledge["ok"]:
        unavailable["knowledge"] = knowledge["error"]

    # 5. cite or refuse: a claim with no evidence is never answered.
    citations = [hit["citation"] for hit in hits if hit.get("citation")]
    # The judge is asked about the claim with the citations retrieval found.
    # With no citation it refuses the claim -- and that refusal IS the
    # cite-or-refuse answer, so it is read, not propagated as a block failure.
    judged = probe_block(
        "evidence_or_refuse",
        {"claims": [{"id": f"{reference}:{claim_type}", "claim": query,
                     "evidence": citations}]},
        action="judge",
        entity=ENTITY,
        roster=BLOCK_IDS,
        default_actions=BLOCK_DEFAULT_ACTIONS,
    )
    judge_result = judged["result"] if judged["ok"] else {}
    verdicts = judge_result.get("verdicts") or []
    grounded = bool(citations) and bool(verdicts) and bool(verdicts[0].get("evidenced"))
    if not judged["ok"]:
        unavailable["evidence_or_refuse"] = judged["error"]

    posture = runner("llm_enhancer", {"text": query}, action="status")

    refusal = runner.refusal()
    if refusal is not None:
        return {"ok": False, "capability": CAPABILITY_ID, **refusal}

    if grounded:
        answer = llm.compose_grounded_answer(
            question=query,
            claim_type=claim_type,
            hits=hits,
            project_tag=project_tag,
        )
        withheld_reason = ""
    else:
        answer = ""
        withheld_reason = (
            "no ingested project sheet supports a "
            f"{claim_type} claim for {project_tag or 'this project'}: the "
            "claim is withheld, not improvised"
        )

    best = hits[0] if hits else {}
    # Every answer carries its authority envelope (precedence.v1). On a
    # grounded answer that is the winning layer among the cited documents and
    # a per-claim label for the claim; on a withheld one there is no layer to
    # claim, so ``authority`` is null and the envelope says so rather than
    # labelling an improvised answer. This is ``app.authority``'s own shape,
    # emitted as-is -- the operator console renders it beside the answer.
    if grounded:
        label = authority.label_answer(
            str(best.get("authority") or authority.HIGHEST),
            claims=[
                {
                    "id": f"{reference}:{claim_type}",
                    "claim_type": claim_type,
                    "authority": best.get("authority"),
                    "evidenced": True,
                    "citation": citations[0] if citations else "",
                }
            ],
        )
    else:
        label = {
            "authority": None,
            "rank": None,
            "precedence": "precedence.v1",
            "withheld": True,
            "claims": [
                {
                    "id": f"{reference}:{claim_type}",
                    "claim_type": claim_type,
                    "authority": None,
                    "evidenced": False,
                    "citation": "",
                }
            ],
        }
    return {
        "ok": True,
        "capability": CAPABILITY_ID,
        "project_tag": project_tag,
        "claim_type": claim_type,
        "question": query,
        "grounded": grounded,
        "answer": answer,
        "withheld_reason": withheld_reason,
        "citation": citations[0] if citations else "",
        "authority_label": best.get("authority") or authority.HIGHEST,
        "label": label,
        "labels": label["claims"],
        "evidence": [
            {
                "citation": hit.get("citation"),
                "authority": hit.get("authority"),
                "score": hit.get("score"),
            }
            for hit in hits
        ],
        "ingest_state": ingest_state,
        "provenance": {
            "schema": (provenance.get("provenance") or {}).get("schema")
            if isinstance(provenance, dict) else None,
            "source_name": document_name,
        },
        "vector_hits": (vectors.get("total") if isinstance(vectors, dict) else None),
        "llm_posture": {
            "model": posture.get("model") if isinstance(posture, dict) else None,
            "active": posture.get("is_active") if isinstance(posture, dict) else None,
        },
        "blocks_unavailable": unavailable,
        "blocks": runner.report(),
    }
