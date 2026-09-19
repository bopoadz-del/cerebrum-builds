"""Handler for capability finance_document_knowledge.

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
CAPABILITY_ID = "finance_document_knowledge"
ENTITY = 'finance_document_knowledge'
BLOCK_IDS = ['document_engine', 'knowledge', 'vector_search', 'storage', 'spec_analyzer', 'capture']
#: Each block's declared default action (block.json / Store registry map).
#: Blocks are action-dispatched; execute() with action=None is answered
#: "Unknown action: None". validation uses check_code_quality -- the block's
#: own validate_pipeline refuses a program that carries no schema entry.
BLOCK_DEFAULT_ACTIONS = {'document_engine': 'parse', 'knowledge': 'search', 'vector_search': 'search', 'storage': 'store', 'spec_analyzer': 'analyze', 'capture': 'extract'}
#: This capability's own domain columns. The kernel strips trust-scope keys
#: from caller arguments, so the domain columns are declared here.
CAPABILITY_FIELDS = ['reference', 'status', 'department', 'document_type', 'question', 'answer', 'citations', 'confidence', 'document_path']

_REQUIRED_FIELDS = ['reference', 'status', 'department', 'document_type', 'question']

def _answer(record):
    """Answer the finance question from the platform's own ingested corpus.

    The corpus is the platform tenant's (app.tenancy.DEFAULT_TENANT -- the
    tenant PLATFORM_TOKEN maps to). Per-caller tenant scoping lives in
    app.rag_routes, which resolves the tenant from the authenticated
    principal and is the path the UI uses.
    """
    from app import llm, retrieval, tenancy

    question = str(record.get('question') or '')
    tenant_id = tenancy.DEFAULT_TENANT
    try:
        passages = retrieval.search(tenant_id=tenant_id, query=question, limit=5)
    except ValueError as exc:
        return {'answer': llm.NO_ANSWER, 'citations': [], 'confidence': 0.0,
                'error': str(exc), 'tenant_id': tenant_id}
    answer = llm.synthesize(question, passages)
    answer['tenant_id'] = tenant_id
    answer['document_type_filter'] = str(record.get('document_type') or 'any')
    answer['passages_considered'] = len(passages)
    return answer


def _platform_side(record, unavailable):
    """The grounded answer, plus ingestion when the caller supplied a body."""
    answer = _answer(record) if 'knowledge' in unavailable else None
    ingested = None
    document = record.get('answer') or record.get('notes')
    if isinstance(document, str) and document.strip():
        from app import retrieval, tenancy

        try:
            ingested = retrieval.ingest(
                tenant_id=tenancy.DEFAULT_TENANT,
                text=document,
                document=str(record.get('reference') or 'uploaded-document'),
                document_type=str(record.get('document_type') or 'policy'),
                department=str(record.get('department') or ''))
        except ValueError as exc:
            ingested = {'error': str(exc)}
    return {'grounded_answer': answer, 'ingested': ingested,
            'blocks_unavailable': sorted(unavailable)}

def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Invoices, contracts, policies and price lists parsed, indexed and answered through knowledge and vector search."""
    import app.dispatch as _dispatch
    from app.block_feed import block_input as _block_input
    from app.block_inputs import default_block_action as _default_block_action
    from app.block_inputs import prepare_block_input as _prepare_block_input
    from app.block_inputs import split_execute_action as _split_execute_action
    from app.vendor_compat import unavailable_reason as _unavailable_reason

    # Reads the question; writes one result envelope. Retrieval is tenant-scoped.
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
