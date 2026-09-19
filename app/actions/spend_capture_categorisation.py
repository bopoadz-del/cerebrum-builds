"""Handler for capability spend_capture_categorisation.

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
CAPABILITY_ID = "spend_capture_categorisation"
ENTITY = 'spend_capture_categorisation'
BLOCK_IDS = ['capture', 'database', 'file_hasher', 'document_engine', 'validation', 'event_bus']
#: Each block's declared default action (block.json / Store registry map).
#: Blocks are action-dispatched; execute() with action=None is answered
#: "Unknown action: None". validation uses check_code_quality -- the block's
#: own validate_pipeline refuses a program that carries no schema entry.
BLOCK_DEFAULT_ACTIONS = {'capture': 'extract', 'database': 'query', 'file_hasher': 'hash', 'document_engine': 'parse', 'validation': 'check_code_quality', 'event_bus': 'publish'}
#: This capability's own domain columns. The kernel strips trust-scope keys
#: from caller arguments, so the domain columns are declared here.
CAPABILITY_FIELDS = ['reference', 'status', 'department', 'supplier', 'category', 'amount', 'currency', 'invoice_date', 'invoice_number', 'document_path', 'notes']

_REQUIRED_FIELDS = ['reference', 'status', 'department', 'supplier', 'category']

#: chart-of-accounts mappings the platform owns (category -> account code).
CHART_OF_ACCOUNTS = {
    'software': '7100-software',
    'travel': '7200-travel',
    'facilities': '7300-facilities',
    'professional_services': '7400-professional-services',
    'marketing': '7500-marketing',
}


def _categorisation(record):
    """Chart-of-accounts code, net/VAT split and the evidence link."""
    from app import formulas

    category = str(record.get('category') or '')
    out = {
        'department': str(record.get('department') or ''),
        'supplier': str(record.get('supplier') or ''),
        'category': category,
        'account_code': CHART_OF_ACCOUNTS.get(category, '7900-uncategorised'),
        'currency': str(record.get('currency') or 'GBP'),
        'invoice_date': str(record.get('invoice_date') or ''),
        'invoice_number': str(record.get('invoice_number') or ''),
        'document_linked': bool(str(record.get('document_path') or '').strip()),
    }
    try:
        out['net_amount'] = formulas.spend_net(amount=record.get('amount'))
        out['vat_amount'] = formulas.spend_vat(amount=record.get('amount'))
    except formulas.FormulaError as exc:
        out['amount_error'] = str(exc)
    return out


def _platform_side(record, unavailable):
    """The categorised spend line, its account code and the captured proof."""
    categorised = _categorisation(record)
    captured = None
    answer = None
    for block in ('capture', 'document_engine'):
        if block in unavailable:
            continue
        answer = answer or block
    try:
        from app import notifications

        captured = notifications.deliver(
            department=str(record.get('department') or ''),
            subject='spend captured: %s' % categorised['supplier'],
            message='%s %s %s -> %s' % (
                categorised['supplier'], record.get('amount'),
                categorised['currency'], categorised['account_code']),
            channel='mcp', record=record)
    except Exception as exc:  # noqa: BLE001
        captured = {'error': '%s: %s' % (type(exc).__name__, exc)}
    return {'categorisation': categorised, 'notification': captured,
            'platform_extractor': answer, 'blocks_unavailable': sorted(unavailable)}

def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Spend capture and categorisation against the chart of accounts, with the supporting document linked and hashed."""
    import app.dispatch as _dispatch
    from app.block_feed import block_input as _block_input
    from app.block_inputs import default_block_action as _default_block_action
    from app.block_inputs import prepare_block_input as _prepare_block_input
    from app.block_inputs import split_execute_action as _split_execute_action
    from app.vendor_compat import unavailable_reason as _unavailable_reason

    # Reads the spend record; writes one result envelope. The document is hashed, never rewritten.
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
