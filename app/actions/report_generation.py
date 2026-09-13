"""report_generation — REUSE document_engine + recommendation_template."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import document_engine_input, recommendation_template_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.persist import ok_envelope

# READS: caller.input, file.local.read, file.input_document, config.runtime
# WRITES: caller.output, file.local.write, file.temp
# NEVER: demanding file paths from the caller; reserved-keyword fields

BLOCK_IDS = ["document_engine", "recommendation_template"]


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Parse a constructed finance PDF and rank recommendations; persist."""
    parsed = execute(
        "document_engine",
        document_engine_input(payload),
        action=BLOCK_DEFAULT_ACTIONS.get("document_engine"),
    )
    ranked = execute(
        "recommendation_template",
        recommendation_template_input(payload),
        action=BLOCK_DEFAULT_ACTIONS.get("recommendation_template"),
    )
    record = {
        **payload,
        "report": {
            "report_type": payload.get("report_type") or "pnl",
            "period": payload.get("period") or "month",
            "documents_parsed": (parsed.get("result") or {}).get("documents_parsed")
            if isinstance(parsed, dict)
            else 0,
        },
    }
    return ok_envelope(
        "report_generation",
        record,
        {"document_engine": parsed, "recommendation_template": ranked},
    )
