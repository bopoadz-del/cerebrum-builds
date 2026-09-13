"""Offline pgvector stub. Knowledge falls back to empty retrieval without a live store."""

from __future__ import annotations

from typing import Any, Dict, List


async def search_vectors(
    project_id: str,
    query: str,
    top_k: int = 5,
    threshold: float = 0.3,
) -> List[Dict[str, Any]]:
    """No remote vector DB on the offline aviation platform."""
    return []
