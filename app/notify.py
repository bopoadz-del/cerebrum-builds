"""Outbound guest messaging: the platform's one live delivery path.

Written by the factory WRITER role (codewhale exec)

Guest engagement is worthless if the message never leaves the box, so delivery
is real: SMTP when the operator configures a relay, an HTTP webhook when they
configure one. With neither configured the send is REFUSED by name -- the
capability reports ``delivery: not_configured`` and the reason, rather than
answering "sent" over a message that went nowhere.

Settings (all optional, all operator-owned):
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM, SMTP_STARTTLS
    GUEST_WEBHOOK_URL
"""

from __future__ import annotations

import json
import os
import smtplib
from email.message import EmailMessage
from typing import Any, Dict, Optional

from app.security import check_outbound_url, clean_text

DEFAULT_FROM = "front-desk@localhost"


def smtp_configured() -> bool:
    return bool((os.environ.get("SMTP_HOST") or "").strip())


def webhook_configured() -> bool:
    return bool((os.environ.get("GUEST_WEBHOOK_URL") or "").strip())


def _smtp_send(to: str, subject: str, body: str) -> Dict[str, Any]:
    host = (os.environ.get("SMTP_HOST") or "").strip()
    port = int((os.environ.get("SMTP_PORT") or "587").strip() or 587)
    user = (os.environ.get("SMTP_USER") or "").strip()
    password = (os.environ.get("SMTP_PASS") or "").strip()
    sender = (os.environ.get("SMTP_FROM") or "").strip() or DEFAULT_FROM
    message = EmailMessage()
    message["From"] = sender
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    with smtplib.SMTP(host, port, timeout=10) as client:
        if (os.environ.get("SMTP_STARTTLS") or "1").strip() not in ("0", "false", "no"):
            try:
                client.starttls()
            except smtplib.SMTPNotSupportedError:
                pass
        if user:
            client.login(user, password)
        client.send_message(message)
    return {"transport": "smtp", "host": host, "port": port, "to": to, "accepted": True}


def _webhook_send(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    import urllib.request

    safe = check_outbound_url(url, field="GUEST_WEBHOOK_URL")
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        safe, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        status = getattr(response, "status", 200)
    return {"transport": "webhook", "url": safe, "status": int(status), "accepted": True}


def deliver(
    *,
    to: Any,
    subject: Any,
    body: Any,
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Deliver a guest message, or refuse by name when nothing is configured."""
    recipient = clean_text(to, field="to", limit=320)
    if "@" not in recipient:
        return {
            "ok": False,
            "delivery": "refused",
            "reason": "recipient_invalid",
            "error": "a recipient email address is required to deliver a guest message",
        }
    text_subject = clean_text(subject, field="subject", limit=200) or "Your stay"
    text_body = clean_text(body, field="body", limit=4000)
    if not text_body:
        return {
            "ok": False,
            "delivery": "refused",
            "reason": "empty_message",
            "error": "message body is empty",
        }
    if smtp_configured():
        try:
            result = _smtp_send(recipient, text_subject, text_body)
        except Exception as exc:  # noqa: BLE001 - report the transport failure
            return {
                "ok": False,
                "delivery": "failed",
                "reason": "smtp_error",
                "error": f"{type(exc).__name__}: {exc}"[:200],
            }
        return {"ok": True, "delivery": "sent", **result}
    if webhook_configured():
        url = (os.environ.get("GUEST_WEBHOOK_URL") or "").strip()
        try:
            result = _webhook_send(
                url,
                {
                    "to": recipient,
                    "subject": text_subject,
                    "message": text_body,
                    "payload": payload or {},
                },
            )
        except Exception as exc:  # noqa: BLE001 - report the transport failure
            return {
                "ok": False,
                "delivery": "failed",
                "reason": "webhook_error",
                "error": f"{type(exc).__name__}: {exc}"[:200],
            }
        return {"ok": True, "delivery": "sent", **result}
    return {
        "ok": False,
        "delivery": "not_configured",
        "reason": "no_egress_configured",
        "error": (
            "no outbound channel is configured: set SMTP_HOST (and SMTP_PORT/ "
            "SMTP_USER/SMTP_PASS) or GUEST_WEBHOOK_URL to deliver guest messages"
        ),
    }
