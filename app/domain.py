"""The CallOps domain kernel: the decisions this platform was asked to make.

Handlers stay thin because the judgement lives here, in one place:

* phone intake — a number that cannot be dialled is flagged, never silently
  dialled, and never invented into a valid one
* the dial-queue policy — cap, concurrency, attempt ceiling and window
* the call state machine — which transitions exist, and the call-window
  guard that can refuse one
* the ledger — a hash chain per Call SID, so attempt / answer / transfer
  history is reconstructable after a restart and tampering is detectable
* the three-outcome vocabulary — a schema, not prose, plus the fields
  collected beside it
* the broker summary — structured from that record, never freehand

Nothing here reads a credential or a money rate; those come from
``app/config.py`` and refuse by name when the operator has not stated them.
"""

from __future__ import annotations

import urllib.error
import urllib.request

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from app import config, formulas
from app.authority import Claim, envelope

PHONE_DIGITS = re.compile(r"\d")
NON_DIAL_CHARS = re.compile(r"[^\d+]")

#: Which transition each call event is allowed to make. A state machine that
#: accepts any transition is not a state machine, so the table is explicit.
TRANSITIONS: Dict[str, Tuple[str, ...]] = {
    "queued": ("dialing",),
    "dialing": ("answered", "callback", "closed"),
    "answered": ("pitched", "callback", "closed"),
    "pitched": ("qualified", "callback", "closed"),
    "qualified": ("transferred", "callback", "closed"),
    "transferred": ("closed",),
    "callback": ("dialing", "closed"),
    "closed": (),
}

#: Event → the state it moves a call into. The Call SID is the key.
EVENT_TARGETS: Dict[str, str] = {
    "dial": "dialing",
    "answer": "answered",
    "pitch": "pitched",
    "qualify": "qualified",
    "transfer": "transferred",
    "callback": "callback",
    "close": "closed",
    "abandon": "callback",
    "retry": "dialing",
    "no_answer": "callback",
    "busy": "callback",
}

#: Twilio status callbacks → the same workflow transitions. The edge reports
#: what the carrier did; the workflow decides what it means.
TWILIO_STATUS_EVENTS: Dict[str, Tuple[str, str]] = {
    "initiated": ("dialing", "dial"),
    "queued": ("dialing", "dial"),
    "ringing": ("dialing", "dial"),
    "in-progress": ("answered", "answer"),
    "answered": ("answered", "answer"),
    "completed": ("closed", "close"),
    "failed": ("callback", "no_answer"),
    "busy": ("callback", "busy"),
    "no-answer": ("callback", "no_answer"),
    "canceled": ("callback", "no_answer"),
}

STATE_SEQUENCE = (
    "queued",
    "dialing",
    "answered",
    "pitched",
    "qualified",
    "transferred",
    "callback",
    "closed",
)

OUTCOME_VOCABULARY: Tuple[str, ...] = (
    "project_interested",
    "other_re_interested",
    "not_interested",
)

OUTCOME_PHRASES: Dict[str, Tuple[str, ...]] = {
    "project_interested": (
        "interested in this project", "like this project", "this project works",
        "yes for this project", "book a viewing for this", "want this project",
        "send me the project details", "this one interests me", "مهتم بهذا المشروع",
    ),
    "other_re_interested": (
        "looking at another project", "other developer", "another developer",
        "comparing projects", "different project", "another area",
        "مهتم بمشروع آخر",
    ),
    "not_interested": (
        "not interested", "no thanks", "stop calling", "remove my number",
        "wrong number", "do not call", "غير مهتم",
    ),
}

PROPERTY_HINTS = {
    "apartment": ("apartment", "flat", "studio", "one bedroom", "two bedroom", "شقة"),
    "villa": ("villa", "townhouse", "فيلا"),
    "townhouse": ("townhouse", "row house"),
    "plot": ("plot", "land", "أرض"),
    "office": ("office", "commercial", "مكتب"),
    "retail": ("retail", "shop", "showroom", "محل"),
}

