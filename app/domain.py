"""Airport operations kernel. Envelope-driven; no invented caller contracts."""

from __future__ import annotations

from typing import Any, Dict, Tuple

STATUS_VALUES = ("open", "in_progress", "closed")
STATUS_NEXT: Dict[str, Tuple[str, ...]] = {
    "open": ("in_progress",),
    "in_progress": ("closed",),
    "closed": (),
}

WINDOW_WEIGHT = {"turnaround": 1.0, "shift": 0.85, "day": 0.7}
STATUS_SCORE = {"open": 0.45, "in_progress": 0.72, "closed": 1.0}
DEGRADED_BELOW = 0.6

WORK_ORDER_STAGE = {
    "open": "assigned",
    "in_progress": "on_stand",
    "closed": "released",
}
CREW_FUNCTIONS = ("turnaround", "baggage", "fueling", "maintenance")
RETENTION_DAYS = {"manual": 365, "certificate": 1095, "directive": 180}
EVIDENCE_SEVERITY = {"sensor": "high", "photo": "medium", "report": "low"}
FLIGHT_CASCADE = {
    "arrival": {"next_action": "stand_ready", "sla_minutes": 25, "queue": "turnaround"},
    "departure": {"next_action": "pushback", "sla_minutes": 15, "queue": "departure"},
    "weather": {"next_action": "hold", "sla_minutes": 60, "queue": "ops"},
    "hold": {"next_action": "release", "sla_minutes": 45, "queue": "ops"},
}
HORIZON_BAND = {"today": "tactical", "week": "planning", "month": "strategic"}


def envelope_status(payload: Dict[str, Any]) -> str:
    status = str(payload.get("status") or "open")
    return status if status in STATUS_VALUES else "open"


def allowed_next_status(status: str) -> Tuple[str, ...]:
    return STATUS_NEXT.get(status, ())


def readiness_score(status: str, window: str) -> float:
    base = STATUS_SCORE.get(status, STATUS_SCORE["open"])
    weight = WINDOW_WEIGHT.get(window, WINDOW_WEIGHT["turnaround"])
    return round(base * weight, 4)


def stand_is_degraded(score: float) -> bool:
    return score < DEGRADED_BELOW


def work_order_stage(status: str) -> str:
    return WORK_ORDER_STAGE.get(status, "assigned")


def crew_function(work_order: str, crew_name: str) -> str:
    text = f"{work_order} {crew_name}".lower()
    if "fuel" in text:
        return "fueling"
    if "bag" in text:
        return "baggage"
    if "maint" in text:
        return "maintenance"
    return "turnaround"


def document_retention_days(control_class: str) -> int:
    return RETENTION_DAYS.get(control_class, RETENTION_DAYS["manual"])


def evidence_severity(kind: str) -> str:
    return EVIDENCE_SEVERITY.get(kind, "medium")


def flight_cascade(event_type: str) -> Dict[str, Any]:
    return dict(FLIGHT_CASCADE.get(event_type, FLIGHT_CASCADE["arrival"]))


def knowledge_source_class(question: str, note_body: str) -> str:
    text = f"{question} {note_body}".lower()
    if "incident" in text or "evidence" in text:
        return "incident_record"
    if "flight" in text or "arrival" in text or "departure" in text:
        return "flight_event"
    return "airside_sop"


def dashboard_band(horizon: str) -> str:
    return HORIZON_BAND.get(horizon, "tactical")
