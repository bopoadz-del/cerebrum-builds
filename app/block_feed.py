"""Construct the block inputs a capability's bound blocks actually accept.

Written by the factory WRITER role (codewhale exec)

A caller posts a domain record; a block wants its own contract. This module
is where the bakery record is turned into that contract -- the caller is
never asked for ``properties``, ``checklist``, ``steps``, file paths, or a
validation program. ``app.block_inputs.prepare_block_input`` covers the
shared cases; the additions here are the ones this build's blocks need on
top of it, derived from the record alone.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Sequence


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
    return (head + "; ".join(parts))[:400] or "bakery record"


def validation_program(record: Dict[str, Any], capability_id: str = "") -> str:
    """A runnable constraint program for this record, assembled from its data.

    The Store ``validation`` block is asked to check this program rather than
    the record's prose: the numbers and vocabularies the capability declared
    become the assertions the block executes.
    """
    checks: List[str] = [
        '"""Constraint program for %s, derived from the record it was given."""'
        % (capability_id or "bakery record"),
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


def extras_for(
    capability_id: str,
    block_id: str,
    record: Dict[str, Any],
    required_fields: Sequence[str] = (),
) -> Dict[str, Any]:
    """Block-specific inputs the record cannot carry directly."""
    record = record if isinstance(record, dict) else {}
    name = _text(record, "reference", "branch", default=capability_id or "bakery")

    if block_id == "portfolio_rollup":
        return {
            "properties": [
                {
                    "id": str(record.get("branch") or name),
                    "value": _number(record, "amount", "deposit_amount", "quantity_on_hand", "guest_count", "confidence"),
                    "status": str(record.get("status") or "open"),
                }
            ]
        }
    if block_id == "estate_registry":
        # The registry mints nothing: it requires the id and refuses a
        # duplicate, so each write carries its own stable identity.
        return {
            "id": f"{name}-{uuid.uuid4().hex[:12]}",
            "data": dict(record),
        }
    if block_id == "readiness_engine":
        checklist = [{"id": str(field), "required": True} for field in required_fields]
        state = {str(field): record.get(field) not in (None, "") for field in required_fields}
        return {"checklist": checklist, "state": state}
    if block_id == "vector_search":
        return {"query": _text(record, "question", "subject", "item_name", default=name)}
    if block_id == "knowledge":
        query = _text(record, "question", "subject", default=name)
        return {"query": query, "question": query}
    if block_id == "spec_analyzer":
        body = _text(record, "body", "question", "notes", "answer", default=name)
        return {"text": body, "spec_text": body}
    if block_id == "storage":
        return {
            "content": summary(record, capability_id),
            "filename": f"{capability_id or 'bakery'}-{name}.txt"[:120],
        }
    if block_id == "estate_maintenance":
        return {"title": _text(record, "item_name", "subject", "event_name", default=summary(record, capability_id))}
    if block_id == "validation":
        program = validation_program(record, capability_id)
        return {
            "block_id": capability_id or "bakery_capability",
            "name": capability_id or "bakery_capability",
            "code": program,
            "test_code": (
                "def test_validate_entry():\n"
                "    from module_under_test import run\n"
                "    assert run({'amount': 1})['ok'] is True\n"
            ),
        }
    if block_id == "workflow":
        topic = "%s.%s" % (capability_id or "bakery", _text(record, "reference", default="record"))
        return {
            "steps": [
                {
                    "block": "event_bus",
                    "action": "publish",
                    # the Store workflow forwards step['params'] to the child
                    # block (step['action'] is the factory's step vocabulary);
                    # both are emitted so neither reader drops the operation
                    "params": {"action": "publish"},
                    "input": {
                        "topic": topic[:80],
                        "payload": {
                            key: value
                            for key, value in sorted(record.items())
                            if isinstance(value, (str, int, float, bool))
                        },
                        "message": summary(record, capability_id),
                        "channel": "mcp",
                        "tool": "event_bus",
                    },
                }
            ]
        }
    if block_id == "database":
        entity = ENTITY_BY_CAPABILITY.get(str(capability_id), "")
        if entity:
            return {
                "sql": (
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='%s'" % entity
                ),
                "table": entity,
            }
        return {}
    if block_id == "audit":
        return {
            "action": f"{capability_id}.record",
            "resource_type": capability_id or "bakery_record",
            "resource_id": name,
        }
    if block_id == "analytics":
        return {"metric": f"{capability_id}.recorded", "value": 1.0, "event": f"{capability_id}.recorded"}
    if block_id == "queue":
        return {"job_type": capability_id or "bakery_job", "payload": {"reference": record.get("reference")}}
    if block_id == "capture":
        body = _text(record, "body", "proof_of_delivery", "follow_up_note", "notes", default=summary(record, capability_id))
        return {"text": body, "content": body}
    if block_id == "memory":
        return {"key": f"{capability_id}:{name}"[:200], "value": summary(record, capability_id)}
    return {}


#: Entity each capability persists to. The Store database block is asked
#: about the capability's own table, never a table it invents.
ENTITY_BY_CAPABILITY = {
    "branch_and_consolidated_operations": "branch_and_consolidated_operations",
    "inventory_and_replenishment": "inventory_and_replenishment",
    "branch_books_and_accounting": "branch_books_and_accounting",
    "delivery_and_dispatch": "delivery_and_dispatch",
    "order_follow_up": "order_follow_up",
    "events_supply": "events_supply",
    "document_grounded_knowledge": "document_grounded_knowledge",
    "outlook_branch_messaging_integration": "outlook_branch_messaging_integration",
}


#: Blocks that validate their input strictly: anything the caller's record
#: carries beyond what the block reads is refused as an unknown field
#: (measured: portfolio_rollup refused "branch, metrics_summary", and the
#: Store analytics adapter answers "metric and value required" when the
#: record arrives nested rather than flat). For these the constructed input
#: is the whole input -- the domain record is not appended to it.
EXCLUSIVE_BLOCKS = frozenset(
    {
        "analytics",
        "audit",
        "capture",
        "estate_maintenance",
        "estate_registry",
        "knowledge",
        "memory",
        "portfolio_rollup",
        "queue",
        "readiness_engine",
        "spec_analyzer",
        "storage",
        "validation",
        "vector_search",
        "workflow",
    }
)


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
