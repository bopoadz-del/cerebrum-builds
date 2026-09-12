"""car_dealership_core — GENERATE. Vehicle inventory, pipeline, quotes, service, CRM, packs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.persist import ok_envelope

# READS: caller.input
# WRITES: caller.output
# NEVER: inventing unverified Store block ids

BLOCK_IDS: list[str] = []

STATUS_VALUES = ("open", "in_progress", "closed")
STATUS_NEXT: Dict[str, Tuple[str, ...]] = {
    "open": ("in_progress",),
    "in_progress": ("closed",),
    "closed": (),
}

# Envelope status → live desk stages. Closed is delivered, not a sample label.
PIPELINE_STAGES: Dict[str, Tuple[str, ...]] = {
    "open": ("lead", "contacted", "visit_scheduled"),
    "in_progress": ("appraisal", "negotiation", "desking", "f_and_i"),
    "closed": ("delivered",),
}

DOC_PACK: Tuple[str, ...] = (
    "buyers_order",
    "credit_application",
    "finance_or_lease_contract",
    "odometer_disclosure",
    "window_sticker_or_buyers_guide",
    "privacy_notice",
)

# VIN transliteration for ISO 3779 check digit (I, O, Q are illegal).
_VIN_MAP = {
    "A": 1,
    "B": 2,
    "C": 3,
    "D": 4,
    "E": 5,
    "F": 6,
    "G": 7,
    "H": 8,
    "J": 1,
    "K": 2,
    "L": 3,
    "M": 4,
    "N": 5,
    "P": 7,
    "R": 9,
    "S": 2,
    "T": 3,
    "U": 4,
    "V": 5,
    "W": 6,
    "X": 7,
    "Y": 8,
    "Z": 9,
}
_VIN_WEIGHTS = (8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2)

DEFAULT_ASKING = 32990.0
DEFAULT_DOWN = 2000.0
DEFAULT_DOC_FEE = 699.0
DEFAULT_ACQ_FEE = 695.0
DEFAULT_RESIDUAL_PCT = 0.55
RETAIL_APR = 5.99
FINANCE_APR = 6.49
LEASE_MONEY_FACTOR = 0.00249


def _status(payload: Dict[str, Any]) -> str:
    status = str(payload.get("status") or "open")
    return status if status in STATUS_VALUES else "open"


def _reference(payload: Dict[str, Any]) -> str:
    return str(payload.get("reference") or "sample")


def _as_money(payload: Dict[str, Any], key: str, default: float) -> float:
    raw = payload.get(key)
    if raw in (None, "", "sample"):
        return float(default)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return float(default)
    if value <= 0:
        return float(default)
    return round(value, 2)


def _as_int(payload: Dict[str, Any], key: str, default: int, *, lo: int, hi: int) -> int:
    raw = payload.get(key)
    if raw in (None, "", "sample"):
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, value))


def _cents(value: float) -> float:
    return round(float(value), 2)


def vin_check_digit_ok(vin: str) -> bool:
    token = (vin or "").strip().upper()
    if len(token) != 17:
        return False
    if any(ch in "IOQ" for ch in token):
        return False
    total = 0
    for index, char in enumerate(token):
        if char.isdigit():
            value = int(char)
        elif char in _VIN_MAP:
            value = _VIN_MAP[char]
        else:
            return False
        total += value * _VIN_WEIGHTS[index]
    remainder = total % 11
    check = "X" if remainder == 10 else str(remainder)
    return token[8] == check


def _condition(vin: str, payload: Dict[str, Any]) -> str:
    declared = str(payload.get("condition") or "").strip().lower()
    if declared in {"new", "used", "cpo"}:
        return declared
    token = vin.lower()
    if token.startswith("u") or token.startswith("used"):
        return "used"
    if token.startswith("cpo"):
        return "cpo"
    return "new"


def _availability(status: str) -> str:
    return {"open": "available", "in_progress": "reserved", "closed": "sold"}[status]


def _vehicle_unit(payload: Dict[str, Any]) -> Dict[str, Any]:
    reference = _reference(payload)
    vin = str(payload.get("vin") or reference)
    status = _status(payload)
    asking = _as_money(payload, "asking_price", DEFAULT_ASKING)
    cost = _as_money(payload, "unit_cost", asking * 0.91)
    return {
        "stock_number": reference,
        "vin": vin,
        "vin_checksum_ok": vin_check_digit_ok(vin),
        "condition": _condition(vin, payload),
        "availability": _availability(status),
        "asking_price": asking,
        "unit_cost": _cents(cost),
        "holdback": _cents(asking * 0.02),
        "days_in_stock": _as_int(payload, "days_in_stock", 12, lo=0, hi=999),
        "recon_needed": _condition(vin, payload) != "new",
        "status": status,
    }


def _advance_stage(sequence: Sequence[str], payload: Dict[str, Any]) -> str:
    requested = str(payload.get("stage") or "").strip().lower()
    if requested in sequence:
        return requested
    if len(sequence) == 1:
        return sequence[0]
    # open starts at lead; in_progress lands on the last live desk stage
    if _status(payload) == "open":
        return sequence[0]
    return sequence[-1]


def _sales_pipeline(payload: Dict[str, Any]) -> Dict[str, Any]:
    status = _status(payload)
    sequence = PIPELINE_STAGES[status]
    stage = _advance_stage(sequence, payload)
    return {
        "reference": _reference(payload),
        "customer_name": payload.get("customer_name") or "sample",
        "status": status,
        "stage": stage,
        "stage_sequence": list(sequence),
        "allowed_next_status": list(STATUS_NEXT[status]),
        "can_close": status == "in_progress",
        "is_terminal": status == "closed",
    }


def _amortized_monthly(principal: float, apr_annual: float, term_months: int) -> float:
    if term_months <= 0:
        raise ValueError("term_months must be positive")
    if principal <= 0:
        raise ValueError("principal must be positive")
    rate = apr_annual / 12.0 / 100.0
    if rate <= 0:
        return _cents(principal / term_months)
    factor = (1.0 + rate) ** term_months
    payment = principal * (rate * factor) / (factor - 1.0)
    return _cents(payment)


def _lease_monthly(cap_cost: float, residual: float, money_factor: float, term_months: int) -> float:
    if term_months <= 0:
        raise ValueError("term_months must be positive")
    depreciation = (cap_cost - residual) / term_months
    rent = (cap_cost + residual) * money_factor
    return _cents(depreciation + rent)


def _apr_for(deal_type: str, payload: Dict[str, Any]) -> float:
    raw = payload.get("apr")
    if raw not in (None, "", "sample"):
        try:
            value = float(raw)
            if value > 0:
                return value
        except (TypeError, ValueError):
            pass
    return FINANCE_APR if deal_type == "finance" else RETAIL_APR


def _finance_quote(payload: Dict[str, Any]) -> Dict[str, Any]:
    deal_type = str(payload.get("deal_type") or "retail")
    if deal_type not in {"retail", "finance", "lease"}:
        deal_type = "retail"
    asking = _as_money(payload, "asking_price", DEFAULT_ASKING)
    down = _as_money(payload, "down_payment", DEFAULT_DOWN)
    trade = _as_money(payload, "trade_allowance", 0.01)
    if payload.get("trade_allowance") in (None, "", "sample", 0, 0.0, "0"):
        trade = 0.0
    fees = DEFAULT_DOC_FEE + (DEFAULT_ACQ_FEE if deal_type == "lease" else 0.0)
    cap = max(asking + fees - down - trade, 500.0)
    status = _status(payload)

    if deal_type == "lease":
        term = _as_int(payload, "term_months", 36, lo=24, hi=48)
        residual = _cents(asking * DEFAULT_RESIDUAL_PCT)
        monthly = _lease_monthly(cap, residual, LEASE_MONEY_FACTOR, term)
        apr = _cents(LEASE_MONEY_FACTOR * 2400.0)
        due_at_signing = _cents(down + monthly + DEFAULT_ACQ_FEE)
        return {
            "deal_type": deal_type,
            "quote_basis": "lease_money_factor",
            "term_months": term,
            "apr_bps": int(round(apr * 100)),
            "money_factor": LEASE_MONEY_FACTOR,
            "cap_cost": _cents(cap),
            "residual": residual,
            "amount_financed": _cents(cap),
            "monthly": monthly,
            "due_at_signing": due_at_signing,
            "total_of_payments": _cents(monthly * term),
            "status": status,
        }

    term = _as_int(payload, "term_months", 60, lo=24, hi=84)
    apr = _apr_for(deal_type, payload)
    monthly = _amortized_monthly(cap, apr, term)
    return {
        "deal_type": deal_type,
        "quote_basis": "amortizing_loan" if deal_type == "finance" else "retail_cash_plus_conventional",
        "term_months": term,
        "apr_bps": int(round(apr * 100)),
        "money_factor": None,
        "cash_price": asking,
        "amount_financed": _cents(cap),
        "monthly": monthly,
        "due_at_signing": _cents(down + DEFAULT_DOC_FEE),
        "total_of_payments": _cents(monthly * term),
        "status": status,
    }


def _service_appointment(payload: Dict[str, Any]) -> Dict[str, Any]:
    status = _status(payload)
    slot = {
        "open": "unscheduled",
        "in_progress": "checked_in",
        "closed": "closed_ro",
    }[status]
    concern = str(payload.get("concern") or "multi_point_inspection")
    return {
        "reference": _reference(payload),
        "ro_number": f"RO-{_reference(payload)}",
        "vin": payload.get("vin") or payload.get("reference") or "sample",
        "channel": "mcp",
        "concern": concern,
        "slot": slot,
        "technician_skill": "general" if concern == "multi_point_inspection" else "line",
        "status": status,
        "allowed_next_status": list(STATUS_NEXT[status]),
        "clocked": status != "open",
    }


def _customer_card(payload: Dict[str, Any]) -> Dict[str, Any]:
    status = _status(payload)
    name = str(payload.get("customer_name") or "sample")
    last_touch = {
        "open": "lead_capture",
        "in_progress": "desk_negotiation",
        "closed": "delivery",
    }[status]
    return {
        "customer_name": name,
        "reference": _reference(payload),
        "household_key": f"hh-{abs(hash(name.lower())) % 10_000_000:07d}",
        "source": "showroom" if name != "sample" else "schema_sample",
        "consent_marketing": False,
        "last_touch": last_touch,
        "do_not_contact": False,
        "status": status,
        "allowed_next_status": list(STATUS_NEXT[status]),
    }


def _doc_status(deal_status: str, doc: str) -> str:
    if deal_status == "closed":
        return "closed"
    if deal_status == "in_progress":
        if doc in {"buyers_order", "credit_application", "odometer_disclosure"}:
            return "in_progress"
        return "open"
    if doc in {"buyers_order", "credit_application"}:
        return "open"
    return "open"


def _deal_document_pack(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    status = _status(payload)
    pack: List[Dict[str, Any]] = []
    signed_at: Optional[str] = None
    if status == "closed":
        signed_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    for doc in DOC_PACK:
        current = _doc_status(status, doc)
        pack.append(
            {
                "doc": doc,
                "status": current,
                "required_for_close": True,
                "transition_from": _doc_status("open", doc),
                "transition_to": current,
                "signed_at": signed_at if current == "closed" else None,
            }
        )
    return pack


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Author the dealership kernel from the envelope. No Store blocks are bound."""
    status = _status(payload)
    record = {
        **payload,
        "status": status,
        "vehicle_inventory": [_vehicle_unit(payload)],
        "sales_pipeline": _sales_pipeline(payload),
        "finance_quote": _finance_quote(payload),
        "service_appointment": _service_appointment(payload),
        "customer_crm": _customer_card(payload),
        "deal_document_pack": _deal_document_pack(payload),
        "status_transitions": {
            "current": status,
            "allowed_next": list(STATUS_NEXT[status]),
        },
    }
    return ok_envelope("car_dealership_core", record)
