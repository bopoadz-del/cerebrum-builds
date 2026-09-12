"""hybrid_program_delivery — GENERATE. Agile+waterfall with RTE / SM / PM / BA owners."""

from __future__ import annotations

from typing import Any, Dict

from app.persist import ok_envelope

# READS: caller.input
# WRITES: caller.output
# NEVER: inventing unverified Store block ids

BLOCK_IDS: list[str] = []

STATUS_VALUES = ("open", "in_progress", "closed")
ROLE_LANE = {
    "rte": "train_sync",
    "scrum_master": "iteration",
    "pm": "waterfall_control",
    "ba": "discovery",
}
MODE_BLEND = {
    "hybrid": ("pi_planning", "stage_gate"),
    "agile": ("sprint", "increment"),
    "waterfall": ("phase", "gate"),
}


def _status(payload: Dict[str, Any]) -> str:
    status = str(payload.get("status") or "open")
    return status if status in STATUS_VALUES else "open"


def _role(payload: Dict[str, Any]) -> str:
    role = str(payload.get("owner_role") or "rte")
    return role if role in ROLE_LANE else "rte"


def _mode(payload: Dict[str, Any]) -> str:
    mode = str(payload.get("delivery_mode") or "hybrid")
    return mode if mode in MODE_BLEND else "hybrid"


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Assign a hybrid delivery lane and owner discipline from the envelope."""
    status = _status(payload)
    role = _role(payload)
    mode = _mode(payload)
    ceremonies = MODE_BLEND[mode]
    record = {
        **payload,
        "status": status,
        "delivery_board": {
            "owner_role": role,
            "lane": ROLE_LANE[role],
            "delivery_mode": mode,
            "ceremonies": list(ceremonies),
            "cadence": "pi_plus_gate" if mode == "hybrid" else ceremonies[0],
            "reference": str(payload.get("reference") or "sample"),
            "can_exit_phase": status == "in_progress",
            "is_terminal": status == "closed",
        },
    }
    return ok_envelope("hybrid_program_delivery", record)
