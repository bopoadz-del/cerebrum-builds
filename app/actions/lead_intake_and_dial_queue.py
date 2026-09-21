"""Handler for capability lead_intake_and_dial_queue.

Written by the factory WRITER role (codewhale exec)

Authored by the coder CLI (codewhale exec) — the factory WRITER coding
agent — against the vendored blocks, in this repository.

Turns a brokerage lead file into a durable dial list. The lead file is
parsed by the vendored ``capture`` block (scripted extraction offline, local
OCR when tesseract is present -- never a cloud call), the dial job is handed
to the vendored ``queue`` block, and the pacing numbers are computed rather
than guessed: calls remaining today, the retry backoff for busy / no-answer
(max three spaced attempts) and the per-language best call window, all
through app.formulas with the vendored ``formula_executor`` carrying the
library call. ``validation`` screens the resulting dial pipeline before it
is queued.

Scope
-----
READS  this capability's own columns from the caller's record; the lead file
       text supplied with the record; app.formulas (pacing arithmetic);
       app.dispatch (the local offline block runtime); app.block_inputs
       (block input construction); app.store (the
       ``lead_intake_and_dial_queue`` table, through the route's
       tenant-scoped save).
WRITES app.dispatch.execute() results; exactly one row in
       ``lead_intake_and_dial_queue`` via the ROUTE's ``store.save(entity,
       record, tenant_id)`` -- this handler has no tenant and never persists
       directly.
NEVER  unguarded network egress; ``vendor/**`` (sealed, read-only); another
       capability's table; ``tests/**``; dialing anything.

Blocks are action-dispatched: ``action=`` is a keyword on
``app.dispatch.execute`` (via app.block_run), never a key inside the domain
payload. Block-contract keys are constructed by
``app.block_inputs.prepare_block_input`` from this record -- the caller is
never asked for them.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app import formulas
from app.block_run import block_runner
from app.security import InputRefused, clean_text

CAPABILITY_ID = "lead_intake_and_dial_queue"
ENTITY = "lead_intake_and_dial_queue"
BLOCK_IDS = ['capture', 'queue', 'formula_executor', 'validation']
#: Each block's declared action (block.json / the Store map). Blocks are
#: action-dispatched; calling one with no action answers "Unknown action".
BLOCK_DEFAULT_ACTIONS = {
    'capture': 'extract',
    'queue': 'enqueue',
    'formula_executor': 'execute',
    'validation': 'validate_pipeline',
}
#: This capability's own domain columns.
CAPABILITY_FIELDS = [
    'reference', 'status', 'lead_name', 'phone', 'language', 'project_tag',
    'source_file', 'call_window', 'daily_call_cap', 'concurrency',
    'attempt_count', 'retry_backoff_minutes', 'queue_status', 'notes',
]

EDGE_CONSTRAINTS = {
    'reference': {'required': True},
    'status': {'allowed_values': ['open', 'in_progress', 'closed'], 'required': True},
    'lead_name': {'required': True},
    'phone': {'required': True},
    'language': {'allowed_values': ['en', 'ar'], 'required': True},
    'project_tag': {'required': True},
}


def _text(data: Dict[str, Any], name: str, limit: int = 2000) -> str:
    return clean_text(data.get(name), field=name, limit=limit)


def _int(data: Dict[str, Any], name: str, default: int) -> int:
    raw = data.get(name)
    if raw in (None, ""):
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _lead_lines(data: Dict[str, Any]) -> List[str]:
    """Rows of the lead file, as text. Never invented when the file is absent."""
    blob = _text(data, "source_file", 40)
    for key in ("lead_file_text", "file_text", "document_text", "text"):
        raw = data.get(key)
        if isinstance(raw, str) and raw.strip():
            return [line for line in raw.splitlines() if line.strip()]
    name = _text(data, "lead_name", 200)
    phone = _text(data, "phone", 40)
    if name and phone:
        return [f"name,phone,language,project_tag",
                f"{name},{phone},{_text(data, 'language', 8) or 'en'},"
                f"{_text(data, 'project_tag', 120)}",
                f"#source: {blob or 'record'}"]
    return []


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(payload or {}) if isinstance(payload, dict) else {}
    runner = block_runner(entity=ENTITY, roster=BLOCK_IDS, default_actions=BLOCK_DEFAULT_ACTIONS)

    try:
        reference = _text(data, "reference", 120) or "lead"
        lead_name = _text(data, "lead_name", 200)
        phone = _text(data, "phone", 40)
        language = _text(data, "language", 8).lower() or "en"
        project_tag = _text(data, "project_tag", 120)
        source_file = _text(data, "source_file", 200)
        if not phone:
            return {
                "ok": False,
                "capability": CAPABILITY_ID,
                "error": "phone is required: a lead with no number cannot be dialed",
            }
        if language not in ("en", "ar"):
            return {
                "ok": False,
                "capability": CAPABILITY_ID,
                "error": "language must be one of: en, ar",
            }
        rows = _lead_lines(data)
    except InputRefused as exc:
        return {"ok": False, "capability": CAPABILITY_ID, "error": str(exc)}

    captured = runner(
        "capture",
        {"text": "\n".join(rows) or f"{lead_name} {phone}", "lead_name": lead_name,
         "source_file": source_file},
        action="extract",
    )

    # Pacing is arithmetic, not a constant: app.formulas owns the rule and the
    # vendored formula_executor is asked for the same numbers so the library
    # call is exercised on one library, not two.
    cap = _int(data, "daily_call_cap", formulas.DEFAULT_DAILY_CALL_CAP)
    attempts_today = max(0, _int(data, "attempt_count", 0))
    pacing = formulas.dial_pacing(
        daily_call_cap=cap,
        attempts_today=attempts_today,
        attempt_count=attempts_today,
        language=language,
    )
    library = runner(
        "formula_executor",
        {
            "formula_key": "calls_per_day_remaining",
            "input_values": {
                "daily_call_cap": pacing["daily_call_cap"],
                "attempts_today": pacing["attempts_today"],
                "attempt_count": pacing["attempt_count"],
            },
        },
        action="execute",
    )

    queue_status = "queued" if pacing["calls_remaining"] > 0 else "exhausted"
    pipeline = {
        "pipeline_id": f"dial-{reference}".replace(" ", "_"),
        "steps": [
            {
                "id": "step_0",
                "type": "queue",
                "block": "queue",
                "input": {
                    "queue_name": "dial-list",
                    "job": "dial_lead",
                    "payload": {
                        "reference": reference,
                        "phone": phone,
                        "language": language,
                        "project_tag": project_tag,
                    },
                },
            }
        ],
    }
    validated = runner("validation", {"pipeline": pipeline}, action="validate_pipeline")

    queued = runner(
        "queue",
        {
            "queue_name": "dial-list",
            "job": "dial_lead",
            "payload": {
                "reference": reference,
                "phone": phone,
                "language": language,
                "project_tag": project_tag,
                "call_window": pacing["call_window"],
                "attempt": pacing["attempt_count"] + 1,
            },
            "delay": pacing["retry_backoff_minutes"] * 60,
        },
        action="enqueue",
    )

    refusal = runner.refusal()
    if refusal is not None:
        return {"ok": False, "capability": CAPABILITY_ID, **refusal}

    return {
        "ok": True,
        "capability": CAPABILITY_ID,
        "lead": {
            "lead_name": lead_name,
            "phone": phone,
            "language": language,
            "project_tag": project_tag,
            "source_file": source_file,
        },
        "capture": {
            "raw_text_lines": len(rows),
            "entities": captured.get("entities") if isinstance(captured, dict) else None,
            "ocr_engine": captured.get("ocr_engine") if isinstance(captured, dict) else None,
        },
        "pacing": pacing,
        "formula_library_keys": sorted(
            (library.get("formula_library") or {}).keys()
        )[:5] if isinstance(library, dict) else [],
        "queue_status": queue_status,
        "queue_job_id": queued.get("job_id") if isinstance(queued, dict) else None,
        "pipeline_validation": validated.get("status") if isinstance(validated, dict) else None,
        "blocks": runner.report(),
    }
