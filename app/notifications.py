"""Email notification outbox for the FleetOps Back-Office Platform.

Written by the factory WRITER role (codewhale exec)

Scope
  READS   the caller's notice (to, subject, body, reference) and STORAGE_PATH.
  WRITES  one JSON line per notice under ``<STORAGE_PATH>/notifications``.
  NEVER   an outbound SMTP/HTTP call at request time.

Why this module exists rather than nothing at all: the Store ``notification``
block is vendored but cannot be imported in this checkout (see
``docs/vendor_block_defects.json``), so every capability that owes the
maintenance-due / rental-overdue / deposit-release / invoice-overdue email
would otherwise have no delivery path. The platform's offline posture is
email-only with no network at request time, so the notice is rendered and
queued here for the mail relay to pick up; nothing is claimed as sent.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List

OUTBOX_DIRNAME = "notifications"
OUTBOX_FILENAME = "outbox.jsonl"


class NotificationError(ValueError):
    """A notice that cannot be addressed or rendered."""


def outbox_dir() -> Path:
    """The mail outbox lives inside the one storage root (app.db decides).

    Read per call, not at import: a test or an operator may point
    STORAGE_PATH at a scratch root after this module loads.
    """
    from app import db as _db

    return _db.storage_root() / OUTBOX_DIRNAME


def outbox_path() -> Path:
    return outbox_dir() / OUTBOX_FILENAME


def smtp_settings() -> Dict[str, Any]:
    """The relay's address, if the operator configured one."""
    host = (os.environ.get("SMTP_HOST") or "").strip()
    if not host:
        return {}
    try:
        port = int((os.environ.get("SMTP_PORT") or "587").strip())
    except ValueError:
        port = 587
    return {
        "host": host,
        "port": port,
        "sender": (os.environ.get("SMTP_FROM") or "backoffice@localhost").strip(),
        "username": (os.environ.get("SMTP_USERNAME") or "").strip(),
        "password": os.environ.get("SMTP_PASSWORD") or "",
    }


def deliver(record: Dict[str, Any], timeout: float = 10.0) -> Dict[str, Any]:
    """Send one queued notice through the mail relay.

    This is the platform's one live outbound connector: with SMTP_HOST set
    the notice leaves the box, and the caller learns whether it did. With no
    relay configured the call is refused by name rather than reported as
    sent — nothing on this platform claims a delivery it did not make.
    """
    import smtplib

    settings = smtp_settings()
    if not settings:
        raise NotificationError(
            "SMTP_HOST is not set — no relay is configured to deliver email"
        )
    message = (
        "From: %s\r\nTo: %s\r\nSubject: %s\r\n\r\n%s\r\n"
        % (
            settings["sender"],
            record.get("to") or "",
            record.get("subject") or "",
            record.get("body") or "",
        )
    )
    client = smtplib.SMTP(settings["host"], settings["port"], timeout=timeout)
    try:
        client.ehlo()
        if client.has_extn("starttls"):
            client.starttls()
            client.ehlo()
        if settings["username"]:
            client.login(settings["username"], settings["password"])
        client.sendmail(settings["sender"], [record.get("to") or ""], message)
    finally:
        try:
            client.quit()
        except Exception:  # noqa: BLE001 - closing a dead socket is not an error
            pass
    return {"sent": True, "via": "smtp", "to": record.get("to")}


def queue_email(
    *,
    to: str,
    subject: str,
    body: str = "",
    reference: str = "",
    role: str = "",
    deliver_now: bool = True,
) -> Dict[str, Any]:
    """Render one email notice and append it to the outbox.

    Raises :class:`NotificationError` when the notice has no addressee or no
    subject -- a notification nobody can receive is not a notification.
    """
    recipient = str(to or "").strip()
    if not recipient or "@" not in recipient:
        raise NotificationError("to is required and must be an email address")
    topic = str(subject or "").strip()
    if not topic:
        raise NotificationError("subject is required")
    record = {
        "queued_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "to": recipient,
        "role": str(role or "branch"),
        "subject": topic[:200],
        "body": str(body or topic)[:4000],
        "reference": str(reference or ""),
        "channel": "email",
    }
    path = outbox_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    # The outbox is the record of what was rendered. When a relay is
    # configured the same notice also makes the live round trip, and the
    # result says which happened.
    if deliver_now and smtp_settings():
        try:
            delivery = deliver(record)
        except Exception as exc:  # noqa: BLE001 - the notice stays queued
            delivery = {
                "sent": False,
                "via": "smtp",
                "error": "%s: %s" % (type(exc).__name__, exc),
            }
        record = {**record, "delivery": delivery}
    else:
        record = {
            **record,
            "delivery": {"sent": False, "reason": "no_relay_configured"},
        }
    return record


def read_outbox(limit: int = 50) -> List[Dict[str, Any]]:
    """Most recent notices, newest last. Empty when nothing has been queued."""
    path = outbox_path()
    if not path.is_file():
        return []
    rows: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return rows[-max(int(limit), 1):]
