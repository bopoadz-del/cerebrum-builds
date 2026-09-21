"""Boot, health, metrics and the console the platform serves."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi.testclient import TestClient

from app.health import evaluate_health
from app.main import app
from app.observe import REQUEST_ID_HEADER, JsonFormatter, strip_emoji
from tests.callops_helpers import client  # noqa: F401 - the client fixture


def test_health_is_fail_closed_when_the_disk_is_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("STORAGE_PATH", str(tmp_path / "not-there"))
    code, body = evaluate_health()
    assert code == 503
    assert body["ok"] is False
    names = {item["name"]: item for item in body["checks"]}
    assert names["persistent_disk"]["ok"] is False


def test_health_is_fail_closed_when_migrations_are_missing(monkeypatch, tmp_path):
    empty = tmp_path / "empty-disk"
    empty.mkdir()
    monkeypatch.setenv("STORAGE_PATH", str(empty))
    code, body = evaluate_health()
    assert code == 503
    names = {item["name"]: item for item in body["checks"]}
    assert names["database"]["ok"] is False or names["migrations"]["ok"] is False


def test_health_is_200_only_when_disk_db_and_head_agree(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["status"] == "ok"
    assert {"process", "persistent_disk", "database", "migrations"} <= {
        item["name"] for item in body["checks"]
    }
    assert all(item["ok"] for item in body["checks"])


def test_metrics_reports_counts_and_latency(client):
    client.get("/health")
    response = client.get("/metrics")
    assert response.status_code == 200
    text = response.text.lower()
    assert "http_requests_total" in text
    assert "duration_seconds" in text


def test_console_is_served_and_calls_the_api(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    html = response.text
    # The console must drive the platform, not merely describe it.
    for route in (
        "/v1/auth/whoami",
        "/v1/capabilities",
        "/v1/rag/ingest",
        "/v1/rag/ground",
        "/v1/formulas/",
        "/v1/dashboard",
        "/v1/connectors",
        "/v1/leads/import",
        "/v1/dial-queue",
    ):
        assert route in html, route


def test_request_log_carries_the_correlation_id(client, caplog):
    import logging

    caplog.set_level(logging.INFO)
    response = client.get("/health", headers={REQUEST_ID_HEADER: "callops-test"})
    assert response.headers.get(REQUEST_ID_HEADER) == "callops-test"
    formatter = JsonFormatter()
    assert strip_emoji("ok") == "ok"
    record = logging.LogRecord("callops", logging.INFO, __file__, 0, "ready", (), None)
    assert "ready" in formatter.format(record)
