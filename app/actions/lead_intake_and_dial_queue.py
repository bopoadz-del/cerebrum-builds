"""Lead intake & dial queue.

Written by the factory WRITER role (codewhale exec)

A brokerage lead file becomes rows this platform can pace: the phone number
is normalised to E.164 or the row is held and says why, the language picks
the calling window, the retry ceiling and backoff are attached, and the row
enters the dial list as ``queued``. A number that cannot be dialled is never
improved by guessing a country — it is held until the operator sets one.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app import config, domain, formulas
from app.models import MODELS

CAPABILITY_ID = "lead_intake_and_dial_queue"

#: The keyword action each bound block is dispatched with:
#: ``dispatch.execute(block_id, action=BLOCK_DEFAULT_ACTIONS.get(block_id))``.
#: The action travels as a keyword and never inside the payload -- the block
#: registry reads its operation from the keyword, and a payload "action" key
#: is just another record field. These are the actions ``app/dispatch.py``
#: registers for each block, so a declared default is a call this platform
#: can actually make.
BLOCK_DEFAULT_ACTIONS = {
    'capture': 'extract',
    'queue': 'enqueue',
    'formula_executor': 'run',
    'validation': 'record',
}

REQUIRED_FIELDS = ["lead_name", "phone", "project_tag"]

#: The same contract app/models.py declares, stated where the handler
#: enforces it: the route refuses from the model, the handler refuses
#: from here, and the two cannot drift (tests/test_capability_round_trip.py).
constraints = {
    "lead_name": {"required": True, "max_length": 160},
    "phone": {"required": True, "max_length": 40},
    "project_tag": {"required": True, "max_length": 80},
    "language": {"allowed_values": ['en', 'ar']},
    "campaign": {"max_length": 80},
    "source_file": {"max_length": 200},
    "lead_email": {"max_length": 200},
    "property_type": {"allowed_values": ['apartment', 'villa', 'townhouse', 'plot', 'office', 'retail', 'other']},
    "budget": {"min": 0},
    "area": {"max_length": 120},
    "timeline": {"allowed_values": ['immediate', 'three_months', 'six_months', 'twelve_months', 'browsing', 'unknown']},
    "priority": {"min": 1, "max": 5},
    "phone_e164": {"max_length": 20},
    "dialable": {},
    "dialable_reason": {"max_length": 200},
    "attempt_count": {"min": 0, "max": 20},
    "max_attempts": {"min": 1, "max": 10},
    "retry_backoff_minutes": {"min": 0},
    "daily_call_cap": {"min": 0},
    "concurrency": {"min": 1},
    "queue_state": {"allowed_values": ['queued', 'dialing', 'dialed', 'held', 'exhausted', 'closed']},
    "best_call_window": {"max_length": 40},
    "window_state": {"allowed_values": ['open', 'closed']},
    "dial_scheduled_at": {"max_length": 40},
    "next_attempt_at": {"max_length": 40},
    "last_call_sid": {"max_length": 64},
    "notes": {"max_length": 2000},
    "reference": {"required": True},
    "status": {"allowed_values": ['open', 'in_progress', 'closed'], "required": True},
}


def _require(body: Dict[str, Any]) -> Dict[str, Any] | None:
    for name in REQUIRED_FIELDS:
        if body.get(name) in (None, ""):
            return {"ok": False, "error": f"Missing required field: {name}"}
    if body.get("reference") in (None, ""):
        return {"ok": False, "error": "Missing required field: reference"}
    if body.get("status") in (None, ""):
        return {"ok": False, "error": "Missing required field: status"}
    return None


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Queue one lead: normalise, attach policy, decide whether it can be dialled."""
    body = dict(payload or {})
    refusal = _require(body)
    if refusal:
        return refusal
    for name, rules in constraints.items():
        values = rules.get("allowed_values") or ()
        value = body.get(name)
        if value is None or value == "":
            continue
        if values and value not in values:
            return {
                "ok": False,
                "error": f"{name} must be one of: " + ", ".join(str(v) for v in values),
            }
    intake = domain.lead_intake(body)
    notes = body.get("notes")
    held = not intake["dialable"]
    queue_reason = intake["dialable_reason"] or "number is dialable"
    record = {
        "language": intake["language"],
        "phone_e164": intake["phone_e164"],
        "dialable": intake["dialable"],
        "dialable_reason": queue_reason,
        "best_call_window": intake["best_call_window"],
        "window_state": intake["window_state"],
        "attempt_count": intake["attempt_count"],
        "max_attempts": intake["max_attempts"],
        "retry_backoff_minutes": intake["retry_backoff_minutes"],
        "daily_call_cap": intake["daily_call_cap"],
        "concurrency": intake["concurrency"],
        "priority": intake["priority"],
        "queue_state": intake["queue_state"],
        "dial_scheduled_at": intake["dial_scheduled_at"],
        "next_attempt_at": intake["next_attempt_at"],
    }
    if notes:
        record["notes"] = str(notes)[:2000]
    remaining = formulas.calls_remaining(
        daily_cap=record["daily_call_cap"], attempted_today=domain.as_int(body.get("attempt_count"), 0)
    )
    return {
        "ok": True,
        "capability": CAPABILITY_ID,
        "decision": "held" if held else "queued",
        "queue_state": record["queue_state"],
        "reason": queue_reason,
        "calls_remaining": remaining["result"],
        "attempts_remaining": max(0, config.MAX_ATTEMPTS - domain.as_int(record["attempt_count"], 0)),
        "record": record,
        "authority": intake["authority"],
    }
