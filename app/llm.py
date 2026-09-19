"""Local, offline "model" surface for Bakery Chain Operations.

Written by the factory WRITER role (codewhale exec)

This platform ships no cloud LLM and no network: the delivered product must run
with no egress. Answers are produced by deterministic extractive retrieval over
the tenant's own corpus (``app.retrieval``) plus the authority ladder
(``app.authority``), which is what the pilot needs and what the offline posture
allows.

``available()`` is honest about that: it reports the local engine, never a
provider credential this deployment does not have. A caller that asks for a
remote provider is refused by name rather than silently downgraded.

Scope
-----
READS  the caller's prompt, the tenant corpus.
WRITES nothing.
NEVER  network, provider credentials, ``vendor/**``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

ENGINE = "offline-extractive"
REMOTE_PROVIDERS = ("openai", "anthropic", "openrouter", "deepseek", "ollama")


def available() -> Dict[str, Any]:
    return {"engine": ENGINE, "network": False, "providers": [], "local": True}


def answer(prompt: str, *, top_k: int = 5, tenant_id: Optional[str] = None) -> Dict[str, Any]:
    """Answer from the tenant's corpus with citations and insufficiency."""
    from app.retrieval import search

    hits = search(prompt, top_k=top_k, tenant_id=tenant_id)
    if not hits:
        return {
            "engine": ENGINE,
            "answer": "",
            "insufficiency": True,
            "citations": [],
            "hits": [],
        }
    answer_text = " ".join(str(hit.get("excerpt") or "") for hit in hits[:2]).strip()
    return {
        "engine": ENGINE,
        "answer": answer_text,
        "insufficiency": not bool(answer_text),
        "citations": [hit.get("doc_id") for hit in hits],
        "hits": hits,
    }


def refuse_remote(provider: str) -> Dict[str, Any]:
    name = str(provider or "").strip().lower()
    return {
        "ok": False,
        "error": f"remote provider {name!r} is not available offline",
        "available": [ENGINE],
    }
