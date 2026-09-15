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

NOTE_KIND = {"open": "inbox", "in_progress": "active", "closed": "archived"}
PREVIEW_LEN = 80
TOKEN_RE = re.compile(r"[a-z0-9]+")


def envelope_status(payload: Dict[str, Any]) -> str:
    status = str(payload.get("status") or "open")
    return status if status in STATUS_VALUES else "open"


def allowed_next_status(status: str) -> Tuple[str, ...]:
    return STATUS_NEXT.get(status, ())


def tokenize(text: str) -> List[str]:
    return TOKEN_RE.findall((text or "").lower())


def word_count(title: str, body: str) -> int:
    return len(tokenize(title)) + len(tokenize(body))


def preview(body: str, limit: int = PREVIEW_LEN) -> str:
    text = (body or "").strip()
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


def title_norm(title: str) -> str:
    tokens = tokenize(title)
    return " ".join(tokens) if tokens else "untitled"


def search_blob(title: str, body: str) -> str:
    return f"{title or ''} {body or ''}".strip().lower()


def note_kind(status: str) -> str:
    return NOTE_KIND.get(status, NOTE_KIND["open"])


def matches_keyword(record: Dict[str, Any], keyword: str) -> bool:
    """True when every keyword token appears in title or body."""
    query = tokenize(keyword)
    if not query:
        return True
    haystack = set(
        tokenize(
            search_blob(
                str(record.get("title") or ""),
                str(record.get("body") or ""),
            )
        )
    )
    return all(token in haystack for token in query)


def compose_note(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Derive note scalars from envelope + title/body. Schema sample is accepted."""
    status = envelope_status(payload)
    title = str(payload.get("title") or payload.get("reference") or "sample")
    body = str(payload.get("body") or "")
    return {
        "title": title,
        "body": body,
        "title_norm": title_norm(title),
        "word_count": word_count(title, body),
        "preview": preview(body or title),
        "note_kind": note_kind(status),
        "search_blob": search_blob(title, body),
        "allowed_next_status": list(allowed_next_status(status)),
    }


def filter_notes(records: List[Dict[str, Any]], keyword: str) -> List[Dict[str, Any]]:
    return [row for row in records if matches_keyword(row, keyword)]
