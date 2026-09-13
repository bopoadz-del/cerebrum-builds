"""erp_oracle_integration — REUSE event_bus workflow, storage, database, audit."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import (
    audit_input,
    database_input,
    event_bus_input,
    storage_input,
    validation_input,
    workflow_with_event_bus,
)
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, file.local.read, database.sql, config.runtime
# WRITES: caller.output, file.local.write, database.sql
# NEVER: forwarding the schema sample as an event_bus step input; cloning Oracle

BLOCK_IDS = ["event_bus", "workflow", "storage", "database", "audit", "validation"]

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


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Track an Oracle ERP suite workstream as delivery oversight, not a clone."""
    status = str(payload.get("status") or "open")
    if status not in STATUS_VALUES:
        status = "open"
    module = str(payload.get("suite_module") or "finance")
    if module not in MODULE_GATES:
        module = "finance"
    workstream = str(payload.get("workstream") or "erp_delivery")
    if workstream not in WORKSTREAM_FOCUS:
        workstream = "erp_delivery"
    gates = MODULE_GATES[module]
    prepared_workflow = workflow_with_event_bus(
        payload,
        [
            ("airops.erp.intake", f"erp intake {workstream}"),
            ("airops.erp.sync", f"erp sync {module}"),
            ("airops.erp.certified", f"erp interface {workstream}/{module}"),
        ],
    )
    blocks = {
        "event_bus": execute(
            "event_bus",
            event_bus_input(payload, topic="airops.erp.publish"),
            action=BLOCK_DEFAULT_ACTIONS.get("event_bus"),
        ),
        "workflow": execute(
            "workflow",
            prepared_workflow,
            action=BLOCK_DEFAULT_ACTIONS.get("workflow"),
        ),
        "storage": execute(
            "storage",
            storage_input(payload),
            action=BLOCK_DEFAULT_ACTIONS.get("storage"),
        ),
        "database": execute(
            "database",
            database_input(payload),
            action=BLOCK_DEFAULT_ACTIONS.get("database"),
        ),
        "audit": execute(
            "audit",
            audit_input(payload),
            action=BLOCK_DEFAULT_ACTIONS.get("audit"),
        ),
        "validation": execute(
            "validation",
            validation_input(payload),
            action=BLOCK_DEFAULT_ACTIONS.get("validation"),
        ),
    }
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
    return ok_envelope("erp_oracle_integration", record, blocks)
