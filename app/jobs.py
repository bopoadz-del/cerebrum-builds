"""The capability roster this platform serves.

``GET /v1/capabilities`` and the operator console both read this, and it is
derived from ``app/models.py`` so the roster cannot drift from the schema.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.models import CAPABILITY_IDS, MODELS, PLATFORM_BLOCKS

CAPABILITIES: List[Dict[str, Any]] = [
    {
        "id": capability_id,
        "capability_id": capability_id,
        "entity": MODELS[capability_id].ENTITY,
        "title": MODELS[capability_id].TITLE,
        "description": MODELS[capability_id].DESCRIPTION,
        "blocks": list(MODELS[capability_id].BLOCKS),
        "fields": [spec["name"] for spec in MODELS[capability_id].field_specs()],
        "required": list(MODELS[capability_id].REQUIRED),
        "statuses": ["open", "in_progress", "closed"],
    }
    for capability_id in CAPABILITY_IDS
]

PLATFORM: Dict[str, Any] = {
    "product": "CallOps",
    "vertical": "real_estate",
    "blocks": list(PLATFORM_BLOCKS),
    "capability_count": len(CAPABILITIES),
}


def ids() -> List[str]:
    return [str(item["id"]) for item in CAPABILITIES]
