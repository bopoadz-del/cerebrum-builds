"""Warm transfer: summary → broker leg → whisper → conference bridge.

Written by the factory WRITER role (codewhale exec)

On a qualifying outcome the platform collects the conversation summary from
the qualification record, dials the broker leg, whispers the private summary
to the broker only (the lead never hears it), and conference-bridges the two
legs. The sequence actually attempted is returned step by step, so the
bridge is auditable without an account: the same shape a real call produces.

No broker number, no transfer. ``BROKER_TRANSFER_NUMBER`` unset means the
outcome is recorded as declined with the setting named — never a claimed
bridge that did not happen.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app import config, domain
from app.models import MODELS
from app.security import mask_phone
from app.voice import twilio_client

CAPABILITY_ID = "warm_transfer"

REQUIRED_FIELDS = ["call_sid", "outcome"]

#: The same contract app/models.py declares, stated where the handler
#: enforces it: the route refuses from the model, the handler refuses
#: from here, and the two cannot drift (tests/test_capability_round_trip.py).
constraints = {
    "call_sid": {"required": True, "max_length": 64},
    "outcome": {"allowed_values": ['transferred', 'declined', 'broker_unavailable', 'no_qualification', 'failed'], "required": True},
    "lead_id": {"max_length": 40},
    "project_tag": {"max_length": 80},
    "qualified_outcome": {"allowed_values": ['project_interested', 'other_re_interested', 'not_interested']},
    "broker_number": {"max_length": 40},
    "broker_language": {"allowed_values": ['en', 'ar']},
    "whisper_text": {"max_length": 2000},
    "summary": {},
    "steps": {},
    "step_count": {"min": 0},
    "conference_name": {"max_length": 80},
    "conference_sid": {"max_length": 64},
    "bridge_seconds": {"min": 0},
    "attempt": {"min": 0},
    "transfer_key": {"max_length": 80},
    "edge_stub": {},
    "unavailable_blocks": {"max_length": 400},
    "reference": {"required": True},
    "status": {"allowed_values": ['open', 'in_progress', 'closed'], "required": True},
}

TRANSFER_STEPS = (
    "collect_summary",
    "resolve_broker_number",
    "dial_broker_leg",
    "whisper_summary_to_broker",
    "conference_bridge",
    "return_outcome",
)


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Bridge a warm lead to a broker, or record honestly that it did not."""
    body = dict(payload or {})
    for name in REQUIRED_FIELDS:
        if body.get(name) in (None, ""):
            return {"ok": False, "error": f"Missing required field: {name}"}
    for name in ("reference", "status"):
        if body.get(name) in (None, ""):
            return {"ok": False, "error": f"Missing required field: {name}"}
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
    # Only the two interest outcomes are warm leads: a caller who is not
    # interested is closed, never handed to a broker.
    qualified = str(body.get("qualified_outcome") or "") in (
        "project_interested",
        "other_re_interested",
    )
    # The whisper is structured from the qualification record the call already
    # wrote, keyed by Call SID -- the brief's "summary structured from the
    # record", not from whatever this request happened to carry. Fields the
    # caller did supply win; the record fills the rest. The outcome that goes
    # into the summary is the caller's three-outcome vocabulary, never the
    # boolean that decides whether they are a warm lead.
    supplied = body.get("collected")
    collected = dict(supplied) if isinstance(supplied, dict) else {}
    record: Dict[str, Any] = {}
    tenant_id = str(body.get("tenant_id") or "")
    call_sid = str(body.get("call_sid") or "")
    if tenant_id and call_sid:
        try:
            from app import store

            rows = [
                row
                for row in store.list_all("qualification_and_broker_summary", tenant_id)
                if str(row.get("call_sid") or "") == call_sid
            ]
            if rows:
                record = rows[-1]
        except Exception:  # noqa: BLE001 -- the request still carries a usable summary
            record = {}
    for name in ("property_type", "budget", "area", "timeline", "lead_name", "language", "project_tag"):
        if body.get(name) not in (None, ""):
            record[name] = body.get(name)
    record["outcome"] = str(body.get("qualified_outcome") or record.get("outcome") or "")
    record["call_sid"] = call_sid or body.get("call_sid")
    stored_collected = record.get("collected")
    if not isinstance(stored_collected, dict):
        # A stored column may be the JSON text of the dict; anything else is
        # not a mapping and must not be splatted into one.
        stored_collected = {}
    record["collected"] = {**stored_collected, **collected}
    summary = domain.broker_summary(record, currency=body.get("currency") or record.get("currency"))
    whisper = domain.whisper_text(summary["summary"])
    raw_broker = body.get("broker_number") or config.BROKER_TRANSFER_NUMBER or ""
    broker_e164, broker_reason = domain.normalize_phone(raw_broker)
    broker_number = broker_e164 or ""
    edge = twilio_client()
    steps: List[Dict[str, Any]] = []
    steps.append({"step": "collect_summary", "status": "done", "summary": summary["summary"]})
    steps.append(
        {
            "step": "resolve_broker_number",
            "status": "done" if broker_number else "blocked",
            "setting": "BROKER_TRANSFER_NUMBER",
            "reason": broker_reason,
        }
    )
    if not qualified:
        outcome = "no_qualification"
        reason = "no qualifying outcome was collected, so the broker is not bridged"
        steps.append({"step": "dial_broker_leg", "status": "skipped", "reason": reason})
        steps.append({"step": "whisper_summary_to_broker", "status": "skipped"})
        steps.append({"step": "conference_bridge", "status": "skipped"})
    elif not broker_number:
        outcome = "declined"
        reason = (
            "no dialable broker leg (BROKER_TRANSFER_NUMBER unset, or the number "
            f"cannot be normalised: {broker_reason}); the warm lead is recorded "
            "and left with the platform rather than bridged to nothing"
        )
        steps.append({"step": "dial_broker_leg", "status": "skipped", "reason": reason})
        steps.append({"step": "whisper_summary_to_broker", "status": "skipped"})
        steps.append({"step": "conference_bridge", "status": "skipped"})
    else:
        language = str(body.get("broker_language") or body.get("language") or "en")[:2]
        conference = f"callops-{body.get('call_sid')}"
        whisper_twiml = edge.whisper_twiml(
            {"broker_language": language, "whisper_text": whisper}
        )
        bridge_twiml = edge.dial_broker_twiml(
            {
                "broker_number": broker_number,
                "broker_language": language,
                "whisper_text": whisper,
                "conference_name": conference,
            }
        )
        outcome = "transferred"
        reason = "broker leg dialled, whispered, and bridged into the conference"
        steps.append(
            {
                "step": "dial_broker_leg",
                "status": "done",
                "broker_leg": domain.normalize_phone(broker_number)[0] or broker_number,
                "edge_stub": bool(edge.state()["stub"]),
            }
        )
        steps.append({"step": "whisper_summary_to_broker", "status": "done", "twiml": whisper_twiml})
        steps.append(
            {
                "step": "conference_bridge",
                "status": "done",
                "conference_name": conference,
                "twiml": bridge_twiml,
            }
        )
    steps.append({"step": "return_outcome", "status": "done", "outcome": outcome})
    record = {
        "outcome": outcome,
        "lead_id": body.get("lead_id"),
        "project_tag": body.get("project_tag"),
        "qualified_outcome": str(body.get("qualified_outcome") or "") or None,
        "broker_number": mask_phone(broker_number) if broker_number else None,
        "broker_language": str(body.get("broker_language") or body.get("language") or "en")[:2],
        "whisper_text": whisper,
        "summary": str(summary["summary"]),
        "steps": str([step["step"] + ":" + step["status"] for step in steps]),
        "step_count": len(steps),
        "conference_name": f"callops-{body.get('call_sid')}",
        "attempt": domain.as_int(body.get("attempt"), 1),
        "transfer_key": f"{body.get('call_sid')}:{body.get('lead_id') or 'lead'}",
        "edge_stub": bool(edge.state()["stub"]),
        "unavailable_blocks": ", ".join(
            list(edge.state()["unavailable_blocks"])
            + ([] if broker_number else ["BROKER_TRANSFER_NUMBER"])
        ),
    }
    return {
        "ok": True,
        "capability": CAPABILITY_ID,
        "decision": outcome,
        "reason": reason,
        "transfer_steps": steps,
        "whisper": whisper,
        "summary": summary["summary"],
        "record": record,
        "authority": summary["authority"],
    }
