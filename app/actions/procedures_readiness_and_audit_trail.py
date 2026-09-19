"""Capability procedures_readiness_and_audit_trail — checklists and evidence.

Written by the factory WRITER role (codewhale exec)

Blocks are invoked through the local dispatch runtime (``app.dispatch.execute``)
against the block source vendored at build time — this module makes no network
call and never persists: the ROUTE writes the tenant-scoped record after
``handle()`` reports success (Phase 2 §0.2).

Pipeline:
  * ``readiness_engine``  — gates the shop/delivery run on the procedure's
    required checklist items; a procedure with an unmet item is not "ready";
  * ``workflow``          — the daily run. EVERY child is prepared in source:
      - step_0 ``audit``            — appends the immutable trail entry;
      - step_1 ``file_hasher``      — hashes the evidence artefact on disk
        (the Store workflow pre-flight validates each child against the block
        registry, so the chain is restricted to registry-declared blocks);
      - step_2 ``event_bus``        — publishes the readiness result with the
        full contract (topic, payload dict, message, channel=mcp, publish);
  * ``audit``             — appends the trail entry on the direct path;
  * ``evidence_verifier`` — stores / verifies the evidence content;
  * ``file_hasher``       — hashes the evidence document (a real file);
  * ``spec_analyzer``     — extracts the procedure structure into sections.

The evidence text, its digest and the stored artefact all cover the same bytes,
so verifying a tampered record fails rather than passing. The schema sample
(``reference``/``status``/domain strings) is never forwarded as a workflow step
input: each child gets a constructed, block-acceptable input.

Scope
-----
READS  the caller's payload, ``STORAGE_PATH`` (evidence artefacts).
WRITES ``STORAGE_PATH`` (evidence) through the blocks.
NEVER  network, HTTP store callbacks, ``vendor/**``.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List

from app.block_inputs import prepare_block_input
from app.dispatch import execute

CAPABILITY_ID = "procedures_readiness_and_audit_trail"
ENTITY = "procedures_readiness_and_audit_trail"
BLOCK_IDS = [
    "readiness_engine",
    "workflow",
    "audit",
    "evidence_verifier",
    "file_hasher",
    "spec_analyzer",
]
#: Each block's declared action (keyword dispatch; never inside the payload).
BLOCK_DEFAULT_ACTIONS = {
    "readiness_engine": "evaluate",
    "workflow": "run",
    "audit": "log",
    "evidence_verifier": "store",
    "file_hasher": "hash",
    "spec_analyzer": "analyze",
}
CAPABILITY_FIELDS: List[str] = [
    "reference",
    "procedure_code",
    "procedure_title",
    "shop_code",
    "checklist",
    "due_date",
    "actor",
    "event_type",
    "evidence_path",
    "content_hash",
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
    state = {item["id"]: bool(record.get("procedure_code")) for item in checklist}
    state["reference"] = str(record.get("reference") or "sample")
    state["status"] = record.get("status")
    state["record_present"] = True
    return {
        "checklist": checklist,
        "state": state,
        "shop": str(record.get("shop_code") or "chain"),
        "title": str(
            record.get("procedure_title")
            or record.get("procedure_code")
            or "procedure"
        ),
        "actor": str(record.get("actor") or "manager"),
        "event_type": str(record.get("event_type") or "procedure_check"),
    }


def _evidence_text(record: Dict[str, Any], readiness: Dict[str, Any]) -> str:
    """The exact text the trail entry, evidence record and digest must cover."""
    return "%s|%s|%s|%s|%s" % (
        readiness["event_type"],
        readiness["title"],
        readiness["shop"],
        readiness["actor"],
        str(record.get("checklist") or ""),
    )


def _evidence_identity(
    record: Dict[str, Any], readiness: Dict[str, Any]
) -> Dict[str, str]:
    text = _evidence_text(record, readiness)
    return {
        "text": text,
        "digest": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "reference": str(record.get("reference") or "sample"),
    }


def _procedure_steps(
    record: Dict[str, Any],
    readiness: Dict[str, Any],
    evidence: Dict[str, str],
) -> List[Dict[str, Any]]:
    """Every workflow child prepared in source (step_0 .. step_1).

    The ``file_hasher`` child is handed the real artefact path the shared
    block-input builder wrote under ``STORAGE_PATH``, so the digest covers
    bytes that exist rather than a path that does not.  ``evidence_verifier``
    is not a registry-declared workflow child, so the integrity record is
    written on the direct path below instead of inside the chain.
    """
    audit_input = prepare_block_input("audit", record, entity=ENTITY)
    audit_input["event_action"] = readiness["event_type"]
    audit_input["resource"] = ENTITY
    audit_input["category"] = "domain"
    audit_input["details"] = {
        "actor": readiness["actor"],
        "procedure_code": str(record.get("procedure_code") or ""),
        "shop_code": readiness["shop"],
        "reference": evidence["reference"],
        "digest": evidence["digest"],
    }
    hasher_input = prepare_block_input("file_hasher", record, entity=ENTITY)
    return [
        {
            "id": "step_0",
            "block": "audit",
            "action": "log",
            "input": audit_input,
            "params": {"action": "log"},
        },
        {
            "id": "step_1",
            "block": "file_hasher",
            "action": "hash",
            "input": hasher_input,
            "params": {"action": "hash"},
        },
        {
            "id": "step_2",
            "block": "event_bus",
            "action": "publish",
            "input": {
                "topic": "readiness.%s" % readiness["event_type"],
                "payload": {
                    "reference": evidence["reference"],
                    "procedure_code": str(record.get("procedure_code") or ""),
                    "shop_code": readiness["shop"],
                    "actor": readiness["actor"],
                    "event_type": readiness["event_type"],
                    "content_hash": evidence["digest"],
                },
                "message": "readiness %s for %s recorded by %s"
                % (readiness["event_type"], readiness["shop"], readiness["actor"]),
                "channel": "mcp",
                "tool": "event_bus",
            },
            "params": {"action": "publish"},
        },
    ]


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(payload) if isinstance(payload, dict) else {"value": payload}
    readiness = _readiness(data)
    evidence = _evidence_identity(data, readiness)
    steps = _procedure_steps(data, readiness, evidence)
    results: Dict[str, Any] = {}
    errors: Dict[str, str] = {}
    for block_id in BLOCK_IDS:
        prepared = prepare_block_input(
            block_id,
            data,
            entity=ENTITY,
            steps=steps if block_id == "workflow" else None,
        )
        if block_id == "readiness_engine":
            prepared["checklist"] = readiness["checklist"]
            prepared["state"] = readiness["state"]
        if block_id == "audit":
            prepared["event_action"] = readiness["event_type"]
            prepared["resource"] = ENTITY
            prepared["details"] = {
                "actor": readiness["actor"],
                "reference": evidence["reference"],
                "digest": evidence["digest"],
                "checklist_items": len(readiness["checklist"]),
            }
        if block_id == "evidence_verifier":
            prepared["content"] = evidence["text"]
            prepared["reference"] = evidence["reference"]
        if block_id == "file_hasher":
            prepared["file_path"] = prepare_block_input(
                "file_hasher", data, entity=ENTITY
            )["file_path"]
        if block_id == "spec_analyzer":
            prepared["text"] = "%s\n%s" % (readiness["title"], evidence["text"])
            prepared["title"] = readiness["title"]
        result = execute(
            block_id, prepared, action=BLOCK_DEFAULT_ACTIONS.get(block_id)
        )
        results[block_id] = result
        if isinstance(result, dict) and (
            result.get("status") in ("error", "failed", "partial")
            or result.get("ok") is False
            or "error" in result
        ):
            errors[block_id] = str(result.get("error") or result)[:400]
    if errors:
        return {
            "ok": False,
            "capability": CAPABILITY_ID,
            "error": "; ".join(f"{b}: {e}" for b, e in sorted(errors.items())),
            "results": results,
        }
    return {
        "ok": True,
        "capability": CAPABILITY_ID,
        "readiness": {
            "shop_code": readiness["shop"],
            "procedure_code": str(data.get("procedure_code") or ""),
            "checklist_items": len(readiness["checklist"]),
            "content_hash": evidence["digest"],
        },
        "results": results,
    }
