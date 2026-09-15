"""Per-capability models. Persist key is id; callers never send it."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Type

from app.schema import SPECS


@dataclass
class CapabilityRecord:
    FIELDS: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    id: int | None = None
    reference: str = ""
    status: str = "open"
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any] | None) -> "CapabilityRecord":
        data = dict(payload or {})
        item_id = data.pop("id", None)
        return cls(
            FIELDS=dict(cls.FIELDS),
            id=item_id,
            reference=str(data.pop("reference", "")),
            status=str(data.pop("status", "open")),
            extra=data,
        )

    def to_dict(self) -> Dict[str, Any]:
        body = {"id": self.id, "reference": self.reference, "status": self.status}
        body.update(self.extra)
        return body


def _model_for(capability_id: str, fields: Dict[str, Dict[str, Any]]) -> Type[CapabilityRecord]:
    return type(
        f"{capability_id.title().replace('_', '')}Model",
        (CapabilityRecord,),
        {"FIELDS": fields, "CAPABILITY_ID": capability_id},
    )


MODELS: Dict[str, Type[CapabilityRecord]] = {
    cap_id: _model_for(cap_id, spec["FIELDS"]) for cap_id, spec in SPECS.items()
}
