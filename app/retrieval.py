"""Tenant-scoped retrieval over the records this practice already holds.

There is no vector service and no network in the delivered platform: the
corpus is the tenant's own persisted rows (app/store.py) plus any documents
the practice registered. Every call resolves the tenant from the authenticated
principal — never from a client-supplied name — and filters rows by that
tenant before scoring, so one practice can never retrieve another's records.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Sequence

from app import store
from app.auth import platform_token
from app.tenancy import TenantRefused, token_map

_WORD = re.compile(r"[a-z0-9_]+")


class RetrievalError(ValueError):
    """The query or the tenant binding is not usable."""


@dataclass(frozen=True)
class Hit:
    entity: str
    record_id: int
    score: float
    match: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity": self.entity,
            "record_id": self.record_id,
            "score": round(self.score, 4),
            "match": self.match,
        }


def _tokens(text: str) -> List[str]:
    return _WORD.findall(str(text or "").lower())


def _score(query_tokens: Sequence[str], row: Dict[str, Any]) -> float:
    blob = " ".join(str(value) for value in row.values() if value is not None)
    row_tokens = _tokens(blob)
    if not row_tokens or not query_tokens:
        return 0.0
    overlap = sum(1 for token in query_tokens if token in row_tokens)
    return overlap / float(len(query_tokens))


def tenant_for_token(token: str) -> str:
    """Resolve the tenant from a bearer token. Refuses anything else."""
    bound = dict(token_map()).get(str(token or "").strip())
    if not bound:
        raise TenantRefused("token is not bound to a tenant")
    return bound


def query(
    text: str,
    *,
    token: str,
    entities: Iterable[str] | None = None,
    limit: int = 10,
) -> Dict[str, Any]:
    """Rank this tenant's rows against ``text``. Offline, deterministic."""
    query_tokens = _tokens(text)
    if not query_tokens:
        raise RetrievalError("query text required")
    tenant_id = tenant_for_token(token if token else platform_token())
    targets = [str(e) for e in (entities or store.TABLES) if str(e) in store.TABLES]
    hits: List[Hit] = []
    for entity in targets:
        try:
            rows = store.list_all(entity, tenant_id=tenant_id)
        except Exception:  # noqa: BLE001 - an absent table is not a retrieval hit
            continue
        for row in rows:
            score = _score(query_tokens, row)
            if score <= 0:
                continue
            match = next(
                (
                    str(row.get(key))
                    for key in ("reference", "patient_name", "owner_name", "subject_ref")
                    if row.get(key)
                ),
                "",
            )
            hits.append(Hit(entity=entity, record_id=int(row.get("id") or 0), score=score, match=match))
    hits.sort(key=lambda hit: (-hit.score, hit.entity, hit.record_id))
    return {
        "ok": True,
        "tenant_id": tenant_id,
        "query": text,
        "hits": [hit.to_dict() for hit in hits[: max(1, min(int(limit), 50))]],
    }
