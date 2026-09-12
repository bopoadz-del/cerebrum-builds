"""kpi_value_realization — GENERATE. KPI and benefit tracking for RX portfolio."""

from __future__ import annotations

from typing import Any, Dict

from app.persist import ok_envelope

# READS: caller.input
# WRITES: caller.output
# NEVER: inventing unverified Store block ids

BLOCK_IDS: list[str] = []

STATUS_VALUES = ("open", "in_progress", "closed")
STREAM_TARGET = {
    "network": 100,
    "digital": 85,
    "erp": 70,
    "ops": 90,
}


def _status(payload: Dict[str, Any]) -> str:
    status = str(payload.get("status") or "open")
    return status if status in STATUS_VALUES else "open"


def _stream(payload: Dict[str, Any]) -> str:
    value = str(payload.get("value_stream") or "network")
    return value if value in STREAM_TARGET else "network"


def _progress(status: str) -> int:
    return {"open": 15, "in_progress": 55, "closed": 100}[status]


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Score a KPI against its value-stream target from the envelope."""
    status = _status(payload)
    stream = _stream(payload)
    target = STREAM_TARGET[stream]
    realized = int(round(target * _progress(status) / 100.0))
    record = {
        **payload,
        "status": status,
        "kpi_card": {
            "kpi_name": str(payload.get("kpi_name") or payload.get("reference") or "sample"),
            "value_stream": stream,
            "target": target,
            "realized": realized,
            "gap": target - realized,
            "realization_pct": _progress(status),
            "benefits_locked": status == "closed",
        },
    }
    return ok_envelope("kpi_value_realization", record)
