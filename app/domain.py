"""Notes kernel. Envelope-driven; no invented caller contracts."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

STATUS_VALUES = ("open", "in_progress", "closed")
STATUS_NEXT: Dict[str, Tuple[str, ...]] = {
    "open": ("in_progress",),
    "in_progress": ("closed",),
    "closed": (),
}
STATUS_LABEL = {"open": "inbox", "in_progress": "editing", "closed": "archived"}

_QUEUE: List[Dict[str, Any]] = []


def envelope_status(payload: Dict[str, Any]) -> str:
    status = str(payload.get("status") or "open")
    return status if status in STATUS_VALUES else "open"


def allowed_next_status(status: str) -> Tuple[str, ...]:
    return STATUS_NEXT.get(status, ())


def note_title(payload: Dict[str, Any]) -> str:
    return str(payload.get("title") or payload.get("reference") or "sample")


def note_body(payload: Dict[str, Any]) -> str:
    return str(payload.get("body") or "")


def word_count(text: str) -> int:
    return len([part for part in str(text).split() if part])


def preview(text: str, limit: int = 80) -> str:
    body = str(text or "")
    return body if len(body) <= limit else body[: limit - 1] + "…"


def matches_keyword(record: Dict[str, Any], keyword: str) -> bool:
    needle = str(keyword or "").strip().lower()
    if not needle:
        return True
    hay = " ".join(
        str(record.get(key) or "")
        for key in ("title", "body", "reference", "preview")
    ).lower()
    return needle in hay


def normalize_note(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Fill envelope + note scalars. Empty probe becomes a persistable sample note."""
    status = envelope_status(payload)
    title = note_title(payload)
    body = note_body(payload) or "sample"
    reference = str(payload.get("reference") or title or "sample")
    record = {
        **payload,
        "reference": reference,
        "status": status,
        "title": title,
        "body": body,
        "word_count": word_count(body),
        "preview": preview(body),
        "status_label": STATUS_LABEL.get(status, "inbox"),
        "allowed_next_status": list(allowed_next_status(status)),
        "capability": "productivity_core",
        "channel": "mcp",
    }
    return record


def normalize_audit(payload: Dict[str, Any]) -> Dict[str, Any]:
    status = envelope_status(payload)
    reference = str(payload.get("reference") or "sample")
    return {
        **payload,
        "reference": reference,
        "status": status,
        "event_action": str(payload.get("event_action") or "note_mutate"),
        "resource": str(payload.get("resource") or reference),
        "category": str(payload.get("category") or "data_access"),
        "capability": "audit",
        "channel": "mcp",
    }


def enqueue(item: Dict[str, Any]) -> Dict[str, Any]:
    job = {**item, "processed": False}
    _QUEUE.append(job)
    return job


def process_queue() -> List[Dict[str, Any]]:
    processed: List[Dict[str, Any]] = []
    while _QUEUE:
        job = _QUEUE.pop(0)
        job["processed"] = True
        processed.append(job)
    return processed


def queue_snapshot() -> List[Dict[str, Any]]:
    return list(_QUEUE)
