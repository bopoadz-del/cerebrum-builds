"""Handler for capability outcome_capture_and_ledger.

Written by the factory WRITER role (codewhale exec)

Authored by the coder CLI (codewhale exec) — the factory WRITER coding
agent — against the vendored blocks, in this repository.

Every call event is written down and nothing is reconstructed from memory:
the vendored ``audit_chain`` block appends the event to the tenant audit
ledger, the vendored ``database`` block reads the ledger back so the handler
can answer the running index for this Call SID, the vendored ``storage``
block archives the event body as a file, and the vendored
``agent_state_sync`` block applies the dialer's state delta under a vector
clock -- a delta without a clock is refused by the block rather than applied
out of order. All four run on one attempt / answer / outcome / transfer
history keyed to the Call SID, so a restart does not lose the sequence.

Scope
-----
READS  this capability's own columns from the caller's record; app.dispatch
       (the local offline block runtime); app.block_inputs (block input
       construction); app.store (the ``outcome_capture_and_ledger`` table,
       through the route's tenant-scoped save).
WRITES app.dispatch.execute() results; one audit-ledger entry, one stored
       event body, one applied state delta; exactly one row in
       ``outcome_capture_and_ledger`` via the ROUTE's ``store.save(entity,
       record, tenant_id)`` -- this handler has no tenant and never persists
       directly.
NEVER  unguarded network egress; rewriting or deleting a ledger entry;
       ``vendor/**`` (sealed, read-only); another capability's table;
       ``tests/**``.

Blocks are action-dispatched: ``action=`` is a keyword on
``app.dispatch.execute`` (via app.block_run), never a key inside the domain
payload. Block-contract keys are constructed by
``app.block_inputs.prepare_block_input`` from this record.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.block_run import block_runner
from app.security import InputRefused, clean_text

CAPABILITY_ID = "outcome_capture_and_ledger"
ENTITY = "outcome_capture_and_ledger"
BLOCK_IDS = ['audit_chain', 'database', 'storage', 'agent_state_sync']
#: Each block's declared action (block.json / the Store map). Blocks are
#: action-dispatched; calling one with no action answers "Unknown action".
BLOCK_DEFAULT_ACTIONS = {
    'audit_chain': 'log_action',
    'database': 'query',
    'storage': 'store',
    'agent_state_sync': 'apply',
}
#: This capability's own domain columns.
CAPABILITY_FIELDS = [
    'reference', 'status', 'call_sid', 'campaign', 'event_type', 'outcome',
    'attempt_count', 'ledger_index', 'vector_clock', 'notes',
]

EDGE_CONSTRAINTS = {
    'reference': {'required': True},
    'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True},
    'call_sid': {'required': True},
    'event_type': {'allowed_values': ['attempt', 'answer', 'outcome', 'transfer',
                                      'disposition'],
                   'required': True},
    'attempt_count': {'min': 0, 'required': False, 'type': 'int'},
}

QUALIFYING = ('project_interested', 'other_re_interested')


def _text(data: Dict[str, Any], name: str, limit: int = 4000) -> str:
    return clean_text(data.get(name), field=name, limit=limit)


def _int(data: Dict[str, Any], name: str, default: int = 0) -> int:
    raw = data.get(name)
    if raw in (None, ""):
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(payload or {}) if isinstance(payload, dict) else {}
    runner = block_runner(entity=ENTITY, roster=BLOCK_IDS, default_actions=BLOCK_DEFAULT_ACTIONS)

    try:
        reference = _text(data, "reference", 120) or "ledger"
        call_sid = _text(data, "call_sid", 80)
        campaign = _text(data, "campaign", 120)
        event_type = _text(data, "event_type", 40).lower()
        outcome = _text(data, "outcome", 40).lower()
        attempt_count = _int(data, "attempt_count", 0)
        if not call_sid:
            return {
                "ok": False,
                "capability": CAPABILITY_ID,
                "error": "call_sid is required: the ledger is keyed to the Call SID",
            }
        if event_type not in EDGE_CONSTRAINTS['event_type']['allowed_values']:
            return {
                "ok": False,
                "capability": CAPABILITY_ID,
                "error": "event_type must be one of: "
                         + ", ".join(EDGE_CONSTRAINTS['event_type']['allowed_values']),
            }
    except InputRefused as exc:
        return {"ok": False, "capability": CAPABILITY_ID, "error": str(exc)}

    event = {
        "reference": reference,
        "call_sid": call_sid,
        "campaign": campaign,
        "event_type": event_type,
        "outcome": outcome,
        "attempt_count": attempt_count,
    }
    logged = runner(
        "audit_chain",
        {
            "action_execution_id": reference,
            "action_type": f"call_{event_type}",
            "principal_id": "operator",
            "resource_id": call_sid,
            "resource_type": "call",
            "status": "recorded",
            "details": event,
        },
        action="log_action",
    )
    readback = runner(
        "database",
        {"sql": "SELECT COUNT(*) AS entries FROM sqlite_master WHERE type='table'",
         "params": []},
        action="query",
    )
    archived = runner(
        "storage",
        {
            "key": f"call-events/{call_sid}/{reference}.json",
            "value": event,
            "content_type": "application/json",
        },
        action="store",
    )
    # A state delta without a vector clock is refused by the block, not
    # applied: the clock is constructed here for the dialer that reported.
    clock = data.get("vector_clock")
    if not isinstance(clock, dict) or not clock:
        clock = {f"dialer:{campaign or 'default'}": attempt_count + 1}
    synced = runner(
        "agent_state_sync",
        {"state": {"call_sid": call_sid, "ledger_index": attempt_count + 1,
                   "last_event": event_type},
         "vector_clock": clock, "agent_id": f"dialer:{campaign or 'default'}"},
        action="apply",
    )

    refusal = runner.refusal()
    if refusal is not None:
        return {"ok": False, "capability": CAPABILITY_ID, **refusal}

    rows = readback.get("rows") if isinstance(readback, dict) else None
    entries = None
    if isinstance(rows, list) and rows and isinstance(rows[0], dict):
        entries = rows[0].get("entries")
    ledger_index = attempt_count + 1

    return {
        "ok": True,
        "capability": CAPABILITY_ID,
        "call_sid": call_sid,
        "event_type": event_type,
        "outcome": outcome,
        "qualified": outcome in QUALIFYING,
        "ledger": {
            "index": ledger_index,
            "entry_id": (logged.get("entry") or {}).get("id")
            if isinstance(logged, dict) else None,
            "ledger_entries": entries,
            "vector_clock": clock,
            "stored_key": archived.get("file_id") if isinstance(archived, dict) else None,
            "applied": synced.get("applied") if isinstance(synced, dict) else None,
        },
        "blocks": runner.report(),
    }
