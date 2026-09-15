"""Notes kernel. Envelope-driven; no invented caller contracts."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

STATUS_VALUES = ("open", "in_progress", "closed")
STATUS_NEXT: Dict[str, Tuple[str, ...]] = {
    "open": ("in_progress",),
    "in_progress": ("closed",),
    "closed": (),
}

AUDIT_CATEGORIES = ("data_access", "auth", "system", "admin")
PREVIEW_LIMIT = 72


def envelope_status(payload: Dict[str, Any]) -> str:
    status = str(payload.get("status") or "open")
    return status if status in STATUS_VALUES else "open"


def allowed_next_status(status: str) -> Tuple[str, ...]:
    return STATUS_NEXT.get(status, ())


def as_text(value: Any) -> str:
    return "" if value is None else str(value)


def word_count(*parts: Any) -> int:
    text = " ".join(as_text(part) for part in parts if as_text(part))
    return len([token for token in text.split() if token])


def char_count(*parts: Any) -> int:
    return sum(len(as_text(part)) for part in parts)


def preview(text: Any, limit: int = PREVIEW_LIMIT) -> str:
    raw = as_text(text).strip()
    if len(raw) <= limit:
        return raw
    return raw[: limit - 1].rstrip() + "…"


def tokens(text: Any) -> List[str]:
    return re.findall(r"[a-z0-9]+", as_text(text).lower())


def matches_keyword(title: Any, body: Any, keyword: Any) -> bool:
    needle = as_text(keyword).strip().lower()
    if not needle:
        return True
    haystack = f"{as_text(title)} {as_text(body)}".lower()
    return needle in haystack


def note_summary(title: Any, body: Any, status: str = "open") -> str:
    return f"note {as_text(title) or 'untitled'} status={status} words={word_count(title, body)}"


def audit_category(value: Any) -> str:
    category = as_text(value) or "data_access"
    return category if category in AUDIT_CATEGORIES else "data_access"
