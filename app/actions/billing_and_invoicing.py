"""billing_and_invoicing — REUSE validation + notification + queue. Domain totals."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import prepare_block_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.domain import allowed_next_status, envelope_status, invoice_totals
from app.persist import ok_envelope

# READS: caller.input, config.runtime, env.process, queue.jobs
# WRITES: caller.output, notification.outbound, queue.jobs
# NEVER: (none)

BLOCK_IDS = ["validation", "notification", "queue"]
CAPABILITY_ID = "billing_and_invoicing"
KINDS = ("consult", "procedure", "pharmacy")


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Stamp invoice kind base + tax; persist totals that are not silent zeros."""
    status = envelope_status(payload)
    invoice_kind = str(payload.get("invoice_kind") or "consult")
    if invoice_kind not in KINDS:
        invoice_kind = "consult"
    line_label = str(payload.get("line_label") or payload.get("reference") or "sample")
    money = invoice_totals(invoice_kind)
    collection_state = {
        "open": "issued",
        "in_progress": "partial",
        "closed": "settled",
    }[status]
    record = {
        **payload,
        "status": status,
        "invoice_kind": invoice_kind,
        "line_label": line_label,
        "subtotal": money["subtotal"],
        "tax": money["tax"],
        "total": money["total"],
        "tax_rate": money["tax_rate"],
        "collection_state": collection_state,
        "capability": CAPABILITY_ID,
        "channel": "mcp",
    }
    blocks: Dict[str, Any] = {}
    for block_id in BLOCK_IDS:
        blocks[block_id] = execute(
            block_id,
            prepare_block_input(block_id, record),
            action=BLOCK_DEFAULT_ACTIONS.get(block_id),
        )
    record["invoice"] = {
        "invoice_kind": invoice_kind,
        "line_label": line_label,
        "subtotal": money["subtotal"],
        "tax": money["tax"],
        "total": money["total"],
        "tax_rate": money["tax_rate"],
        "collection_state": collection_state,
        "allowed_next_status": list(allowed_next_status(status)),
        "queued": True,
        "notified": True,
    }
    return ok_envelope(CAPABILITY_ID, record, blocks)
