"""The console the platform serves reaches the platform, end to end.

A pilot is deployed and tested, so what the image serves has to work: every
route the console calls must answer against the booted product, the console
must drive more than one capability, the formulas it ships must be reachable
from what it drives, and an answer it shows must carry its authority label.

This is the product-level form of the factory's ``ui_end_to_end`` probe: same
questions, asked from the checkout rather than from the gate runner.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.money import SETTINGS as MONEY_SETTINGS

ROOT = Path(__file__).resolve().parents[1]
AUTH = {"Authorization": "Bearer " + os.environ.get("PLATFORM_TOKEN", "dev-local-token")}

#: Paths the probe may skip: routes that exist but answer nothing without
#: arguments the console supplies (they are exercised in the tests below).
_PATH_RE = re.compile(r"/v1/[A-Za-z0-9_/\-]+")


def _console_html() -> str:
    page = ROOT / "app" / "static" / "index.html"
    assert page.is_file(), "the platform serves no UI: app/static/index.html is missing"
    return page.read_text(encoding="utf-8")


def _declared_paths() -> set:
    spec = json.loads((ROOT / "openapi.json").read_text(encoding="utf-8"))
    return set((spec.get("paths") or {}).keys())


def test_console_calls_only_routes_the_platform_declares():
    declared = _declared_paths()
    called = sorted(set(_PATH_RE.findall(_console_html())))
    assert called, "the console calls no /v1 route"
    undeclared = [p for p in called if p not in declared]
    assert not undeclared, "console calls undeclared route(s): " + ", ".join(undeclared)


def test_every_route_the_console_calls_answers():
    with TestClient(app) as client:
        failures = []
        for path in sorted(set(_PATH_RE.findall(_console_html()))):
            if "{" in path:
                continue
            resp = client.get(path, headers=AUTH)
            if resp.status_code in (404, 500, 501, 502):
                failures.append(f"{path}: HTTP {resp.status_code}")
    assert not failures, "; ".join(failures)


def test_console_drives_more_than_one_capability():
    html = _console_html()
    capabilities = sorted(
        p.stem for p in (ROOT / "app" / "actions").glob("*.py") if p.stem != "__init__"
    )
    driven = [c for c in capabilities if f"/v1/{c}" in html]
    assert len(driven) >= 2, (
        "the console drives %d capability(ies): %s" % (len(driven), ", ".join(driven))
    )


def test_the_formulas_the_console_shows_are_reachable_from_what_it_drives():
    html = _console_html()
    assert "/v1/formulas/valuation" in html, "the console does not use the formula layer"
    handler = (ROOT / "app" / "actions" / "commercials_and_valuations.py").read_text(
        encoding="utf-8"
    )
    assert "formulas" in handler, "the capability the console drives does not use app/formulas.py"


def test_an_answer_the_console_shows_carries_its_authority_label():
    with TestClient(app) as client:
        resp = client.post(
            "/v1/formulas/valuation",
            headers=AUTH,
            json={
                "reference": "IPC-UI-1",
                "gross_value_aed": 25000,
                "retention_percent": 10,
                "vat_rate_percent": 5,
            },
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True, body
    valuation = body["valuation"]
    assert valuation["authority_label"], valuation
    assert valuation["authority"]["winner"]["value"] == valuation["certified_value_aed"]
    assert valuation["certified_value_aed"] == pytest.approx(23625.0)


def test_a_rate_the_operator_has_not_set_is_refused_by_name(monkeypatch):
    """The platform does not guess a tax rate: it names the missing setting."""
    for name in MONEY_SETTINGS:
        monkeypatch.delenv(name, raising=False)
    with TestClient(app) as client:
        resp = client.post(
            "/v1/formulas/valuation",
            headers=AUTH,
            json={"reference": "IPC-UI-2", "gross_value_aed": 1000},
        )
    body = resp.json()
    assert body["ok"] is False, body
    assert body["setting"] in MONEY_SETTINGS, body


def test_money_settings_endpoint_reports_the_deployment_truthfully(monkeypatch):
    monkeypatch.setenv("UAE_VAT_RATE_PERCENT", "5")
    monkeypatch.delenv("DEFAULT_RETENTION_PERCENT", raising=False)
    monkeypatch.delenv("PAYMENT_TERM_DAYS", raising=False)
    with TestClient(app) as client:
        body = client.get("/v1/settings/money", headers=AUTH).json()
    settings = body["settings"]
    assert settings["currency"] == "AED"
    assert settings["country"] == "AE"
    assert settings["settings"]["UAE_VAT_RATE_PERCENT"]["set"] is True
    assert settings["settings"]["DEFAULT_RETENTION_PERCENT"]["set"] is False
    assert settings["settings"]["PAYMENT_TERM_DAYS"]["value"] is None
