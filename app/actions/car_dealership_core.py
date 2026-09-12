"""car_dealership_core — GENERATE. Vehicle inventory, pipeline, quotes, service, CRM, packs."""

from __future__ import annotations

from typing import Any, Dict, List

from app.persist import ok_envelope

# READS: caller.input
# WRITES: caller.output
# NEVER: inventing unverified Store block ids

BLOCK_IDS: list[str] = []


def _vehicle_unit(payload: Dict[str, Any]) -> Dict[str, Any]:
    reference = str(payload.get("reference") or "sample")
    vin = str(payload.get("vin") or reference)
    return {
        "stock_number": reference,
        "vin": vin,
        "condition": "used" if vin.lower().startswith("u") else "new",
        "status": payload.get("status", "open"),
    }


def _sales_pipeline(payload: Dict[str, Any]) -> Dict[str, Any]:
    status = payload.get("status", "open")
    stage = {
        "open": "lead",
        "in_progress": "negotiation",
        "closed": "delivered",
    }.get(status, "lead")
    return {
        "reference": payload.get("reference", "sample"),
        "stage": stage,
        "customer_name": payload.get("customer_name") or "sample",
        "status": status,
    }


def _finance_quote(payload: Dict[str, Any]) -> Dict[str, Any]:
    deal_type = str(payload.get("deal_type") or "retail")
    return {
        "deal_type": deal_type,
        "term_months": 36 if deal_type == "lease" else 60,
        "apr_bps": 0 if deal_type == "retail" else 649,
        "monthly": 0,
        "status": payload.get("status", "open"),
    }


def _service_appointment(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "reference": payload.get("reference", "sample"),
        "vin": payload.get("vin") or payload.get("reference") or "sample",
        "channel": "mcp",
        "status": payload.get("status", "open"),
    }


def _customer_card(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "customer_name": payload.get("customer_name") or "sample",
        "reference": payload.get("reference", "sample"),
        "status": payload.get("status", "open"),
    }


def _deal_document_pack(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    status = payload.get("status", "open")
    return [
        {"doc": "buyers_order", "status": status},
        {"doc": "finance_or_lease_contract", "status": status},
        {"doc": "odometer_disclosure", "status": "closed" if status == "closed" else status},
    ]


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Author the dealership kernel from the envelope. No Store blocks are bound."""
    record = {
        **payload,
        "vehicle_inventory": [_vehicle_unit(payload)],
        "sales_pipeline": _sales_pipeline(payload),
        "finance_quote": _finance_quote(payload),
        "service_appointment": _service_appointment(payload),
        "customer_crm": _customer_card(payload),
        "deal_document_pack": _deal_document_pack(payload),
    }
    return ok_envelope("car_dealership_core", record)
