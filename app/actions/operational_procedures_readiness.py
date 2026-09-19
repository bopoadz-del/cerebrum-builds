"""Capability operational_procedures_readiness — procedures as daily checklists.

Written by the factory WRITER role (codewhale exec)

Blocks are invoked through the local dispatch runtime (``app.dispatch.execute``)
against the block source vendored at build time — this module makes no network
call and never persists: the ROUTE writes the tenant-scoped record after
``handle()`` reports success (Phase 2 §0.2).

Pipeline:
  * ``readiness_engine`` — gates the shop on the procedure's required checklist
    items (a procedure with an unmet item is not "ready");
  * ``workflow``         — the daily run: a database step writes the procedure
    and a validation step checks the checklist record it was given;
  * ``knowledge``        — answers the shop's question over the uploaded
    procedure corpus;
  * ``notification``     — sends the checklist notice over the MCP channel;
  * ``validation``       — runs the five-stage pipeline over the procedure record.

Scope
-----
READS  the caller's payload, ``STORAGE_PATH`` (procedure corpus).
WRITES nothing (dispatch results are returned; the route persists).
NEVER  network, HTTP store callbacks, ``vendor/**``.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.block_inputs import prepare_block_input
from app.dispatch import execute

CAPABILITY_ID = "operational_procedures_readiness"
ENTITY = "operational_procedures_readiness"
BLOCK_IDS = [
    "readiness_engine",
    "workflow",
    "knowledge",
    "notification",
    "validation",
]
#: Each block's declared action (keyword dispatch; never inside the payload).
BLOCK_DEFAULT_ACTIONS = {
    "readiness_engine": "evaluate",
    "workflow": "run",
    "knowledge": "ask",
    "notification": "send",
    "validation": "validate_pipeline",
}
CAPABILITY_FIELDS: List[str] = [
    "reference",
    "procedure_code",
    "procedure_title",
    "shop_code",
    "checklist",
    "due_date",
    "notes",
    "status",
]


def _checklist_items(record: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The required checklist items the shop must acknowledge."""
    raw = str(record.get("checklist") or "")
    items = [part.strip() for part in raw.replace(";", ",").split(",") if part.strip()]
    if not items:
        items = ["procedure_uploaded"]
    return [{"id": item, "required": True} for item in items]


def _readiness(record: Dict[str, Any]) -> Dict[str, Any]:
    """Checklist plus the state each item is acknowledged in."""
    checklist = _checklist_items(record)
    state = {
        item["id"]: bool(record.get("procedure_code"))
        for item in checklist
    }
    state["reference"] = str(record.get("reference") or "sample")
    state["status"] = record.get("status")
    state["record_present"] = True
    return {
        "checklist": checklist,
        "state": state,
        "shop": str(record.get("shop_code") or "chain"),
        "title": str(record.get("procedure_title") or record.get("procedure_code") or "procedure"),
    }


def _procedure_steps(record: Dict[str, Any], readiness: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Prepared workflow children: procedure write, then the shop notice."""
    values = prepare_block_input("database", record, entity=ENTITY)["values"]
    validation = prepare_block_input("validation", record, entity=ENTITY)
    validation["item"] = {
        "id": str(record.get("reference") or "sample"),
        "type": ENTITY,
        "checklist_items": len(readiness["checklist"]),
    }
    validation["context"] = {"entity": ENTITY, "shop_code": readiness["shop"]}
    return [
        {
            "id": "step_0",
            "block": "database",
            "action": "insert",
            "input": {"table": ENTITY, "values": values},
            "params": {"action": "insert"},
        },
        {
            "id": "step_1",
            "block": "validation",
            "action": "validate_pipeline",
            "input": validation,
            "params": {"action": "validate_pipeline"},
        },
    ]


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(payload) if isinstance(payload, dict) else {"value": payload}
    readiness = _readiness(data)
    steps = _procedure_steps(data, readiness)
    results: Dict[str, Any] = {}
    errors: Dict[str, str] = {}
    for block_id in BLOCK_IDS:
        prepared = prepare_block_input(
            block_id, data, entity=ENTITY, steps=steps if block_id == "workflow" else None
        )
        if block_id == "readiness_engine":
            prepared["checklist"] = readiness["checklist"]
            prepared["state"] = readiness["state"]
        if block_id == "knowledge":
            prepared["query"] = readiness["title"]
            prepared["collection"] = "bakery_procedures"
            prepared["tenant_id"] = "local"
            prepared["documents"] = [
                {
                    "doc_id": str(data.get("procedure_code") or "procedure"),
                    "text": "%s %s" % (readiness["title"], data.get("checklist") or ""),
                }
            ]
        if block_id == "notification":
            prepared["message"] = "%s: procedure %s due %s" % (
                readiness["shop"],
                readiness["title"],
                data.get("due_date") or "unscheduled",
            )
        if block_id == "validation":
            item = dict(prepared.get("item") or {})
            item.setdefault("id", str(data.get("reference") or "sample"))
            item.setdefault("type", ENTITY)
            prepared["item"] = item
        result = execute(
            block_id, prepared, action=BLOCK_DEFAULT_ACTIONS.get(block_id)
        )
        results[block_id] = result
        if isinstance(result, dict) and (
            result.get("status") in ("error", "failed", "partial")
            or result.get("ok") is False
            or "error" in result
        ):
            errors[block_id] = str(result.get("error") or result)[:200]
    if errors:
        return {
            "ok": False,
            "capability": CAPABILITY_ID,
            "error": "; ".join(f"{b}: {e}" for b, e in sorted(errors.items())),
            "results": results,
        }
    return {"ok": True, "capability": CAPABILITY_ID, "results": results}
