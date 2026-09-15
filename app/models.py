"""Capability models. Empty from_dict leaves id unset."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from app.schema import SPECS


@dataclass
class CapabilityModel:
    capability_id: str
    FIELDS: Dict[str, Dict[str, Any]]
    id: Optional[int] = None
    values: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any] | None) -> "CapabilityModel":
        payload = dict(data or {})
        raw_id = payload.get("id")
        ident = None if raw_id in (None, "") else int(raw_id)
        return cls(
            capability_id=cls.capability_id,
            FIELDS=cls.FIELDS,
            id=ident,
            values=payload,
        )

    def to_dict(self) -> Dict[str, Any]:
        body = dict(self.values)
        body["id"] = self.id
        return body


def _build_models() -> Dict[str, type]:
    models: Dict[str, type] = {}
    for cap_id, spec in SPECS.items():
        models[cap_id] = type(
            f"{cap_id.title().replace('_', '')}Model",
            (CapabilityModel,),
            {"capability_id": cap_id, "FIELDS": dict(spec["FIELDS"])},
        )
    return models


MODELS = _build_models()
