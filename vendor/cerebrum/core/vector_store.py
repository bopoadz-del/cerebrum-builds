"""Offline vector store stub. Knowledge asks without a live pgvector corpus."""

from __future__ import annotations

from typing import Any, Dict, List


async def search_vectors(
    project_id: str,
    query: str,
    top_k: int = 5,
    threshold: float = 0.3,
) -> List[Dict[str, Any]]:
    return []


async def add_vectors(*_args: Any, **_kwargs: Any) -> Dict[str, Any]:
    return {"status": "success", "added": 0}
