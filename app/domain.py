"""Notes kernel. Envelope-driven; no invented caller contracts."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

STATUS_VALUES = ("open", "in_progress", "closed")
STATUS_NEXT: Dict[str, Tuple[str, ...]] = {
    "open": ("in_progress",),
    "in_progress": ("closed",),
    "closed": (),
}
NOTE_OPS = ("create", "update", "delete", "search")


def envelope_status(payload: Dict[str, Any]) -> str:
    status = str(payload.get("status") or "open")
    return status if status in STATUS_VALUES else "open"


def allowed_next_status(status: str) -> Tuple[str, ...]:
    return STATUS_NEXT.get(status, ())


def note_op(payload: Dict[str, Any]) -> str:
    op = str(payload.get("note_op") or "create")
    return op if op in NOTE_OPS else "create"


def note_title(payload: Dict[str, Any]) -> str:
    return str(payload.get("title") or payload.get("reference") or "sample")


def note_body(payload: Dict[str, Any]) -> str:
    raw = payload.get("body")
    if raw is None:
        return "sample"
    return str(raw)


def note_keyword(payload: Dict[str, Any]) -> str:
    return str(payload.get("keyword") or "")


def note_matches(record: Dict[str, Any], keyword: str) -> bool:
    needle = (keyword or "").strip().lower()
    if not needle:
        return True
    hay = " ".join(
        str(record.get(key) or "")
        for key in ("title", "body", "reference", "keyword")
    ).lower()
    return needle in hay


def search_notes(records: List[Dict[str, Any]], keyword: str) -> List[Dict[str, Any]]:
    return [row for row in records if note_matches(row, keyword)]


def normalize_note(payload: Dict[str, Any]) -> Dict[str, Any]:
    status = envelope_status(payload)
    reference = str(payload.get("reference") or "sample")
    title = note_title(payload)
    body = note_body(payload)
    keyword = note_keyword(payload)
    op = note_op(payload)
    return {
        **payload,
        "reference": reference,
        "status": status,
        "title": title,
        "body": body,
        "keyword": keyword,
        "note_op": op,
        "capability": "productivity_core",
        "channel": "mcp",
        "allowed_next_status": list(allowed_next_status(status)),
    }


def normalize_audit(payload: Dict[str, Any]) -> Dict[str, Any]:
    status = envelope_status(payload)
    reference = str(payload.get("reference") or "sample")
    return {
        **payload,
        "reference": reference,
        "status": status,
        "event_action": str(payload.get("event_action") or payload.get("capability") or "audit"),
        "resource": str(payload.get("resource") or reference),
        "capability": "audit",
        "channel": "mcp",
        "category": "data_access",
        "allowed_next_status": list(allowed_next_status(status)),
    }
