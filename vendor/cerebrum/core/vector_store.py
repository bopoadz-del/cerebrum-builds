"""Offline vector store stub. CLONER did not vendor the Store's live pgvector module."""

from __future__ import annotations

from typing import Any, Dict, List


async def search_vectors(
    project_id: str,
    query: str,
    top_k: int = 5,
    threshold: float = 0.3,
) -> List[Dict[str, Any]]:
    return []


def add_vectors(*_args: Any, **_kwargs: Any) -> None:
    return None
