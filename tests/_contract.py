"""One schema-sample builder, shared by the code and pilot suites.

The factory's own probes (WRITER behaviour, PRODUCT one-record round-trip,
scripts/acceptance.py) build a payload from each capability's own FIELDS +
CONSTRAINTS and nothing else. A suite that hand-writes payloads drifts from
that contract: the previous pass asserted ``{'patient_name': 'sample',
'reference': 'sample', 'status': 'open'}`` against models that also require
``procedure`` / ``appointment_type`` / ``staff_role`` and reported the
product's own 422 as a product defect.

So this module mirrors the probe's ``_value`` rules exactly, once:

* CONSTRAINTS.allowed_values[0] when declared
* int/float -> min when set (min=0 stays 0), else 1
* bool -> False
* email-shaped name -> a valid address
* datetime / *_at -> 2026-09-03T10:00:00, date / *_date -> 2026-09-03,
  time names -> 10:00:00
* status / *_status -> open, channel / *_channel -> email
* otherwise the word sample
"""

from __future__ import annotations

from typing import Any, Dict

DEFAULT_TENANT = "local"
SAMPLE_EMAIL = "sample@example.com"
SAMPLE_DATETIME = "2026-09-03T10:00:00"
SAMPLE_DATE = "2026-09-03"
SAMPLE_TIME = "10:00:00"


def annotation(cls: Any, name: str) -> str:
    """Declared type for a field. PEP 563 makes annotations strings."""
    raw = getattr(cls, "__annotations__", {}).get(name, "str")
    return str(raw).replace("Optional[", "").replace("]", "").strip()


def sample_value(cls: Any, name: str) -> Any:
    constraints = getattr(cls, "CONSTRAINTS", {}) or {}
    rules = constraints.get(name) or {}
    allowed = rules.get("allowed_values")
    if allowed:
        return allowed[0]
    kind = annotation(cls, name)
    kind_l = kind.lower().replace("datetime.", "").replace(" ", "")
    if kind in ("int", "float") or kind_l in ("int", "float"):
        low, high = rules.get("min"), rules.get("max")
        if low is not None:
            return low
        if high is not None:
            return high if high < 1 else 1
        return 1
    if kind == "bool" or kind_l == "bool":
        return False
    if "email" in name.lower():
        return SAMPLE_EMAIL
    fmt = str(rules.get("format") or "").lower().replace("-", "")
    lowered = name.lower()
    if (
        kind_l in ("datetime", "timestamp")
        or fmt in ("datetime", "timestamp", "iso8601")
        or lowered.endswith("_at")
        or lowered.endswith("_datetime")
    ):
        return SAMPLE_DATETIME
    if kind_l == "date" or fmt == "date" or lowered.endswith("_date"):
        return SAMPLE_DATE
    if kind_l == "time" or fmt == "time" or lowered.endswith("_time") or lowered == "time":
        return SAMPLE_TIME
    if lowered == "status" or lowered.endswith("_status"):
        return "open"
    if lowered == "channel" or lowered.endswith("_channel"):
        return "email"
    return "sample"


def sample_payload(cls: Any) -> Dict[str, Any]:
    """A valid instance of the entity, built from the entity's own model."""
    return {name: sample_value(cls, name) for name in getattr(cls, "FIELDS", [])}


def required_fields(cls: Any) -> list:
    constraints = getattr(cls, "CONSTRAINTS", {}) or {}
    return [
        name
        for name in getattr(cls, "FIELDS", [])
        if (constraints.get(name) or {}).get("required")
    ]


def invalid_value(cls: Any, name: str) -> Any:
    """A value the entity's own vocabulary refuses."""
    rules = (getattr(cls, "CONSTRAINTS", {}) or {}).get(name) or {}
    allowed = list(rules.get("allowed_values") or [])
    if allowed:
        return "__not_in_contract__"
    return None
