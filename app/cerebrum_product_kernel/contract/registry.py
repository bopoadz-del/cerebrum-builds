"""Capability registry: id, entity, fields, constraints and bound blocks."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.models import ENTITIES, MODELS


def _blocks() -> Dict[str, List[str]]:
    from app.jobs import CAPABILITIES

    return {item["id"]: list(item.get("blocks") or []) for item in CAPABILITIES}


def contract_for(capability_id: str) -> Optional[Dict[str, Any]]:
    cls = MODELS.get(str(capability_id or ""))
    if cls is None:
        return None
    return {
        "id": capability_id,
        "entity": ENTITIES[capability_id],
        "fields": list(cls.FIELDS),
        "constraints": dict(cls.CONSTRAINTS),
        "blocks": _blocks().get(capability_id, []),
        "status_vocabulary": list(
            (cls.CONSTRAINTS.get("status") or {}).get("allowed_values") or []
        ),
    }


CAPABILITIES: Dict[str, Dict[str, Any]] = {
    capability_id: contract_for(capability_id) for capability_id in sorted(MODELS)
}


def entity_for(capability_id: str) -> Optional[str]:
    return ENTITIES.get(str(capability_id or ""))
