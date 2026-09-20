"""The one live connector, and the settings the operator still owes.

Written by the factory WRITER role (codewhale exec)

one_live_connector: with SMTP_HOST set, a notice makes a real outbound round
trip to the relay. The drill below runs a local SMTP server on the loopback
interface and asserts the platform actually spoke to it, rather than
reporting a delivery it never made. Every other integration stays a stub.
"""

from __future__ import annotations

import os
import socket
import threading

import pytest
from fastapi.testclient import TestClient

from app.main import app

# Self-contained fixtures, deliberately not taken from conftest.py: that file
# belongs to the factory and is rewritten between rounds with the canonical
# bootstrap (STORAGE_PATH isolation + the offline socket guard) and no
# fixtures of its own. Sharing its names here is what took this suite red.
AUTH = {"Authorization": "Bearer " + os.environ.get("PLATFORM_TOKEN", "dev-local-token")}


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def auth():
    return dict(AUTH)


@pytest.fixture()
def storage_path(tmp_path, monkeypatch):
    """Point persistence at a scratch root for one test.

    notifications.outbox_dir() reads STORAGE_PATH per call, so patching the
    environment is enough; nothing is cached at import time.
    """
    monkeypatch.setenv("STORAGE_PATH", str(tmp_path))
    return tmp_path


class _FakeSmtp(threading.Thread):
    """A minimal SMTP responder on 127.0.0.1, recording what it was sent."""

    def __init__(self) -> None:
        super().__init__(daemon=True)
        self.messages: list = []
        self.commands: list = []
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.bind(("127.0.0.1", 0))
        self._sock.listen(1)
        self._sock.settimeout(10.0)
        self.port = self._sock.getsockname()[1]
        self._halt = False

    def run(self) -> None:
        try:
            conn, _addr = self._sock.accept()
        except OSError:
            return
        with conn:
            conn.sendall(b"220 fleetops-test ESMTP\r\n")
            buffer = b""
            in_data = False
            while not self._halt:
                try:
                    chunk = conn.recv(4096)
                except OSError:
                    break
                if not chunk:
                    break
                buffer += chunk
                while b"\r\n" in buffer:
                    line, buffer = buffer.split(b"\r\n", 1)
                    text = line.decode("utf-8", "replace")
                    if in_data:
                        if text == ".":
                            in_data = False
                            conn.sendall(b"250 queued\r\n")
                        else:
                            self.messages.append(text)
                        continue
                    self.commands.append(text)
                    verb = text.split(" ", 1)[0].upper()
                    if verb in ("EHLO", "HELO"):
                        conn.sendall(b"250-fleetops-test\r\n250 HELP\r\n")
                    elif verb in ("MAIL", "RCPT"):
                        conn.sendall(b"250 ok\r\n")
                    elif verb == "DATA":
                        in_data = True
                        conn.sendall(b"354 send data\r\n")
                    elif verb == "QUIT":
                        conn.sendall(b"221 bye\r\n")
                        return
                    else:
                        conn.sendall(b"250 ok\r\n")

    def stop(self) -> None:
        self._halt = True
        try:
            self._sock.close()
        except OSError:
            pass


@pytest.fixture()
def fake_smtp(monkeypatch):
    server = _FakeSmtp()
    server.start()
    monkeypatch.setenv("SMTP_HOST", "127.0.0.1")
    monkeypatch.setenv("SMTP_PORT", str(server.port))
    monkeypatch.setenv("SMTP_FROM", "backoffice@example.com")
    yield server
    server.stop()
    server.join(timeout=2)


def test_notice_makes_a_real_smtp_round_trip(fake_smtp):
    from app.notifications import queue_email

    record = queue_email(
        to="manager@example.com",
        subject="Maintenance due for V-100",
        body="Service due on 2026-09-20",
        reference="maint-1",
    )
    assert record["delivery"]["sent"] is True
    assert record["delivery"]["via"] == "smtp"
    for _ in range(50):
        if fake_smtp.messages:
            break
        threading.Event().wait(0.05)
    assert any("Maintenance due for V-100" in line for line in fake_smtp.messages), fake_smtp.commands


def test_delivery_is_refused_by_name_without_a_relay(monkeypatch):
    from app.notifications import NotificationError, deliver

    monkeypatch.delenv("SMTP_HOST", raising=False)
    with pytest.raises(NotificationError) as excinfo:
        deliver({"to": "a@example.com", "subject": "x", "body": "y"})
    assert "SMTP_HOST" in str(excinfo.value)


def test_notice_is_still_queued_when_no_relay_is_configured(monkeypatch, storage_path):
    from app.notifications import outbox_path, queue_email

    monkeypatch.delenv("SMTP_HOST", raising=False)
    record = queue_email(to="agent@example.com", subject="Deposit release due", reference="inv-9")
    assert record["delivery"] == {"sent": False, "reason": "no_relay_configured"}
    assert outbox_path().is_file()
    assert "Deposit release due" in outbox_path().read_text(encoding="utf-8")


def test_a_notice_without_an_addressee_is_refused():
    from app.notifications import NotificationError, queue_email

    with pytest.raises(NotificationError):
        queue_email(to="not-an-address", subject="x")


def test_no_default_currency_is_invented(monkeypatch):
    from app.settings import SettingMissing, currency, money_or_none

    monkeypatch.delenv("CURRENCY", raising=False)
    with pytest.raises(SettingMissing) as excinfo:
        currency()
    assert "CURRENCY" in str(excinfo.value)
    assert money_or_none(150.0) is None


def test_currency_is_used_when_the_operator_sets_it(monkeypatch):
    from app.settings import money_or_none

    monkeypatch.setenv("CURRENCY", "USD")
    assert money_or_none(150.0) == {"amount": 150.0, "currency": "USD"}


def test_tax_rate_is_refused_when_it_is_not_a_decimal(monkeypatch):
    from app.settings import SettingMissing, tax_rate

    monkeypatch.setenv("TAX_VAT_RATE", "twenty percent")
    with pytest.raises(SettingMissing):
        tax_rate("TAX_VAT_RATE")


def test_settings_route_reports_names_not_values(client, auth, monkeypatch):
    monkeypatch.setenv("CURRENCY", "EUR")
    resp = client.get("/v1/settings", headers=auth)
    assert resp.status_code == 200
    body = resp.json()
    assert body["money"]["CURRENCY"] == "EUR"
    assert "CURRENCY" in body["required_before_use"]


def test_settings_route_needs_a_token(client):
    assert client.get("/v1/settings").status_code == 401
