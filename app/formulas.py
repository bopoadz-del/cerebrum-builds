"""The arithmetic CallOps runs: pacing, backoff, windows, conversion, money.

Every function here is pure, returns its inputs beside its result, and
carries the ``formulas`` authority label — an operator can see which layer
produced a number. The values these functions work from are operator
settings (app/config.py), never constants baked into the arithmetic:

* daily cap remaining and dial pacing
* retry backoff after a busy / no-answer (max 3 attempts, spaced)
* the best call window for a language
* attempted / answered / interest / transfer / conversion metrics
* money: displayed price with VAT, and broker commission — both refuse by
  name when the operator has not stated the currency or the rates, because
  the brief does not state them and this platform does not guess a country.

Where a domain fact is not stated by the brief it is not invented here.
The retry ceiling (3) and the window shape come from the brief; the exact
minutes, cap and window hours are settings.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence

from app import config
from app.authority import Claim, envelope

FORMULA_LAYER = "formulas"

#: The three outcomes the conversation is allowed to end in.
OUTCOMES: tuple[str, ...] = (
    "project_interested",
    "other_re_interested",
    "not_interested",
)

#: The platform's own ceiling on dialling one lead, from the brief.
MAX_ATTEMPTS = config.MAX_ATTEMPTS


def _labelled(name: str, inputs: Dict[str, Any], result: Any, source: str = "") -> Dict[str, Any]:
    claim = Claim(name=name, value=result, layer=FORMULA_LAYER, source=source or name)
    return {
        "formula": name,
        "inputs": inputs,
        "result": result,
        "authority": envelope([claim]),
    }


def calls_remaining(
    *,
    daily_cap: Optional[int] = None,
    attempted_today: int = 0,
    reserved: int = 0,
) -> Dict[str, Any]:
    """How many dials this campaign may still make today."""
    cap = config.DAILY_CALL_CAP if daily_cap is None else int(daily_cap)
    attempted = max(0, int(attempted_today))
    held = max(0, int(reserved))
    remaining = max(0, cap - attempted - held)
    inputs = {"daily_cap": cap, "attempted_today": attempted, "reserved": held}
    return {**_labelled("calls_remaining", inputs, remaining), "cap_reached": remaining == 0}


def dial_pacing(
    *,
    remaining: int,
    window_minutes: int,
    concurrency: Optional[int] = None,
    dial_interval_seconds: Optional[int] = None,
) -> Dict[str, Any]:
    """Spacing between dials so a window's remaining slots are usable."""
    free = max(0, int(remaining))
    minutes = max(1, int(window_minutes))
    lanes = max(1, int(config.CONCURRENCY if concurrency is None else concurrency))
    floor = max(1, int(config.DIAL_INTERVAL_SECONDS if dial_interval_seconds is None else dial_interval_seconds))
    if free == 0:
        interval = 0
    else:
        interval = max(floor, int((minutes * 60) / max(1, free / lanes)))
    inputs = {
        "remaining": free,
        "window_minutes": minutes,
        "concurrency": lanes,
        "dial_interval_floor_seconds": floor,
    }
    return {**_labelled("dial_pacing", inputs, interval), "concurrency": lanes}


def retry_backoff(
    *,
    attempt: int,
    reason: str = "no-answer",
    backoff_minutes: Optional[int] = None,
    factor: Optional[float] = None,
    max_attempts: Optional[int] = None,
) -> Dict[str, Any]:
    """When to try a lead again, and whether there is a next attempt.

    The brief's rule: max 3 attempts, spaced. ``attempt`` is the attempt
    that just failed, so attempt 3 returns ``exhausted`` and no next time.
    """
    ceiling = int(config.MAX_ATTEMPTS if max_attempts is None else max_attempts)
    base = int(config.RETRY_BACKOFF_MINUTES if backoff_minutes is None else backoff_minutes)
    growth = float(config.RETRY_BACKOFF_FACTOR if factor is None else factor)
    tried = max(1, int(attempt))
    label = str(reason or "no-answer").strip().lower()
    if label not in ("busy", "no-answer", "no_answer", "failed", "declined", "voicemail"):
        label = "no-answer"
    exhausted = tried >= ceiling
    delay = 0 if exhausted else int(round(base * (growth ** (tried - 1))))
    inputs = {
        "attempt": tried,
        "reason": label,
        "max_attempts": ceiling,
        "backoff_minutes": base,
        "factor": growth,
    }
    result = {
        **_labelled("retry_backoff", inputs, delay),
        "next_attempt": None if exhausted else tried + 1,
        "exhausted": exhausted,
        "attempts_remaining": max(0, ceiling - tried),
    }
    return result


