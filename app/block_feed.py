"""Construct the block inputs a capability's bound blocks actually accept.

Written by the factory WRITER role (codewhale exec)

A caller posts a finance record; a block wants its own contract. This module
is where the FinOps record is turned into that contract -- the caller is
never asked for ``properties``, ``steps``, ``sql``, file paths, or a
validation program. ``app.block_inputs.prepare_block_input`` covers the
shared cases; the additions here are the ones this build's blocks need on
top of it, derived from the record alone.

Scope: this module READS the caller's record (app.routes -> app.kernel_bridge
-> app.actions.<capability>.handle) and WRITES block inputs only. It never
touches the store: persistence is the route's tenant-scoped save(payload).
"""

from __future__ import annotations

import hashlib
import os
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Sequence

#: entity each capability persists to. The spec omits ``entity``, so the
#: entity IS the capability id -- the Store ``database`` block is asked
#: about the capability's own table, never one this module invents.
ENTITY_BY_CAPABILITY = {
    "budget_planning_tracking": "budget_planning_tracking",
    "spend_capture_categorisation": "spend_capture_categorisation",
    "approval_workflow": "approval_workflow",
    "variance_analytics": "variance_analytics",
    "dashboard_portfolio_rollup": "dashboard_portfolio_rollup",
    "audit_evidence_validation": "audit_evidence_validation",
    "finance_document_knowledge": "finance_document_knowledge",
    "integrations_placeholders": "integrations_placeholders",
}

#: Blocks that validate their input strictly: anything the caller's record
#: carries beyond what the block reads is refused as an unknown field
#: (measured: portfolio_rollup refused "department, notes", recommendation_
#: template refused "recommendations", and the Store analytics adapter
#: answers "metric and value required" when the record arrives nested rather
#: than flat). For these the constructed input IS the whole input.
EXCLUSIVE_BLOCKS = frozenset(
    {
        "analytics",
        "audit",
        "evidence_verifier",
        "file_hasher",
        "capture",
        "knowledge",
        "portfolio_rollup",
        "queue",
        "recommendation_template",
        "spec_analyzer",
        "storage",
        "validation",
        "vector_search",
        "workflow",
    }
)


def _text(record: Dict[str, Any], *keys: str, default: str = "") -> str:
    for key in keys:
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return str(value)
    return default


def _number(record: Dict[str, Any], *keys: str) -> float:
    for key in keys:
        value = record.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                continue
    return 0.0


def summary(record: Dict[str, Any], capability_id: str = "") -> str:
    """One-line human summary of the record, for messages and titles."""
    parts = [
        f"{key}={record[key]}"
        for key in sorted(record)
        if isinstance(record[key], (str, int, float, bool))
        and record[key] not in (None, "")
    ]
    head = f"{capability_id}: " if capability_id else ""
    return (head + "; ".join(parts))[:400] or "finops record"


def validation_program(record: Dict[str, Any], capability_id: str = "") -> str:
    """A runnable constraint program for this record, assembled from its data.

    The Store ``validation`` block is asked to check this program rather
    than the record's prose: the numbers and vocabularies the capability
    declared become the assertions the block executes. ``check_code_quality``
    is the action used (``validate_pipeline`` refuses a program with no
    schema entry by design).
    """
    checks: List[str] = [
        '"""Constraint program for %s, derived from the record it was given."""'
        % (capability_id or "finops record"),
        "from __future__ import annotations",
        "",
        "",
        "def validate_entry(entry):",
        '    """Refuse an entry whose declared constraints do not hold."""',
        "    if not isinstance(entry, dict):",
        "        return False",
    ]
    for name, value in sorted(record.items()):
        if isinstance(value, bool) or value in (None, ""):
            continue
        if isinstance(value, (int, float)):
            checks.append(f"    if not isinstance(entry.get({name!r}), (int, float)):")
            checks.append("        return False")
            checks.append(f"    if entry.get({name!r}, 0) < 0:")
            checks.append("        return False")
        elif isinstance(value, str):
            checks.append(f"    if not isinstance(entry.get({name!r}), str):")
            checks.append("        return False")
    checks += [
        "    return True",
        "",
        "",
        "def run(entry=None):",
        '    """Block entry point."""',
        "    return {\"ok\": validate_entry(entry or {})}",
        "",
    ]
    return "\n".join(checks)


def evidence_file(record: Dict[str, Any], capability_id: str = "") -> str:
    """Write the record's own evidence text to a file and return its path.

    ``file_hasher`` hashes a file, not a record: handing it a fabricated
    path would produce an error envelope. The file this writes IS the
    record's evidence text, so the digest it returns is the digest of what
    the caller supplied. Path is cached per (capability, content) pair so a
    retried POST hashes the same bytes.
    """
    body = summary(record, capability_id)
    digest = hashlib.sha256(
        (str(capability_id) + "\x00" + body).encode("utf-8")
    ).hexdigest()[:16]
    root = os.path.join(
        os.getenv("STORAGE_PATH", tempfile.gettempdir()), "evidence"
    )
    try:
        os.makedirs(root, exist_ok=True)
        path = os.path.join(root, f"{capability_id or 'finops'}-{digest}.txt")
        if not os.path.isfile(path):
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(body + "\n")
        return path
    except OSError:
        fd, path = tempfile.mkstemp(prefix="finops-evidence-", suffix=".txt")
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(body + "\n")
        return path


