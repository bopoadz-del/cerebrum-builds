"""Grounded answers. Offline, and honest about it.

Written by the factory WRITER role (codewhale exec)

This platform runs offline (P1): there is no cloud model and no provider key,
so there is no model call here. ``answer()`` composes the reply from what the
platform actually knows -- the tenant's retrieved corpus, the versioned formula
registry and the operating procedures -- and tells the caller which one won by
``precedence.v1``. The model is handed the winner; it never picks a source and
never blends two silently: every claim carries its layer label and every
disagreement is returned as a divergence record.

``status()`` reports the provider truthfully (``offline-deterministic``). If a
provider is ever configured it is reported as unconfigured until it really is,
because a platform that claims a model it does not have is the same lie as a
stub that claims a block it cannot run.

Scope
-----
READS  its inputs: retrieved chunks, registry data, the caller's question.
WRITES nothing but the caller's answer log row (through app.retrieval).
NEVER  network, provider APIs, ``vendor/**``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from app import authority, formulas, retrieval

PROVIDER = "offline-deterministic"
NETWORK = False
#: Sentences returned when the corpus has nothing to ground an answer.
NO_GROUNDING = "No grounded source matched this question in your corpus."


def status() -> Dict[str, Any]:
    """What this adapter really is: no provider, no network, no pretence."""
    return {
        "provider": PROVIDER,
        "network": NETWORK,
        "configured": True,
        "note": (
            "Answers are composed from the tenant's corpus and the versioned "
            "formula registry. No model provider is configured or called."
        ),
    }


def _claims_from_hits(hits: Sequence[Dict[str, Any]]) -> List[authority.Claim]:
    claims: List[authority.Claim] = []
    for hit in hits:
        claims.append(
            authority.Claim(
                layer=int(hit.get("layer") or authority.LAYER_RANK["documents"]),
                source=str(hit.get("title") or f"chunk:{hit.get('chunk_id')}"),
                text=str(hit.get("text") or "").strip(),
                detail={
                    "chunk_id": hit.get("chunk_id"),
                    "document_id": hit.get("document_id"),
                    "score": hit.get("score"),
                    "matched_terms": hit.get("matched_terms"),
                },
            )
        )
    return claims


def _formula_claims(question: str) -> List[authority.Claim]:
    """Formula-registry entries that name a term in the question (layer 3)."""
    terms = set(retrieval.tokenize(question))
    claims: List[authority.Claim] = []
    for entry in formulas.registry():
        haystack = set(
            retrieval.tokenize(
                entry["id"] + " " + entry["description"] + " " + " ".join(entry["params"])
            )
        )
        overlap = sorted(terms & haystack)
        if not overlap:
            continue
        claims.append(
            authority.Claim(
                layer=authority.LAYER_RANK["formulas"],
                source=f"formula:{entry['id']}@{entry['version']}",
                text=f"{entry['description']} ({entry['expression']}), unit {entry['unit']}",
                detail={"formula_id": entry["id"], "version": entry["version"], "matched_terms": overlap},
            )
        )
    return claims


def answer(question: str, *, tenant: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
    """Compose one grounded answer and log it against the tenant."""
    tenant_id = tenant or retrieval.tenancy.current_tenant()
    hits = retrieval.retrieve(question, tenant=tenant_id, limit=limit)
    resolution = authority.resolve([*_claims_from_hits(hits), *_formula_claims(question)])
    winner = resolution.get("winner")
    if winner is None:
        text = NO_GROUNDING
    else:
        text = (
            f"[{winner['layer_name']}:{winner['source']}] {winner['text']}"
        )
    body = {
        "question": question,
        "answer": text,
        "grounded": winner is not None,
        "precedence": resolution["precedence"],
        "winner": winner,
        "claims": resolution["claims"],
        "divergences": resolution["divergences"],
        "labels": resolution["labels"],
        "hits": hits,
        "provider": PROVIDER,
        "network": NETWORK,
        "tenant": tenant_id,
    }
    body["answer_id"] = retrieval.log_answer(
        tenant=tenant_id,
        question=question,
        answer=text,
        winner_source=str((winner or {}).get("source") or ""),
        labels=resolution["labels"],
        divergences=resolution["divergences"],
    )
    return body
