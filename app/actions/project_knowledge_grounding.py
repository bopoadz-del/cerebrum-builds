"""Project knowledge grounding (cite-or-refuse).

Written by the factory WRITER role (codewhale exec)

The bot may only claim what an ingested PSI project sheet says. This handler
retrieves per project tag and answers with a verbatim sentence plus its
citation, or withholds — and the withheld claim is named, so a broker can
see exactly which number the bot refused to invent. Price, payment plan and
handover date are the three claims that create liability when improvised.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app import domain, retrieval
from app import tenancy
from app.models import MODELS

CAPABILITY_ID = "project_knowledge_grounding"

#: The keyword action each bound block is dispatched with:
#: ``dispatch.execute(block_id, action=BLOCK_DEFAULT_ACTIONS.get(block_id))``.
#: The action travels as a keyword and never inside the payload -- the block
#: registry reads its operation from the keyword, and a payload "action" key
#: is just another record field. These are the actions ``app/dispatch.py``
#: registers for each block, so a declared default is a call this platform
#: can actually make.
BLOCK_DEFAULT_ACTIONS = {
    'knowledge': 'ingest',
    'vector_search': 'query',
    'ingestion_provenance': 'record',
    'evidence_or_refuse': 'answer',
    'llm_enhancer': 'turn',
}

REQUIRED_FIELDS = ["project_tag", "question"]

#: The same contract app/models.py declares, stated where the handler
#: enforces it: the route refuses from the model, the handler refuses
#: from here, and the two cannot drift (tests/test_capability_round_trip.py).
constraints = {
    "project_tag": {"required": True, "max_length": 80},
    "question": {"required": True, "max_length": 600},
    "claim_type": {"allowed_values": ['price', 'payment_plan', 'handover_date', 'amenities', 'location', 'availability']},
    "language": {"allowed_values": ['en', 'ar']},
    "answer": {"max_length": 4000},
    "pitch": {"max_length": 4000},
    "citations": {},
    "source_documents": {"max_length": 600},
    "retrieved_count": {"min": 0},
    "withheld": {},
    "withheld_claims": {"max_length": 400},
    "authority_layer": {"max_length": 40},
    "authority_label": {"max_length": 200},
    "divergence": {"max_length": 2000},
    "campaign": {"max_length": 80},
    "reference": {"required": True},
    "status": {"allowed_values": ['open', 'in_progress', 'closed'], "required": True},
}

LIABILITY_CLAIMS = ("price", "payment_plan", "handover_date")


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Answer a project question from the corpus, or withhold the claim."""
    body = dict(payload or {})
    for name in REQUIRED_FIELDS:
        if body.get(name) in (None, ""):
            return {"ok": False, "error": f"Missing required field: {name}"}
    for name in ("reference", "status"):
        if body.get(name) in (None, ""):
            return {"ok": False, "error": f"Missing required field: {name}"}
    for name, rules in constraints.items():
        values = rules.get("allowed_values") or ()
        value = body.get(name)
        if value is None or value == "":
            continue
        if values and value not in values:
            return {
                "ok": False,
                "error": f"{name} must be one of: " + ", ".join(str(v) for v in values),
            }
    tenant_id = str(body.get("tenant_id") or tenancy.deployment_tenant())
    if not tenant_id:
        # Tenancy comes from the authenticated principal, which the route
        # injects. A handler that cannot see it refuses rather than
        # assuming a tenant: defaulting here is how one brokerage ends up
        # writing into another's corpus with a valid token of its own.
        return {
            "ok": False,
            "error": "no tenant could be resolved: this deployment binds more "
            "than one operator, so tenancy comes from the authenticated "
            "principal and is never assumed by a handler",
        }
    claim = body.get("claim_type")
    answer = retrieval.grounded_answer(
        tenant_id,
        project_tag=str(body.get("project_tag") or ""),
        question=str(body.get("question") or ""),
        claim_type=claim,
        language=str(body.get("language") or "en"),
    )
    withheld = bool(answer.get("withheld"))
    liability = str(claim or "") in LIABILITY_CLAIMS
    return {
        "ok": True,
        "capability": CAPABILITY_ID,
        "decision": "withheld" if withheld else "cited",
        "claim_type": claim,
        "liability_claim": liability,
        "withheld": withheld,
        "withheld_claims": answer.get("withheld_claims") or [],
        "reason": answer.get("reason"),
        "record": {
            "project_tag": body.get("project_tag"),
            "question": body.get("question"),
            "claim_type": claim,
            "language": str(body.get("language") or "en"),
            "answer": answer.get("answer"),
            "pitch": answer.get("pitch"),
            "citations": ", ".join(answer.get("citations") or []),
            "source_documents": answer.get("source_documents"),
            "retrieved_count": domain.as_int(answer.get("retrieved_count"), 0),
            "withheld": withheld,
            "withheld_claims": ", ".join(answer.get("withheld_claims") or []),
            "authority_layer": (answer.get("authority") or {}).get("layer"),
            "authority_label": (answer.get("authority") or {}).get("label"),
            "divergence": str((answer.get("authority") or {}).get("divergence") or ""),
            "campaign": body.get("campaign"),
        },
        "authority": answer.get("authority"),
    }
