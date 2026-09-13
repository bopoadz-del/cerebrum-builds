"""Veterinary clinic kernel. Envelope-driven; no invented caller contracts."""

from __future__ import annotations

from typing import Any, Dict, Tuple

STATUS_VALUES = ("open", "in_progress", "closed")
STATUS_NEXT: Dict[str, Tuple[str, ...]] = {
    "open": ("in_progress",),
    "in_progress": ("closed",),
    "closed": (),
}

WINDOW_WEIGHT = {"walk_in": 1.0, "shift": 0.85, "day": 0.7}
STATUS_SCORE = {"open": 0.45, "in_progress": 0.72, "closed": 1.0}
OVERLOADED_BELOW = 0.6

SPECIES_RISK = {
    "canine": "routine",
    "feline": "routine",
    "exotic": "elevated",
    "equine": "elevated",
}
VISIT_CASCADE = {
    "wellness": {"next_action": "confirm_slot", "sla_minutes": 30, "queue": "front_desk"},
    "surgery": {"next_action": "pre_op", "sla_minutes": 90, "queue": "surgery"},
    "emergency": {"next_action": "triage", "sla_minutes": 10, "queue": "triage"},
    "follow_up": {"next_action": "chart_review", "sla_minutes": 45, "queue": "exam"},
}
DOSE_FORM_MG_PER_KG = {"tablet": 5.0, "liquid": 4.0, "injectable": 2.5}
DEFAULT_WEIGHT_KG = 10.0
INVOICE_BASE = {"consult": 85.0, "procedure": 240.0, "pharmacy": 42.0}
TAX_RATE = 0.08
COMMS_PRIORITY = {"reminder": "normal", "result": "high", "billing": "normal"}
AUDIT_RETENTION_DAYS = {"clinical": 2555, "billing": 2555, "access": 365}
HORIZON_BAND = {"today": "tactical", "week": "planning", "month": "strategic"}
CHART_CLASS = {
    "canine": "companion",
    "feline": "companion",
    "exotic": "specialty",
    "equine": "large_animal",
}


def envelope_status(payload: Dict[str, Any]) -> str:
    status = str(payload.get("status") or "open")
    return status if status in STATUS_VALUES else "open"


def allowed_next_status(status: str) -> Tuple[str, ...]:
    return STATUS_NEXT.get(status, ())


def clinic_load_score(status: str, window: str) -> float:
    base = STATUS_SCORE.get(status, STATUS_SCORE["open"])
    weight = WINDOW_WEIGHT.get(window, WINDOW_WEIGHT["walk_in"])
    return round(base * weight, 4)


def clinic_is_overloaded(score: float) -> bool:
    return score < OVERLOADED_BELOW


def patient_risk_band(species: str) -> str:
    return SPECIES_RISK.get(species, "routine")


def chart_class(species: str) -> str:
    return CHART_CLASS.get(species, "companion")


def appointment_cascade(visit_type: str) -> Dict[str, Any]:
    return dict(VISIT_CASCADE.get(visit_type, VISIT_CASCADE["wellness"]))


def _numeric(raw: Any, default: float) -> float:
    if raw in (None, "", "sample"):
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def daily_dose_mg(payload: Dict[str, Any], dose_form: str) -> float:
    """Weight × mg/kg. Schema sample omits numbers — use clinic defaults, never 0."""
    weight = _numeric(payload.get("weight_kg"), DEFAULT_WEIGHT_KG)
    mg_per_kg = _numeric(payload.get("mg_per_kg"), DOSE_FORM_MG_PER_KG.get(dose_form, 5.0))
    if weight <= 0:
        weight = DEFAULT_WEIGHT_KG
    if mg_per_kg <= 0:
        mg_per_kg = DOSE_FORM_MG_PER_KG.get(dose_form, 5.0)
    return round(weight * mg_per_kg, 2)


def invoice_totals(invoice_kind: str) -> Dict[str, float]:
    subtotal = INVOICE_BASE.get(invoice_kind, INVOICE_BASE["consult"])
    tax = round(subtotal * TAX_RATE, 2)
    total = round(subtotal + tax, 2)
    return {"subtotal": subtotal, "tax": tax, "total": total, "tax_rate": TAX_RATE}


def comms_priority(message_kind: str) -> str:
    return COMMS_PRIORITY.get(message_kind, "normal")


def audit_retention_days(event_category: str) -> int:
    return AUDIT_RETENTION_DAYS.get(event_category, AUDIT_RETENTION_DAYS["clinical"])


def dashboard_band(horizon: str) -> str:
    return HORIZON_BAND.get(horizon, "tactical")


def knowledge_source_class(patient_name: str, species: str) -> str:
    text = f"{patient_name} {species}".lower()
    if "exotic" in text or species == "exotic":
        return "specialty_chart"
    if "equine" in text or species == "equine":
        return "large_animal_chart"
    return "companion_chart"
