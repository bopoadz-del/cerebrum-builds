"""evidence_verifier — GAP. Verify operational evidence without PII leak."""

from __future__ import annotations

from typing import Any, Dict

from app.persist import ok_envelope

# READS: caller.input
# WRITES: caller.output
# NEVER: network, credential

BLOCK_IDS: list[str] = []


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Mark evidence as verified in-process; strip obvious PII-shaped keys."""
    cleaned = {
        key: value
        for key, value in payload.items()
        if key not in {"email", "phone", "ssn", "passport"}
    }
    cleaned["verified"] = True
    cleaned["verifier"] = "estate_operator"
    return ok_envelope("evidence_verifier", cleaned)
