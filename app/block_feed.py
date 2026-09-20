"""Construct the block inputs a capability's bound blocks actually accept.

Written by the factory WRITER role (codewhale exec)

A caller posts a complaint, a team record or a dashboard snapshot; a block
wants its own contract. This module is where the facility record is turned
into that contract -- the caller is never asked for ``properties``,
``steps``, ``sql``, file paths, or a validation program.
``app.block_inputs.prepare_block_input`` covers the shared cases; the
additions here are the ones this build's blocks need on top of it, derived
from the record alone.

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
    "complaints_management": "complaints_management",
    "auto_assignment": "auto_assignment",
    "workforce_management": "workforce_management",
    "management_dashboards": "management_dashboards",
    "reporting": "reporting",
    "role_based_access": "role_based_access",
    "erp_integration": "erp_integration",
    "booking_system_integration": "booking_system_integration",
}

#: Blocks that validate their input strictly: anything the caller's record
#: carries beyond what the block reads is refused as an unknown field
#: (measured on the Store roster: portfolio_rollup refused foreign keys,
#: recommendation_template refused "recommendations", and the analytics
#: adapter answers "metric and value required" when the record arrives
#: nested rather than flat). For these the constructed input IS the input.
EXCLUSIVE_BLOCKS = frozenset(
    {
        "analytics",
        "audit",
        "capture",
        "dashboard",
        "evidence_verifier",
        "file_hasher",
        "knowledge",
        "notification",
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
    return (head + "; ".join(parts))[:400] or "facility record"


def rollup_properties(record: Dict[str, Any], capability_id: str = "") -> List[Dict[str, Any]]:
    """The per-school rows ``portfolio_rollup`` sums.

    The Dubai estate carries ten schools; a per-site record names one, a
    portfolio record covers the estate. Each property carries the numeric
    value the rollup aggregates, so the block never receives a non-numeric
    value and never has to be told what the number means.
    """
    school = _text(record, "school", "busiest_school", default="portfolio")
    open_count = _number(record, "complaints_open", "open_jobs", "candidate_count")
    closed_count = _number(record, "complaints_closed", "closed_total")
    in_progress = _number(record, "complaints_in_progress", "jobs_in_progress")
    rows = [
        {
            "id": f"{school}:open",
            "value": open_count,
            "status": "open",
        },
        {
            "id": f"{school}:in_progress",
            "value": in_progress,
            "status": "in_progress",
        },
        {
            "id": f"{school}:closed",
            "value": closed_count,
            "status": "closed",
        },
    ]
    if str(record.get("scope") or "").lower() == "portfolio":
        # a portfolio row is the estate rollup: the same three measures
        # under the estate id, so the block sums both views.
        rows.append(
            {
                "id": "estate:portfolio",
                "value": open_count + in_progress + closed_count,
                "status": str(record.get("status") or "open"),
            }
        )
    if capability_id:
        rows.append(
            {
                "id": f"{capability_id}:recorded",
                "value": 1.0,
                "status": str(record.get("status") or "open"),
            }
        )
    return rows


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
        % (capability_id or "facility record"),
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
        path = os.path.join(root, f"{capability_id or 'facility'}-{digest}.txt")
        if not os.path.isfile(path):
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(body + "\n")
        return path
    except OSError:
        fd, path = tempfile.mkstemp(prefix="facility-evidence-", suffix=".txt")
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
    name = _text(record, "reference", "school", default=capability_id or "facility")

    if block_id == "portfolio_rollup":
        return {"properties": rollup_properties(record, capability_id)}
    if block_id == "dashboard":
        return {
            "widgets": [
                {
                    "id": "complaints",
                    "title": "Complaints open / in progress / closed",
                    "type": "metric",
                    "data_source": capability_id or "facility",
                },
                {
                    "id": "sla",
                    "title": "SLA compliance (%%)",
                    "type": "metric",
                    "data_source": capability_id or "facility",
                },
            ],
            "theme": "management",
            "layout": {"columns": 2, "widgets": ["complaints", "sla"]},
        }
    if block_id == "vector_search":
        return {"query": _text(record, "description", "detail", "notes", default=name)}
    if block_id == "knowledge":
        query = _text(record, "description", "detail", default=name)
        return {"query": query, "question": query}
    if block_id == "spec_analyzer":
        body = _text(record, "description", "detail", "notes", default=name)
        return {"text": body, "spec_text": body}
    if block_id == "storage":
        return {
            "content": summary(record, capability_id),
            "filename": f"{capability_id or 'facility'}-{name}.txt"[:120],
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
        # The Store validation block runs a five-stage pipeline over an
        # ITEM, so it is handed this record as the item -- the fields the
        # capability declared (reference, status, and the rest) become the
        # schema the pipeline checks, not a fabricated entry.
        item = {
            "id": str(record.get("reference") or name),
            "type": str(capability_id or "facility_record"),
        }
        item.update(
            {
                key: value
                for key, value in sorted(record.items())
                if isinstance(value, (str, int, float, bool))
                and value not in (None, "")
            }
        )
        return {
            "item": item,
            "block_id": capability_id or "facility_capability",
            "name": capability_id or "facility_capability",
        }
    if block_id == "workflow":
        return {"steps": [event_bus_step(capability_id, record)], "result": dict(record)}
    if block_id == "formula_executor":
        return {
            "expression": _text(record, "formula", default="open + in_progress + closed"),
            "variables": {
                "open": _number(record, "complaints_open", "complaints_total", "headcount"),
                "in_progress": _number(record, "complaints_in_progress", "jobs_in_progress", "open_jobs"),
                "closed": _number(record, "complaints_closed", "closed_total"),
                "sla_breaches": _number(record, "sla_breaches"),
                "target_hours": _number(record, "sla_hours"),
            },
            "formula": _text(record, "formula", default="open + in_progress + closed"),
        }
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
            "action_name": f"{capability_id}.record",
            "resource_type": capability_id or "facility_record",
            "resource_id": name,
            "category": capability_id or "facility",
            "details": {"reference": record.get("reference"),
                        "status": record.get("status")},
            "event": f"{capability_id}.record",
        }
    if block_id == "analytics":
        value = _number(
            record, "complaints_open", "complaints_total", "headcount", "match_score"
        )
        return {
            "metric": f"{capability_id}.recorded",
            "name": f"{capability_id}.recorded",
            "value": value or 1.0,
            "event": f"{capability_id}.recorded",
            "tags": {"school": _text(record, "school", default="estate")},
        }
    if block_id == "queue":
        return {
            "job_type": capability_id or "facility_job",
            "payload": {"reference": record.get("reference"),
                        "school": record.get("school")},
        }
    # The ``team`` block mints its own team and the platform preconditions
    # create it at boot; prepare_block_input carries that minted id. No
    # domain-looking team_id is invented here.
    if block_id == "capture":
        body = _text(
            record,
            "description",
            "detail",
            "notes",
            default=summary(record, capability_id),
        )
        return {"text": body, "content": body}
    if block_id == "notification":
        # The Store notification block's MCP channel dispatches to another
        # vendored block by name; event_bus is the one every capability in
        # this product carries, so the notification is published there
        # rather than to a block this product does not vendor.
        return {
            "channel": "mcp",
            "message": summary(record, capability_id),
            "subject": f"{capability_id}: {name}"[:200],
            "block": "event_bus",
            "tool": "event_bus",
            "topic": f"{capability_id}.{name}"[:80],
            "payload": {"reference": record.get("reference"),
                        "school": record.get("school")},
        }
    if block_id == "recommendation_template":
        # The block refuses any key beyond its own declared input.
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
    topic = "%s.%s" % (
        capability_id or "facility",
        _text(record, "reference", "integration", "booking_reference",
              default="record"),
    )
    return {
        "block": "event_bus",
        "action": "publish",
        # the Store workflow forwards step['params'] to the child block
        # (step['action'] is the factory's own step vocabulary); both are
        # emitted so neither reader drops the operation
        "params": {"action": "publish"},
        "input": {
            "topic": topic[:80],
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
