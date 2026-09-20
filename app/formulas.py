"""Deterministic facility-management formulas (SLA, workload, match, rollup).

Written by the factory WRITER role (codewhale exec)

Pure stdlib arithmetic, no provider and no network: these are the figures
the platform computes on its own records rather than sending to the LLM.
Every function refuses malformed input by name rather than returning a
number that looks authoritative; the caller sees why it could not be
computed.

Money is AED (the brief names the United Arab Emirates for a Dubai schools
estate). No tax rate is encoded here: the brief names a country and a
currency, not a rate, so any VAT figure a caller needs is a named input it
supplies (§9 MONEY). Nothing in this module assumes a rate.

Scope: READS the numbers handed in by a handler, WRITES a figure. It never
touches the store, the filesystem or the network.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional

#: Currency the brief names for this estate. A caller may override it, but
#: the platform never invents a different one.
CURRENCY = os.environ.get("PLATFORM_CURRENCY") or "AED"

#: Service targets, in hours, by priority. These are the operator's
#: settings, not constants baked into the product: each one is read from
#: the environment and falls back to the pilot default recorded here.
DEFAULT_RESPONSE_HOURS: Dict[str, int] = {
    "critical": 4,
    "high": 24,
    "medium": 72,
    "low": 168,
}

#: Priority weight used when ranking candidate field staff.
PRIORITY_WEIGHT: Dict[str, int] = {
    "critical": 100,
    "high": 75,
    "medium": 50,
    "low": 25,
}


class FormulaError(ValueError):
    """A formula was asked for a figure its inputs cannot support."""


def to_number(value: Any, name: str) -> float:
    """Coerce a facility figure, or refuse by name."""
    if isinstance(value, bool) or value is None:
        raise FormulaError(f"{name} must be a number")
    try:
        return float(value)
    except (TypeError, ValueError):
        raise FormulaError(
            f"{name} must be a number, got {type(value).__name__}"
        ) from None


def _number(value: Any, name: str) -> float:
    return to_number(value, name)


def response_target_hours(priority: Any = "medium", category: Any = "") -> float:
    """Service target in hours for a complaint's priority.

    The environment wins over the pilot default when the operator has set
    ``SLA_<PRIORITY>_HOURS``: a service target is the customer's to change,
    not the vendor's to freeze.
    """
    name = str(priority or "medium").strip().lower() or "medium"
    env_key = "SLA_%s_HOURS" % name.upper()
    configured = os.environ.get(env_key)
    if configured:
        try:
            hours = float(configured)
        except ValueError:
            raise FormulaError(f"{env_key} must be a number") from None
        if hours <= 0:
            raise FormulaError(f"{env_key} must be greater than zero")
        return hours
    if name not in DEFAULT_RESPONSE_HOURS:
        raise FormulaError(
            "priority must be one of: "
            + ", ".join(sorted(DEFAULT_RESPONSE_HOURS))
        )
    return float(DEFAULT_RESPONSE_HOURS[name])


def sla_due_at(reported_at: Any, hours: Any) -> str:
    """ISO-8601 deadline: the moment the service target expires."""
    window = _number(hours, "hours")
    if window <= 0:
        raise FormulaError("hours must be greater than zero")
    stamp = str(reported_at or "").strip()
    if not stamp:
        started = datetime.now(timezone.utc)
    else:
        try:
            started = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        except ValueError:
            raise FormulaError(
                "reported_at must be an ISO-8601 timestamp"
            ) from None
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
    return (started + timedelta(hours=window)).isoformat()


def sla_breach(*, due_at: Any, closed_at: Any = None) -> bool:
    """True when the record closed after its deadline, or is still late."""
    deadline = _parse(due_at, "due_at")
    if deadline is None:
        raise FormulaError("due_at must be an ISO-8601 timestamp")
    end = _parse(closed_at, "closed_at") or datetime.now(timezone.utc)
    return end > deadline


def closure_hours(*, reported_at: Any, closed_at: Any) -> float:
    """Hours from report to closure."""
    start = _parse(reported_at, "reported_at")
    end = _parse(closed_at, "closed_at")
    if start is None or end is None:
        raise FormulaError("reported_at and closed_at must be ISO-8601 stamps")
    if end < start:
        raise FormulaError("closed_at cannot precede reported_at")
    return round((end - start).total_seconds() / 3600.0, 4)


def sla_compliance_pct(*, within_target: Any, total: Any) -> float:
    """Share of closures that met the service target, as a percentage."""
    met = _number(within_target, "within_target")
    everything = _number(total, "total")
    if everything < 0 or met < 0:
        raise FormulaError("counts cannot be negative")
    if everything == 0:
        raise FormulaError("total must be greater than zero")
    if met > everything:
        raise FormulaError("within_target cannot exceed total")
    return round((met / everything) * 100.0, 4)


def average_closure_hours(*, total_hours: Any, count: Any) -> float:
    """Mean closure time across a set of closed complaints."""
    hours = _number(total_hours, "total_hours")
    n = _number(count, "count")
    if n <= 0:
        raise FormulaError("count must be greater than zero")
    if hours < 0:
        raise FormulaError("total_hours cannot be negative")
    return round(hours / n, 4)


def utilisation_pct(*, open_jobs: Any, headcount: Any) -> float:
    """Open jobs per field-staff member, as a workload percentage."""
    jobs = _number(open_jobs, "open_jobs")
    people = _number(headcount, "headcount")
    if jobs < 0:
        raise FormulaError("open_jobs cannot be negative")
    if people <= 0:
        raise FormulaError("headcount must be greater than zero")
    return round((jobs / people) * 100.0, 4)


def workload_score(*, open_jobs: Any, headcount: Any = 1, cap: Any = 5) -> float:
    """0-100 workload pressure for one team or member (lower is freer).

    ``cap`` is the number of concurrent jobs a field-staff member is
    expected to carry; it is a named setting, not a law of the domain.
    """
    jobs = _number(open_jobs, "open_jobs")
    people = _number(headcount, "headcount")
    ceiling = _number(cap, "cap")
    if jobs < 0:
        raise FormulaError("open_jobs cannot be negative")
    if people <= 0:
        raise FormulaError("headcount must be greater than zero")
    if ceiling <= 0:
        raise FormulaError("cap must be greater than zero")
    load = jobs / (people * ceiling)
    return round(max(0.0, min(1.0, load)) * 100.0, 4)


def match_score(
    *,
    trade_match: bool = False,
    skill_match: bool = False,
    same_school: bool = False,
    workload: Any = 0,
    priority: Any = "medium",
) -> float:
    """0-100 suitability of a candidate field staff member for a job.

    The weights are the platform's routing policy: the right trade is the
    strongest signal, an exact skill next, being already on site third, and
    current workload a penalty. Higher is a better match; a manual
    override by management still wins.
    """
    load = _number(workload, "workload")
    if load < 0 or load > 100:
        raise FormulaError("workload must be between 0 and 100")
    name = str(priority or "medium").strip().lower()
    if name not in PRIORITY_WEIGHT:
        raise FormulaError(
            "priority must be one of: " + ", ".join(sorted(PRIORITY_WEIGHT))
        )
    if not isinstance(trade_match, bool) or not isinstance(skill_match, bool):
        raise FormulaError("trade_match and skill_match must be booleans")
    if not isinstance(same_school, bool):
        raise FormulaError("same_school must be a boolean")
    base = 0.0
    base += 45.0 if trade_match else 0.0
    base += 20.0 if skill_match else 0.0
    base += 15.0 if same_school else 0.0
    base += PRIORITY_WEIGHT[name] * 0.10
    base -= load * 0.20
    return round(max(0.0, min(100.0, base)), 4)


def estate_total(*, schools: Any) -> float:
    """The estate's school count, refusing a non-list."""
    if not isinstance(schools, (list, tuple)):
        raise FormulaError("schools must be a list")
    if not schools:
        raise FormulaError("schools cannot be empty")
    return float(len(schools))


