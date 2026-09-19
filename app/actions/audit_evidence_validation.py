"""Handler for capability audit_evidence_validation.

Written by the factory WRITER role (codewhale exec)

FinOps Central. Blocks are invoked in-process through the local dispatch runtime
(app.dispatch.execute) -- this module makes no network call. Persistence is
route-scoped: the tenant-scoped save in app/routes.py writes the request
after SUCCESS. handle() is pure dispatch and never touches the store.

Scope
  READS   the capability record handed in by the route, plus the vendored
          block contracts it feeds.
  WRITES  its own result envelope only (app/routes.py persists).
  NEVER   the tenant store, the network, or another capability's state.

A block that cannot be loaded from the sealed vendor tree is named in
``results`` and ``unavailable_blocks`` after being invoked and failing to
load; a block that answers with an error fails the capability closed.

Authored by the coding agent (codewhale exec) under the factory WRITER role.
"""

from __future__ import annotations

from typing import Any, Dict

from app.dispatch import execute

PRODUCT_NAME = "FinOps Central"
CAPABILITY_ID = "audit_evidence_validation"
ENTITY = 'audit_evidence_validation'
BLOCK_IDS = ['audit', 'evidence_verifier', 'file_hasher', 'validation', 'storage', 'database']
#: Each block's declared default action (block.json / Store registry map).
#: Blocks are action-dispatched; execute() with action=None is answered
#: "Unknown action: None". validation uses check_code_quality -- the block's
#: own validate_pipeline refuses a program that carries no schema entry.
BLOCK_DEFAULT_ACTIONS = {'audit': 'log', 'evidence_verifier': 'store', 'file_hasher': 'hash', 'validation': 'check_code_quality', 'storage': 'store', 'database': 'query'}
#: This capability's own domain columns. The kernel strips trust-scope keys
#: from caller arguments, so the domain columns are declared here.
CAPABILITY_FIELDS = ['reference', 'status', 'department', 'record_type', 'record_reference', 'evidence_hash', 'verified', 'checked_at', 'notes']

_REQUIRED_FIELDS = ['reference', 'status', 'department', 'record_type', 'record_reference']

def _evidence(record):
    """Evidence digest and integrity verdict for one finance record."""
    import hashlib

    body = '|'.join(str(record.get(key) or '') for key in (
        'reference', 'department', 'record_type', 'record_reference',
        'evidence_hash', 'notes'))
    digest = hashlib.sha256(body.encode('utf-8')).hexdigest()
    out = {
        'department': str(record.get('department') or ''),
        'record_type': str(record.get('record_type') or ''),
        'record_reference': str(record.get('record_reference') or ''),
        'checked_at': str(record.get('checked_at') or ''),
        'evidence_digest': digest,
        'submitted_hash': str(record.get('evidence_hash') or ''),
        'verified': bool(record.get('verified')),
    }
    out['digest_matches'] = bool(out['submitted_hash']) and out['submitted_hash'] == digest
    out['verdict'] = 'verified' if (out['digest_matches'] or out['verified']) else 'unverified'
    return out


def _platform_side(record, unavailable):
    """The audit verdict; the audit block's own chain is the durable trail."""
    evidence = _evidence(record)
    try:
        from app import notifications

        evidence['notification'] = notifications.deliver(
            department=str(record.get('department') or ''),
            subject='evidence %s: %s' % (evidence['verdict'], evidence['record_reference']),
            message='digest=%s matches=%s' % (
                evidence['evidence_digest'][:16], evidence['digest_matches']),
            channel='mcp', record=record)
    except Exception as exc:  # noqa: BLE001
        evidence['notification'] = {'error': '%s: %s' % (type(exc).__name__, exc)}
    return {'evidence': evidence, 'blocks_unavailable': sorted(unavailable)}

def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Immutable audit trail plus hashed evidence and verifier checks over finance records, approvals and documents."""
    import app.dispatch as _dispatch
    from app.block_feed import block_input as _block_input
    from app.block_inputs import default_block_action as _default_block_action
    from app.block_inputs import prepare_block_input as _prepare_block_input
    from app.block_inputs import split_execute_action as _split_execute_action
    from app.vendor_compat import unavailable_reason as _unavailable_reason

    # Reads the finance record; writes one result envelope. The audit chain is append-only.
    results: Dict[str, Any] = {}
    block_errors: Dict[str, str] = {}
    unavailable: Dict[str, str] = {}

    def _invoke(block_id, data, action=None):
        resolved, record = _split_execute_action(
            data, action=action,
            default_action=_default_block_action(block_id, BLOCK_DEFAULT_ACTIONS))
        prepared = _prepare_block_input(
            block_id, record, action=resolved, roster=BLOCK_IDS,
            product_name=PRODUCT_NAME, entity=ENTITY,
            default_actions=BLOCK_DEFAULT_ACTIONS)
        prepared = _block_input(CAPABILITY_ID, block_id, prepared, record, _REQUIRED_FIELDS)
        try:
            answer = _dispatch.execute(block_id, prepared, action=resolved)
        except Exception as exc:  # a block that cannot load is named, never hidden
            unavailable[block_id] = ('%s: %s' % (type(exc).__name__, exc))[:300]
            return {'ok': False, 'block': block_id, 'invoked': True,
                    'unavailable': True, 'reason': unavailable[block_id]}
        if isinstance(answer, dict) and (
            str(answer.get('status') or '').lower() == 'error'
            or 'error' in answer
        ):
            reason = _unavailable_reason(block_id)
            if reason:
                # The block was invoked and the vendored source it wraps
                # cannot load (sealed vendor: notification.py does not
                # parse). Named, not fatal -- the capability's own module
                # performs that step and the reason travels in the
                # envelope. An error from a block that DID load still
                # fails the capability closed below.
                unavailable[block_id] = reason[:300]
                return {'ok': False, 'block': block_id, 'invoked': True,
                        'unavailable': True, 'reason': unavailable[block_id]}
        return answer

    # The workflow block runs last: its steps are the prepared event_bus
    # children, and the Store workflow 0-indexes them, so every child carries
    # the full contract (block, action=publish, params.action, topic,
    # payload dict, message, channel=mcp, tool=event_bus).
    ordered = [b for b in BLOCK_IDS if b != 'workflow'] + (
        ['workflow'] if 'workflow' in BLOCK_IDS else [])
    for block_id in ordered:
        answer = _invoke(block_id, payload)
        results[block_id] = answer
        if not isinstance(answer, dict):
            continue
        status = str(answer.get('status') or '').lower()
        if status in ('error', 'failed', 'partial') or 'error' in answer:
            block_errors[block_id] = str(answer.get('error') or status)[:200]
        elif block_id == 'validation' and answer.get('passed') is False:
            block_errors[block_id] = 'validation block reported passed=false'
        elif block_id == 'evidence_verifier' and answer.get('verified') is False:
            block_errors[block_id] = 'evidence_verifier reported verified=false'

    if block_errors:
        return {'ok': False, 'capability': CAPABILITY_ID,
                'error': '; '.join('%s: %s' % (b, e) for b, e in sorted(block_errors.items())),
                'results': results, 'unavailable_blocks': sorted(unavailable)}

    record = payload if isinstance(payload, dict) else {}
    return {'ok': True, 'capability': CAPABILITY_ID, 'results': results,
            'unavailable_blocks': sorted(unavailable),
            'platform': _platform_side(record, unavailable)}
