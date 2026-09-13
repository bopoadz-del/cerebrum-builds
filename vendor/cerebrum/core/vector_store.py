"""Offline vector_store shim. No network, no pgvector."""

from __future__ import annotations

from typing import Any, Dict, List


async def search_vectors(
    project_id: str,
    query: str,
    top_k: int = 5,
    threshold: float = 0.3,
) -> List[Dict[str, Any]]:
    """Store-unwired search: empty corpus, never call a remote DB."""
    return []
