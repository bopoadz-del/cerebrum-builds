"""Offline notification delivery for the FinOps Central platform.

Written by the factory WRITER role (codewhale exec)

The platform is offline by design (no SMTP, no webhook, no network). This
module is the platform's own delivery path: it resolves the recipients for
a department, renders the message, and appends a durable delivery record to the
outbox under ``STORAGE_PATH``. Nothing leaves the machine.

It exists because the vendored ``notification`` block shipped in this
checkout does not import (``vendor/cerebrum/blocks/notification.py`` has a
bare ``try:`` at line 230 -- a syntax error in sealed vendor source). The
capability handlers still call ``execute("notification", ...)`` so the
block binding is real and observable; when that call cannot load, the
handler records the block as unavailable and this module performs the
delivery, naming which path ran in the response envelope.
"""

from __future__ import annotations

import json
import re
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

VALID_CHANNELS = ("mcp", "email", "inbox", "outbox", "department-mailbox")


def outbox_dir() -> Path:
    root = Path(os.getenv("STORAGE_PATH", "./data"))
    path = root / "outbox"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _recipients(record: Dict[str, Any], department: str) -> List[str]:
    who = (
        record.get("approver_email")
        or record.get("contact_email")
        or record.get("budget_owner")
    )
    if isinstance(who, str) and who.strip() and "@" in who:
        return [who.strip()]
    slug = re.sub(r"[^a-z0-9-]+", "-", str(department or "finance").lower()).strip("-")
    return [f"{slug or 'finance'}@finops.local"]


def deliver(
    *,
    department: str,
    subject: str,
    message: str,
    channel: str = "mcp",
    record: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Record one outbound message and return its delivery receipt."""
    record = dict(record or {})
    used_channel = channel if channel in VALID_CHANNELS else "mcp"
    receipt = {
        "channel": used_channel,
        "department": str(department or "finance"),
        "recipients": _recipients(record, str(department or "")),
        "subject": str(subject or "finops notification")[:200],
        "message": str(message or "")[:2000],
        "delivered_at": datetime.now(timezone.utc).isoformat(),
        "transport": "local_outbox",
        "network": False,
    }
    path = outbox_dir() / "notifications.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(receipt, sort_keys=True) + "\n")
    receipt["outbox"] = str(path)
    return receipt


def outbox(*, limit: int = 50) -> List[Dict[str, Any]]:
    """The most recent delivery receipts, newest last."""
    path = outbox_dir() / "notifications.jsonl"
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()[-max(1, int(limit)):]
    out: List[Dict[str, Any]] = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out
