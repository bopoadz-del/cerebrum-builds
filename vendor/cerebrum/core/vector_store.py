"""Offline vector-store shim. Knowledge imports this; the pilot has no network corpus."""

from __future__ import annotations

from typing import Any, Dict, List


async def search_vectors(
    project_or_query: Any,
    query: str | None = None,
    top_k: int = 5,
    threshold: float = 0.0,
    **_kwargs: Any,
) -> List[Dict[str, Any]]:
    return []