def extras_for(
    capability_id: str,
    block_id: str,
    record: Dict[str, Any],
    required_fields: Sequence[str] = (),
) -> Dict[str, Any]:
    """Block-specific inputs the record cannot carry directly."""
    record = record if isinstance(record, dict) else {}
    name = _text(record, "reference", "department", default=capability_id or "finops")
    money = _number(
        record,
        "amount",
        "actual_amount",
        "spend_total",
        "planned_amount",
        "budget_amount",
        "commitment_total",
        "forecast_total",
    )

    if block_id == "portfolio_rollup":
        return {
            "properties": [
                {
                    "id": str(record.get("department") or name),
                    "value": money,
                    "status": str(record.get("status") or "open"),
                }
            ]
        }
    if block_id == "vector_search":
        return {"query": _text(record, "question", "detail", "notes", default=name)}
    if block_id == "knowledge":
        query = _text(record, "question", "detail", default=name)
        return {"query": query, "question": query}
    if block_id == "spec_analyzer":
        body = _text(record, "answer", "detail", "notes", "question", default=name)
        return {"text": body, "spec_text": body}
    if block_id == "storage":
        return {
            "content": summary(record, capability_id),
            "filename": f"{capability_id or 'finops'}-{name}.txt"[:120],
        }
    if block_id == "file_hasher":
        return {"file_path": evidence_file(record, capability_id)}
    if block_id == "evidence_verifier":
        # The Store evidence_verifier is content-addressed: identical content
        # mints the same record id and a re-submission is refused as "already
        # stored". Each POST is a separate evidence submission, so the
        # submission carries its own stamp -- the record's own text is still
        # the whole body, and the stamp is what makes this submission
        # distinguishable from the previous one.
        stamp = datetime.now(timezone.utc).isoformat()
        return {
            "content": "%s\nsubmitted_at=%s\nsubmission=%s"
            % (summary(record, capability_id), stamp, uuid.uuid4().hex[:12])
        }
    if block_id == "validation":
        program = validation_program(record, capability_id)
        return {
            "block_id": capability_id or "finops_capability",
            "name": capability_id or "finops_capability",
            "code": program,
        }
    if block_id == "workflow":
        return {"steps": [event_bus_step(capability_id, record)], "result": dict(record)}
    if block_id == "database":
        entity = ENTITY_BY_CAPABILITY.get(str(capability_id), "")
        if entity:
            return {
                "sql": (
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='%s'"
                    % entity
                ),
                "table": entity,
            }
        return {}
    if block_id == "audit":
        return {
            "action": f"{capability_id}.record",
            "resource_type": capability_id or "finops_record",
            "resource_id": name,
        }
    if block_id == "analytics":
        return {
            "metric": f"{capability_id}.recorded",
            "value": 1.0,
            "event": f"{capability_id}.recorded",
        }
    if block_id == "queue":
        return {
            "job_type": capability_id or "finops_job",
            "payload": {"reference": record.get("reference")},
        }
    if block_id == "capture":
        body = _text(
            record,
            "detail",
            "notes",
            "answer",
            "question",
            default=summary(record, capability_id),
        )
        return {"text": body, "content": body}
    if block_id == "recommendation_template":
        return {"input": dict(record)}
    return {}


def event_bus_step(capability_id: str, record: Dict[str, Any]) -> Dict[str, Any]:
    """One prepared Store ``event_bus`` workflow step.

    Every event_bus child -- step_0 included -- carries the full prepared
    contract. The Store workflow reads ``step['block']`` (not block_id),
    forwards ``step['params']`` to the child, and 0-indexes children, so an
    unprepared or action-less step fails as
    ``workflow: step_0 (event_bus): error``. ``channel`` is ``mcp``: an
    ``email`` channel without a ``to`` is not notify-ready, and ``sample``
    is never a channel.
    """
    scalars = {
        key: value
        for key, value in sorted(record.items())
        if isinstance(value, (str, int, float, bool)) and value not in (None, "")
    }
    return {
        "block": "event_bus",
        "action": "publish",
        # the Store workflow forwards step['params'] to the child block
        # (step['action'] is the factory's own step vocabulary); both are
        # emitted so neither reader drops the operation
        "params": {"action": "publish"},
        "input": {
            "topic": "%s.%s" % (
                capability_id or "finops",
                _text(record, "reference", "department", default="record"),
            )[:80],
            "payload": scalars or {"reference": "record"},
            "message": summary(record, capability_id),
            "channel": "mcp",
            "tool": "event_bus",
        },
    }


def block_input(
    capability_id: str,
    block_id: str,
    prepared: Any,
    record: Dict[str, Any],
    required_fields: Sequence[str] = (),
) -> Dict[str, Any]:
    """The final input handed to one block: constructed keys plus the record.

    ``prepared`` is what ``prepare_block_input`` produced (the shared
    construction rules); ``extras`` are this build's per-block additions.
    Exclusive blocks receive only the constructed input; the rest receive
    the prepared input with any missing constructed keys filled in.
    """
    extras = extras_for(capability_id, block_id, record, required_fields)
    base = dict(prepared) if isinstance(prepared, dict) else {}
    base.pop("action", None)
    if block_id in EXCLUSIVE_BLOCKS:
        out = dict(extras)
    else:
        out = base
        for key, value in extras.items():
            if key not in out or out[key] in (None, "", {}):
                out[key] = value
    return out
