"""Capability models that survive a sqlite round trip."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Type

from app.schema import SPECS


@dataclass
class CapabilityModel:
    FIELDS: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    id: int | None = None
    reference: str = ""
    status: str = "open"
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any] | None) -> "CapabilityModel":
        data = dict(payload or {})
        raw_id = data.pop("id", None)
        try:
            parsed_id = int(raw_id) if raw_id is not None else None
        except (TypeError, ValueError):
            parsed_id = None
        return cls(
            FIELDS=dict(cls.FIELDS),
            id=parsed_id,
            reference=str(data.get("reference") or ""),
            status=str(data.get("status") or "open"),
            extra=data,
        )

    def to_dict(self) -> Dict[str, Any]:
        body = {"id": self.id, "reference": self.reference, "status": self.status}
        body.update(self.extra)
        return body


def _model_for(capability_id: str, fields: Dict[str, Dict[str, Any]]) -> Type[CapabilityModel]:
    return type(
        f"{capability_id.title().replace('_', '')}Model",
        (CapabilityModel,),
        {"FIELDS": fields},
    )


MODELS: Dict[str, Type[CapabilityModel]] = {
    cap_id: _model_for(cap_id, spec["FIELDS"]) for cap_id, spec in SPECS.items()
}
