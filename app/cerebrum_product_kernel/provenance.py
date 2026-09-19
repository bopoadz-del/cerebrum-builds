"""Provenance records for what the platform ran and where it came from."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ProvenanceRecord:
    capability_id: str
    entity: str
    blocks: List[str] = field(default_factory=list)
    record_digest: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "entity": self.entity,
            "blocks": list(self.blocks),
            "record_digest": self.record_digest,
        }


def digest(payload: Any) -> str:
    import json

    body = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def for_record(capability_id: str, entity: str, blocks: List[str], payload: Any) -> ProvenanceRecord:
    return ProvenanceRecord(capability_id=capability_id, entity=entity,
                            blocks=list(blocks), record_digest=digest(payload))