def _parse_windows(spec: str) -> List[tuple]:
    out: List[tuple] = []
    for chunk in str(spec or "").split(";"):
        chunk = chunk.strip()
        if not chunk or "-" not in chunk:
            continue
        start, _, end = chunk.partition("-")
        try:
            sh, sm = [int(part) for part in start.strip().split(":")[:2]]
            eh, em = [int(part) for part in end.strip().split(":")[:2]]
        except ValueError:
            continue
        out.append((sh * 60 + sm, eh * 60 + em))
    return out


def _now_minutes(moment: Optional[datetime]) -> int:
    current = moment or datetime.now(timezone.utc)
    return current.hour * 60 + current.minute


def best_call_window(
    *,
    language: str = "en",
    moment: Optional[datetime] = None,
    windows: Optional[str] = None,
) -> Dict[str, Any]:
    """The best window for this language, and whether now is inside it."""
    lang = str(language or "en").strip().lower()[:2]
    spec = windows if windows is not None else config.CALL_WINDOW_BY_LANGUAGE.get(
        lang, config.CALL_WINDOW_BY_LANGUAGE["en"]
    )
    spans = _parse_windows(spec)
    now_minutes = _now_minutes(moment)
    inside = any(start <= now_minutes <= end for start, end in spans)
    next_window: Optional[str] = None
    if spans and not inside:
        ahead = [(start, end) for start, end in spans if start > now_minutes]
        chosen = ahead[0] if ahead else spans[0]
        next_window = "%02d:%02d" % divmod(chosen[0], 60)
    label = "%02d:%02d-%02d:%02d" % (
        (spans[0][0] // 60, spans[0][0] % 60, spans[0][1] // 60, spans[0][1] % 60)
    ) if spans else ""
    inputs = {"language": lang, "windows": spec, "minutes_now": now_minutes}
    result = {
        **_labelled("best_call_window", inputs, label),
        "inside_window": inside,
        "windows": [
            {"start": "%02d:%02d" % divmod(s, 60), "end": "%02d:%02d" % divmod(e, 60)}
            for s, e in spans
        ],
        "next_window": next_window,
        "timezone": config.CALL_WINDOW_TZ,
        "days": [d.strip() for d in config.CALL_WINDOW_DAYS.split(",") if d.strip()],
    }
    return result


def window_open(
    *,
    language: str = "en",
    moment: Optional[datetime] = None,
    allowed_days: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """The call-window guard a workflow transition is checked against."""
    current = moment or datetime.now(timezone.utc)
    days = [str(d).strip().lower()[:3] for d in (allowed_days or config.CALL_WINDOW_DAYS.split(","))]
    day = current.strftime("%a").lower()[:3]
    best = best_call_window(language=language, moment=current)
    open_now = bool(best["inside_window"]) and day in days
    reason = "open" if open_now else (
        "outside_window" if day in days else "outside_allowed_day"
    )
    return {
        **_labelled(
            "window_open",
            {"language": language, "day": day, "days": days, "minutes_now": _now_minutes(current)},
            open_now,
        ),
        "reason": reason,
        "window": best["result"],
        "next_window": best["next_window"],
        "timezone": config.CALL_WINDOW_TZ,
    }


def campaign_metrics(rows: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Attempted / answered / interest split / transfers / conversion.

    One row per call record. Interest is the brief's three-outcome
    vocabulary; anything else is counted as unclassified rather than folded
    into a category it does not belong to.
    """
    attempted = answered = transferred = qualified = 0
    interest = {outcome: 0 for outcome in OUTCOMES}
    unclassified = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        attempted += 1
        state = str(row.get("answer_state") or row.get("answered") or "").lower()
        answered_flag = row.get("answered")
        if state in ("answered", "true") or answered_flag is True:
            answered += 1
        outcome = str(row.get("outcome") or "").strip()
        if outcome in interest:
            interest[outcome] += 1
            qualified += 1
        elif outcome:
            unclassified += 1
        if str(row.get("transfer_outcome") or "").lower() in ("transferred", "bridged"):
            transferred += 1
    conversion = (transferred / attempted) if attempted else 0.0
    qualify_rate = (qualified / answered) if answered else 0.0
    inputs = {"calls": attempted, "outcomes": list(OUTCOMES)}
    result = {
        "attempted": attempted,
        "answered": answered,
        "qualified": qualified,
        "transfers": transferred,
        "interest": interest,
        "unclassified": unclassified,
        "answer_rate": round(answered / attempted, 4) if attempted else 0.0,
        "qualify_rate": round(qualify_rate, 4),
        "conversion": round(conversion, 4),
    }
    return {**_labelled("campaign_metrics", inputs, result)}


def price_with_tax(amount: float, *, quantity: int = 1) -> Dict[str, Any]:
    """A displayed price: the operator's currency and VAT, or a named refusal.

    Neither the country nor the currency nor any tax rate is in the brief,
    so nothing is assumed here: an unset CURRENCY or VAT_RATE refuses and
    says which setting to supply.
    """
    from app.config import SettingMissing

    currency = config.currency()
    rate = config.vat_rate()
    net = float(amount) * max(1, int(quantity))
    tax = round(net * rate, 2)
    inputs = {"amount": float(amount), "quantity": int(quantity), "vat_rate": rate}
    return {
        **_labelled("price_with_tax", inputs, round(net + tax, 2), source=f"CURRENCY={currency}"),
        "currency": currency,
        "net": round(net, 2),
        "tax": tax,
        "gross": round(net + tax, 2),
        "vat_rate": rate,
        "settings_required": ["CURRENCY", "VAT_RATE"],
    }


def broker_commission(sale_price: float, *, rate: Optional[float] = None) -> Dict[str, Any]:
    """Commission owed on a closed deal, from the operator's stated rate."""
    currency = config.currency()
    applied = config.broker_commission_rate() if rate is None else float(rate)
    commission = round(float(sale_price) * applied, 2)
    inputs = {"sale_price": float(sale_price), "rate": applied}
    return {
        **_labelled("broker_commission", inputs, commission, source=f"CURRENCY={currency}"),
        "currency": currency,
        "rate": applied,
        "settings_required": ["CURRENCY", "BROKER_COMMISSION_RATE"],
    }


def next_attempt_time(
    *, attempt: int, now: Optional[datetime] = None, reason: str = "no-answer"
) -> Dict[str, Any]:
    """The backoff above, as a wall-clock instant the queue can schedule."""
    moment = now or datetime.now(timezone.utc)
    policy = retry_backoff(attempt=attempt, reason=reason)
    scheduled = None if policy["exhausted"] else (moment + timedelta(minutes=policy["result"])).isoformat()
    return {
        **policy,
        "formula": "next_attempt_time",
        "now": moment.isoformat(),
        "scheduled_at": scheduled,
    }


CATALOG: tuple[Dict[str, str], ...] = tuple(
    {
        "id": name,
        "means": meaning,
    }
    for name, meaning in (
        ("calls_remaining", "dials left under the campaign's daily cap"),
        ("dial_pacing", "seconds between dials so a window's slots are usable"),
        ("retry_backoff", "minutes before the next attempt, max 3 spaced attempts"),
        ("next_attempt_time", "that backoff as a schedulable instant"),
        ("best_call_window", "per-language calling window and whether now is in it"),
        ("window_open", "the call-window guard a state transition is checked against"),
        ("campaign_metrics", "attempted, answered, interest split, transfers, conversion"),
        ("price_with_tax", "a displayed price in the operator's currency and VAT"),
        ("broker_commission", "commission owed on a closed deal"),
    )
)