def portfolio_total(
    records: Iterable[Dict[str, Any]],
    *,
    key: str,
) -> float:
    """Sum one numeric field across records, naming the records that break it."""
    if not isinstance(key, str) or not key.strip():
        raise FormulaError("key must be a non-empty string")
    total = 0.0
    invalid: List[str] = []
    for index, record in enumerate(records or ()):
        if not isinstance(record, dict):
            invalid.append(f"record {index} is not an object")
            continue
        if key not in record or record[key] in (None, ""):
            continue
        value = record[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            invalid.append(f"record {index} {key}={value!r}")
            continue
        total += float(value)
    if invalid:
        raise FormulaError("non-numeric values: " + "; ".join(invalid[:5]))
    return round(total, 4)


def complaint_rate_per_school(*, complaints: Any, schools: Any) -> float:
    """Complaint volume per school across the estate."""
    total = _number(complaints, "complaints")
    count = _number(schools, "schools")
    if total < 0:
        raise FormulaError("complaints cannot be negative")
    if count <= 0:
        raise FormulaError("schools must be greater than zero")
    return round(total / count, 4)


def _parse(value: Any, name: str) -> Optional[datetime]:
    if value is None or isinstance(value, datetime):
        return value if isinstance(value, datetime) else None
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        raise FormulaError(f"{name} must be an ISO-8601 timestamp") from None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def evaluate(name: str, **kwargs: Any) -> Dict[str, Any]:
    """Named lookup used by the formula layer and the API surface."""
    known = {
        "response_target_hours": response_target_hours,
        "sla_due_at": sla_due_at,
        "sla_breach": sla_breach,
        "closure_hours": closure_hours,
        "sla_compliance_pct": sla_compliance_pct,
        "average_closure_hours": average_closure_hours,
        "utilisation_pct": utilisation_pct,
        "workload_score": workload_score,
        "match_score": match_score,
        "complaint_rate_per_school": complaint_rate_per_school,
    }
    fn = known.get(str(name or "").strip())
    if fn is None:
        raise FormulaError(
            "unknown formula: %s (known: %s)"
            % (name, ", ".join(sorted(known)))
        )
    try:
        return {"formula": name, "value": fn(**kwargs), "currency": CURRENCY}
    except FormulaError:
        raise
    except TypeError as exc:
        raise FormulaError(f"{name}: {exc}") from None


def catalogue() -> List[Dict[str, Any]]:
    """The named formulas this platform ships, for the UI and the API."""
    return [
        {
            "name": "response_target_hours",
            "purpose": "service target hours for a complaint priority",
            "inputs": ["priority", "category"],
        },
        {
            "name": "sla_due_at",
            "purpose": "ISO deadline a complaint is due by",
            "inputs": ["reported_at", "hours"],
        },
        {
            "name": "sla_breach",
            "purpose": "whether a closure missed the target",
            "inputs": ["due_at", "closed_at"],
        },
        {
            "name": "closure_hours",
            "purpose": "hours from report to closure",
            "inputs": ["reported_at", "closed_at"],
        },
        {
            "name": "sla_compliance_pct",
            "purpose": "share of closures within target",
            "inputs": ["within_target", "total"],
        },
        {
            "name": "average_closure_hours",
            "purpose": "mean closure time",
            "inputs": ["total_hours", "count"],
        },
        {
            "name": "utilisation_pct",
            "purpose": "open jobs per field-staff member",
            "inputs": ["open_jobs", "headcount"],
        },
        {
            "name": "workload_score",
            "purpose": "0-100 workload pressure for a team or member",
            "inputs": ["open_jobs", "headcount", "cap"],
        },
        {
            "name": "match_score",
            "purpose": "0-100 suitability of a field staff member",
            "inputs": ["trade_match", "skill_match", "same_school", "workload",
                       "priority"],
        },
        {
            "name": "complaint_rate_per_school",
            "purpose": "complaint volume per school across the estate",
            "inputs": ["complaints", "schools"],
        },
    ]
