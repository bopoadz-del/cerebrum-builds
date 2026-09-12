"""oracle_erp_program_oversight — GENERATE. ERP delivery workstream, not an Oracle clone."""

from __future__ import annotations

from typing import Any, Dict

from app.persist import ok_envelope

# READS: caller.input
# WRITES: caller.output
# NEVER: inventing unverified Store block ids; cloning Oracle product surfaces

BLOCK_IDS: list[str] = []

STATUS_VALUES = ("open", "in_progress", "closed")
MODULE_GATES = {
    "finance": ("chart_of_accounts", "period_close_rehearsal"),
    "procurement": ("supplier_cutover", "po_parity"),
    "hcm": ("org_tree", "payroll_parallel"),
}
WORKSTREAM_FOCUS = {
    "erp_delivery": "suite_program",
    "integration": "interface_map",
    "cutover": "go_live_runbook",
}


def _status(payload: Dict[str, Any]) -> str:
    status = str(payload.get("status") or "open")
    return status if status in STATUS_VALUES else "open"


def _module(payload: Dict[str, Any]) -> str:
    value = str(payload.get("suite_module") or "finance")
    return value if value in MODULE_GATES else "finance"


def _workstream(payload: Dict[str, Any]) -> str:
    value = str(payload.get("workstream") or "erp_delivery")
    return value if value in WORKSTREAM_FOCUS else "erp_delivery"


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Track an Oracle ERP suite workstream as delivery oversight, not a clone."""
    status = _status(payload)
    module = _module(payload)
    workstream = _workstream(payload)
    gates = MODULE_GATES[module]
    record = {
        **payload,
        "status": status,
        "erp_oversight": {
            "workstream": workstream,
            "focus": WORKSTREAM_FOCUS[workstream],
            "suite_module": module,
            "gates": list(gates),
            "active_gate": gates[0] if status != "closed" else gates[-1],
            "is_oracle_clone": False,
            "delivery_only": True,
            "cutover_ready": status == "closed",
        },
    }
    return ok_envelope("oracle_erp_program_oversight", record)