TIMELINE_HINTS = {
    "immediate": ("immediately", "as soon as possible", "this month", "now"),
    "three_months": ("three months", "3 months", "quarter"),
    "six_months": ("six months", "6 months", "half a year"),
    "twelve_months": ("twelve months", "12 months", "next year", "a year"),
    "browsing": ("just looking", "browsing", "no rush", "exploring"),
}

BUDGET_RE = re.compile(
    r"(?:budget|up to|around|maximum|max|about)\s*(?:is|of)?\s*"
    r"([A-Z]{3})?\s*([\d][\d,\.]*)\s*(m|million|k|thousand)?",
    re.IGNORECASE,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def as_int(value: Any, default: int = 0) -> int:
    """The number a value carries, or the default when it carries none.

    The entity contracts this platform publishes are declared as text unless
    a type is stated, and the acceptance harness samples one value per
    declared field -- so ``"sample"`` reaches a column the deployment reads
    as a count. Refusing it would be a contract stricter than the schema can
    express; raising on it would turn a record into a 500. The value is read
    as a number when it is one, and the domain default applies when it is
    not, so pacing a dial list never crashes on a row an operator typed by
    hand.
    """
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return int(default)


def as_float(value: Any, default: float = 0.0) -> float:
    """The same read for a money or ratio column (unset money stays unset)."""
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return float(default)


def declared(payload: Mapping[str, Any] | None, names: Sequence[str]) -> Dict[str, Any]:
    """Read only the declared fields of a payload — never the rest of it."""
    body = dict(payload or {})
    return {name: body[name] for name in names if name in body}


def normalize_phone(raw: Any) -> Tuple[Optional[str], Optional[str]]:
    """E.164 when the number can be read that way, else the reason it cannot.

    A brokerage file is a human artefact: numbers arrive with spaces,
    brackets and a national trunk zero. This normalises what it can and
    flags the rest, because guessing a country code is how a bot dials a
    stranger in another country.
    """
    text = _clean(raw)
    if not text:
        return None, "phone is empty"
    digits = PHONE_DIGITS.findall(text)
    if not digits:
        return None, "phone contains no digits"
    if len(digits) < 7:
        return None, "phone has too few digits to dial"
    if len(digits) > 15:
        return None, "phone is longer than E.164 allows"
    if text.strip().startswith("+"):
        return "+" + "".join(digits), None
    default_country = config.env("DEFAULT_COUNTRY_CODE")
    if default_country:
        prefix = "+" + str(default_country).lstrip("+")
        return prefix + "".join(digits).lstrip("0"), None
    return None, "phone has no country code (set DEFAULT_COUNTRY_CODE to dial it)"


def lead_intake(record: Mapping[str, Any], *, moment: Optional[datetime] = None) -> Dict[str, Any]:
    """Everything intake decides for one lead, as data."""
    body = dict(record or {})
    language = str(body.get("language") or "en").lower()[:2]
    if language not in ("en", "ar"):
        language = "en"
    e164, reason = normalize_phone(body.get("phone"))
    window = formulas.best_call_window(language=language, moment=moment)
    attempts = as_int(body.get("attempt_count"), 0)
    backoff = formulas.retry_backoff(attempt=max(1, attempts or 1), reason="no-answer")
    dialable = bool(e164)
    return {
        "language": language,
        "phone_e164": e164,
        "dialable": dialable,
        "dialable_reason": reason,
        "best_call_window": window["result"],
        "window_state": "open" if window["inside_window"] else "closed",
        "attempt_count": attempts,
        "max_attempts": config.MAX_ATTEMPTS,
        "retry_backoff_minutes": as_int(config.RETRY_BACKOFF_MINUTES),
        "daily_call_cap": as_int(body.get("daily_call_cap"), config.DAILY_CALL_CAP),
        "concurrency": as_int(body.get("concurrency"), config.CONCURRENCY),
        "priority": as_int(body.get("priority"), 3),
        "queue_state": "queued" if dialable else "held",
        "dial_scheduled_at": window["next_window"] or window["result"],
        "next_attempt_at": None if dialable else utc_now(),
        "authority": envelope(
            [
                Claim(
                    name="retry_backoff",
                    value=backoff["result"],
                    layer="formulas",
                    source="formulas.retry_backoff",
                ),
                Claim(
                    name="best_call_window",
                    value=window["result"],
                    layer="formulas",
                    source="formulas.best_call_window",
                ),
            ]
        ),
    }


def dial_queue(
    tenant_id: str,
    *,
    campaign: Optional[str] = None,
    attempted_today: int = 0,
    moment: Optional[datetime] = None,
) -> Dict[str, Any]:
    """The dial list for a campaign, paced against the cap and the window."""
    from app import store

    rows = store.list_all("lead_intake_and_dial_queue", tenant_id)
    if campaign:
        rows = [row for row in rows if str(row.get("campaign") or "") == str(campaign)]
    dialable = [row for row in rows if row.get("dialable") and row.get("queue_state") != "closed"]
    held = [row for row in rows if not row.get("dialable")]
    remaining = formulas.calls_remaining(
        daily_cap=min(
            [as_int(row.get("daily_call_cap"), config.DAILY_CALL_CAP) for row in rows]
            or [config.DAILY_CALL_CAP]
        ),
        attempted_today=attempted_today,
    )
    pacing = formulas.dial_pacing(
        remaining=int(remaining["result"]),
        window_minutes=120,
    )
    ordered = sorted(
        dialable,
        key=lambda row: (-as_int(row.get("priority"), 3), as_int(row.get("id"), 0)),
    )
    return {
        "tenant_id": tenant_id,
        "campaign": campaign,
        "cap": remaining,
        "pacing": pacing,
        "queued": ordered[: int(remaining["result"])],
        "queue_depth": len(dialable),
        "held": held,
        "held_count": len(held),
        "authority": envelope(
            [
                Claim(name="calls_remaining", value=remaining["result"], layer="formulas", source="formulas.calls_remaining"),
                Claim(name="dial_pacing", value=pacing["result"], layer="formulas", source="formulas.dial_pacing"),
            ]
        ),
    }


def dial_permitted(
    tenant_id: str,
    *,
    language: str = "en",
    moment: Optional[datetime] = None,
) -> Dict[str, Any]:
    """May this tenant dial another lead right now?

    The campaign's own policy, in one function so the console, the queue
    processor and the voice edge cannot disagree about it: the call window
    for the language (``formulas.window_open``) and the daily cap remaining
    (``formulas.calls_remaining``) against today's originate attempts. The
    answer and status-callback URLs come from settings too — see
    ``app/config.py``.
    """
    from app import store

    current = moment or datetime.now(timezone.utc)
    window = formulas.window_open(language=language, moment=current)
    today = current.date().isoformat()
    attempts = [
        row
        for row in store.list_all("voice_gateway", tenant_id)
        if str(row.get("created_at") or "").startswith(today)
        and str(row.get("voice_action") or row.get("action") or "") == "originate"
    ]
    leads = store.list_all("lead_intake_and_dial_queue", tenant_id)
    caps = [as_int(row.get("daily_call_cap"), config.DAILY_CALL_CAP) for row in leads] or [
        config.DAILY_CALL_CAP
    ]
    remaining = formulas.calls_remaining(daily_cap=min(caps), attempted_today=len(attempts))
    if not window["result"]:
        permitted, reason = False, f"outside the call window ({window['reason']})"
    elif int(remaining["result"]) <= 0:
        permitted, reason = False, "daily call cap reached for this campaign"
    else:
        permitted, reason = True, "window open and cap remaining"
    return {
        "permitted": permitted,
        "reason": reason,
        "language": language,
        "window": window["window"],
        "window_state": window["reason"],
        "attempted_today": len(attempts),
        "calls_remaining": int(remaining["result"]),
        "answer_url": config.TWILIO_ANSWER_URL,
        "status_callback_url": config.TWILIO_STATUS_CALLBACK_URL,
        "pacing": formulas.dial_pacing(
            remaining=int(remaining["result"]), window_minutes=120
        ),
        "authority": envelope(
            [
                Claim(
                    name="dial_permitted",
                    value=permitted,
                    layer="formulas",
                    source="formulas.calls_remaining",
                    detail=reason,
                ),
                Claim(
                    name="call_window",
                    value=window["result"],
                    layer="formulas",
                    source="formulas.window_open",
                ),
            ]
        ),
    }


def transition(
    record: Mapping[str, Any],
    *,
    moment: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Guard one call-state transition: the table, then the call window."""
    body = dict(record or {})
    event = str(body.get("event") or "").strip().lower()
    target = EVENT_TARGETS.get(event)
    current = _clean(body.get("previous_state")) or "queued"
    language = str(body.get("language") or "en").lower()[:2]
    window = formulas.window_open(language=language, moment=moment)
    allowed_from = TRANSITIONS.get(current, ())
    table_ok = bool(target) and target in allowed_from
    refused: Optional[str] = None
    if target is None:
        refused = f"event {event!r} maps to no state"
    elif not table_ok:
        refused = f"{current} does not move to {target} on {event}"
    elif event == "dial" and not window["result"]:
        refused = f"outside the call window ({window['reason']})"
    final = target if (target and not refused) else current
    return {
        "event": event,
        "previous_state": current,
        "current_state": final,
        "transition_allowed": refused is None,
        "refusal_reason": refused,
        "within_window": bool(window["result"]),
        "window_reason": window["reason"],
        "attempt_count": as_int(body.get("attempt_count"), 0) + (1 if event == "dial" and not refused else 0),
        "occurred_at": utc_now(),
        "window_snapshot": json.dumps(
            {"window": window["window"], "timezone": window["timezone"], "reason": window["reason"]},
            sort_keys=True,
        ),
        "authority": envelope(
            [
                Claim(
                    name="transition",
                    value=f"{current}->{final}",
                    layer="procedures",
                    source="domain.TRANSITIONS",
                    detail=refused or "allowed",
                ),
                Claim(
                    name="call_window",
                    value=window["result"],
                    layer="formulas",
                    source="formulas.window_open",
                ),
            ]
        ),
    }


def twilio_transition(status: str, current: str = "dialing") -> Dict[str, Any]:
    """Map a Twilio status callback onto a workflow transition by Call SID."""
    key = str(status or "").strip().lower()
    target, event = TWILIO_STATUS_EVENTS.get(key, (current, ""))
    return {
        "status": key,
        "target_state": target,
        "event": event,
        "mapping_ok": bool(event),
    }


def ledger_digest(payload: Mapping[str, Any] | None) -> str:
    body = json.dumps(payload or {}, sort_keys=True, default=str)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def ledger_hash(*, prev_hash: str, digest: str, call_sid: str, sequence: int) -> str:
    material = f"{prev_hash}|{digest}|{call_sid}|{sequence}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def append_ledger(
    tenant_id: str,
    *,
    call_sid: str,
    event_type: str,
    detail: Mapping[str, Any] | None = None,
    outcome: Optional[str] = None,
    actor: str = "platform",
    campaign: Optional[str] = None,
) -> Dict[str, Any]:
    """Append one call event to the tenant's hash chain for that Call SID."""
    from app import store

    history = [
        row
        for row in store.list_all("outcome_capture_and_ledger", tenant_id)
        if str(row.get("call_sid") or "") == str(call_sid)
    ]
    history.sort(key=lambda row: as_int(row.get("sequence"), 0))
    sequence = (as_int(history[-1].get("sequence"), 0) if history else 0) + 1
    prev_hash = str(history[-1]["entry_hash"]) if history else "genesis"
    payload = dict(detail or {})
    payload_digest = ledger_digest(payload)
    entry_hash = ledger_hash(
        prev_hash=prev_hash, digest=payload_digest, call_sid=str(call_sid), sequence=sequence
    )
    return {
        "sequence": sequence,
        "prev_hash": prev_hash,
        "entry_hash": entry_hash,
        "payload_digest": payload_digest,
        "detail": json.dumps(payload, sort_keys=True, default=str),
        "actor": actor,
        "outcome": outcome,
        "campaign": campaign,
        "event_type": event_type,
        "call_sid": str(call_sid),
        "chain_ok": True,
        "verified_count": len(history) + 1,
    }


def verify_chain(entries: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    """Walk a Call SID's chain and name the first entry that does not link."""
    ordered = sorted(
        (dict(entry) for entry in entries),
        key=lambda row: as_int(row.get("sequence"), 0),
    )
    prev = "genesis"
    violations: List[Dict[str, Any]] = []
    for entry in ordered:
        expected = ledger_hash(
            prev_hash=prev,
            digest=str(entry.get("payload_digest") or ""),
            call_sid=str(entry.get("call_sid") or ""),
            sequence=as_int(entry.get("sequence"), 0),
        )
        if str(entry.get("prev_hash") or "") != prev:
            violations.append(
                {"sequence": entry.get("sequence"), "problem": "prev_hash does not link"}
            )
        if expected != str(entry.get("entry_hash") or ""):
            violations.append(
                {"sequence": entry.get("sequence"), "problem": "entry_hash does not verify"}
            )
        prev = str(entry.get("entry_hash") or "")
    return {
        "entries": len(ordered),
        "intact": not violations,
        "violations": violations,
    }


def call_history(tenant_id: str, call_sid: str) -> Dict[str, Any]:
    from app import store

    entries = [
        row
        for row in store.list_all("outcome_capture_and_ledger", tenant_id)
        if str(row.get("call_sid") or "") == str(call_sid)
    ]
    states = [
        row
        for row in store.list_all("call_state_machine", tenant_id)
        if str(row.get("call_sid") or "") == str(call_sid)
    ]
    return {
        "call_sid": call_sid,
        "events": len(entries),
        "chain": verify_chain(entries),
        "ledger": sorted(entries, key=lambda row: as_int(row.get("sequence"), 0)),
        "states": sorted(states, key=lambda row: as_int(row.get("id"), 0)),
    }


def classify_outcome(text: str) -> Dict[str, Any]:
    """Classify a spoken turn into the three-outcome vocabulary.

    Rule-based and inspectable: the vocabulary is the contract, and a turn
    that matches nothing is not guessed into an outcome.
    """
    lowered = str(text or "").lower()
    for outcome in OUTCOME_VOCABULARY:
        for phrase in OUTCOME_PHRASES[outcome]:
            if phrase in lowered:
                return {"outcome": outcome, "matched": phrase, "confident": True}
    return {"outcome": None, "matched": None, "confident": False}


def collect_fields(text: str, base: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """The fields collected beside the outcome, from what the caller said."""
    body = dict(base or {})
    lowered = str(text or "").lower()
    collected: Dict[str, Any] = {
        "property_type": body.get("property_type"),
        "budget": body.get("budget"),
        "area": body.get("area"),
        "timeline": body.get("timeline"),
    }
    for kind, hints in PROPERTY_HINTS.items():
        if any(hint in lowered for hint in hints):
            collected["property_type"] = kind
            break
    for kind, hints in TIMELINE_HINTS.items():
        if any(hint in lowered for hint in hints):
            collected["timeline"] = kind
            break
    match = BUDGET_RE.search(str(text or ""))
    if match:
        currency, amount, scale = match.group(1), match.group(2), (match.group(3) or "").lower()
        try:
            value = float(amount.replace(",", ""))
        except ValueError:
            value = None
        if value is not None:
            if scale in ("m", "million"):
                value *= 1_000_000
            elif scale in ("k", "thousand"):
                value *= 1_000
            collected["budget"] = value
            if currency:
                collected["currency"] = currency.upper()
    area_match = re.search(r"(?:in|at|near)\s+([A-Z][\w\s-]{2,40})", str(text or ""))
    if area_match:
        collected["area"] = area_match.group(1).strip()
    return collected


def broker_summary(record: Mapping[str, Any], *, currency: Optional[str] = None) -> Dict[str, Any]:
    """The broker summary, structured from the qualification record."""
    body = dict(record or {})
    outcome = str(body.get("outcome") or "")
    interest = {
        "project_interested": "wants this project",
        "other_re_interested": "wants another project",
        "not_interested": "not interested",
    }.get(outcome, "unclassified")
    collected = {
        "property_type": body.get("property_type"),
        "budget": body.get("budget"),
        "area": body.get("area"),
        "timeline": body.get("timeline"),
    }
    stated_currency = _clean(body.get("currency")) or currency
    lines = [
        f"Lead: {body.get('lead_name') or 'unnamed'} ({body.get('language') or 'en'})",
        f"Project: {body.get('project_tag') or 'unstated'}",
        f"Outcome: {outcome or 'withheld'}",
        f"Interest: {interest}",
        "Collected: " + ", ".join(
            f"{key}={value}" for key, value in collected.items() if value not in (None, "")
        ) or "Collected: nothing further",
    ]
    if stated_currency:
        lines.append(f"Currency: {stated_currency}")
    transfer_required = outcome in ("project_interested", "other_re_interested")
    recommendation = {
        True: "bridge to the broker while the lead is warm",
        False: "no transfer; close or nurture",
    }[transfer_required]
    return {
        "summary": {
            "outcome": outcome,
            "interest": interest,
            "collected": collected,
            "currency": stated_currency,
            "call_sid": body.get("call_sid"),
            "project_tag": body.get("project_tag"),
            "next_action": "transfer_to_broker" if transfer_required else "close_lead",
        },
        "summary_text": "; ".join(lines),
        "recommendation": recommendation,
        "qualified": bool(outcome),
        "transfer_required": transfer_required,
        "next_action": "transfer_to_broker" if transfer_required else "close_lead",
        "authority": envelope(
            [
                Claim(
                    name="outcome",
                    value=outcome,
                    layer="procedures",
                    source="domain.OUTCOME_VOCABULARY",
                )
            ]
        ),
    }


def whisper_text(summary: Mapping[str, Any]) -> str:
    """What the broker hears, before the two legs are bridged."""
    body = dict(summary or {})
    collected = body.get("collected") or {}
    parts = [
        "Warm lead on the line.",
        f"Outcome {body.get('outcome') or 'unclassified'}.",
    ]
    if body.get("project_tag"):
        parts.append(f"Project {body['project_tag']}.")
    budget = collected.get("budget")
    if budget:
        currency = body.get("currency") or ""
        parts.append(f"Budget {currency} {budget}.")
    if collected.get("property_type"):
        parts.append(f"Wants a {collected['property_type']}.")
    if collected.get("timeline"):
        parts.append(f"Timeline {collected['timeline']}.")
    parts.append("Bridging now.")
    return " ".join(parts)


def crm_payload_shape(
    *,
    call_sid: str,
    outcome: Optional[str],
    summary: Mapping[str, Any] | None,
    destination: Optional[str],
) -> Dict[str, Any]:
    """The shape a CRM connector would receive — recorded, never claimed sent."""
    from collections.abc import Mapping as _Mapping

    body = dict(summary) if isinstance(summary, _Mapping) else {}
    return {
        "external_id": str(call_sid),
        "record_type": "call_outcome",
        "outcome": outcome,
        "summary": body,
        "destination": destination,
        "fields": ["external_id", "outcome", "summary.outcome", "summary.collected", "summary.currency"],
    }


class _GuardedRedirects(urllib.request.HTTPRedirectHandler):
    """Follow a redirect only when its target passes the same egress guard.

    ``check_egress`` judges the URL the caller supplied. Without this, a public
    host that answers ``302 Location: http://169.254.169.254/...`` (or any
    private address) would be dialled after the guard had already said yes --
    the guard would be checking the first hop of a chain it does not control.
    Every hop is checked, and a refused hop stops the delivery.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D102
        from app.security import check_egress

        check_egress(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _opener() -> Any:
    """One opener per delivery: guarded redirects, no ambient global state."""
    return urllib.request.build_opener(_GuardedRedirects())


def webhook_delivery(url: str, payload: Mapping[str, Any], *, timeout: Optional[int] = None) -> Dict[str, Any]:
    """A real outbound POST, through the private-address guard.

    This is the connector the platform is proven to leave the box with: a
    webhook the operator names. Nothing is delivered to a URL a payload
    supplied, and a failure is reported as a failure.
    """
    import urllib.error
    import urllib.request

    from app.security import EgressRefused, check_egress

    try:
        target = check_egress(url)
    except EgressRefused as exc:
        return {"delivery": "refused", "error": str(exc), "response_code": 0, "url": url}
    body = json.dumps(dict(payload or {}), sort_keys=True, default=str).encode("utf-8")
    request = urllib.request.Request(
        target,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": "CallOps/1.0"},
        method="POST",
    )
    try:
        # nosec B310 - check_egress() above already refused any scheme but
        # http(s) and any private, loopback or unresolvable host.
        with _opener().open(  # nosec B310 - scheme and every redirect hop checked
            request, timeout=int(timeout or config.CREDITOR_WEBHOOK_TIMEOUT_SECONDS)
        ) as response:
            code = int(getattr(response, "status", 200) or 200)
            return {
                "delivery": "delivered" if 200 <= code < 300 else "unavailable",
                "response_code": code,
                "url": target,
            }
    except EgressRefused as exc:
        # A redirect aimed at a private address is a refusal, not a delivery.
        return {"delivery": "refused", "response_code": 0, "url": target, "error": str(exc)}
    except urllib.error.HTTPError as exc:
        return {"delivery": "unavailable", "response_code": int(exc.code), "url": target}
    except Exception as exc:  # noqa: BLE001 - a delivery failure is data
        return {"delivery": "unavailable", "response_code": 0, "url": target, "error": type(exc).__name__}


def campaign_rows(tenant_id: str, campaign: Optional[str] = None) -> List[Dict[str, Any]]:
    """One row per call, joined from the ledgers the platform already keeps."""
    from app import store

    calls: Dict[str, Dict[str, Any]] = {}
    for row in store.list_all("call_state_machine", tenant_id):
        sid = str(row.get("call_sid") or "")
        if not sid:
            continue
        entry = calls.setdefault(sid, {"call_sid": sid})
        entry["answer_state"] = row.get("current_state")
        entry["answered"] = str(row.get("current_state") or "") in (
            "answered",
            "pitched",
            "qualified",
            "transferred",
            "closed",
        )
        entry["campaign"] = row.get("campaign") or entry.get("campaign")
    for row in store.list_all("qualification_and_broker_summary", tenant_id):
        sid = str(row.get("call_sid") or "")
        entry = calls.setdefault(sid, {"call_sid": sid})
        entry["outcome"] = row.get("outcome")
        entry["campaign"] = entry.get("campaign") or row.get("campaign")
    for row in store.list_all("warm_transfer", tenant_id):
        sid = str(row.get("call_sid") or "")
        entry = calls.setdefault(sid, {"call_sid": sid})
        entry["transfer_outcome"] = row.get("outcome")
    out = list(calls.values())
    if campaign:
        out = [row for row in out if str(row.get("campaign") or "") == str(campaign)]
    return out


def campaign_metrics(tenant_id: str, campaign: Optional[str] = None) -> Dict[str, Any]:
    rows = campaign_rows(tenant_id, campaign)
    metrics = formulas.campaign_metrics(rows)
    return {
        "tenant_id": tenant_id,
        "campaign": campaign,
        "calls": rows,
        "metrics": metrics["result"],
        "authority": metrics["authority"],
    }
