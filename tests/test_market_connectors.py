"""Property-market connectors: offline mocks + pilot happy paths.

CI blocks non-loopback sockets (tests/conftest.py). Every live path is mocked
here. Pilot-marked tests exercise connector happy paths with fakes — they do
not open the internet.
"""

from __future__ import annotations

import json
import os

import pytest
from fastapi.testclient import TestClient

from app.connectors import apify_bayut, dld, dxb_data, market_status
from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer " + os.environ.get("PLATFORM_TOKEN", "dev-local-token")}


@pytest.fixture(autouse=True)
def _clear_market_env(monkeypatch):
    for key in ("DXB_DATA_MCP_URL", "DLD_QUERY_URL", "APIFY_TOKEN"):
        monkeypatch.delenv(key, raising=False)


def test_market_status_not_configured_without_env():
    body = market_status()
    assert set(body["not_configured"]) == {"dxb_data", "dld", "apify_bayut"}
    assert body["configured"] == []
    assert "cite-or-refuse" in body["cite_or_refuse"].lower() or "cite_or_refuse" in body["cite_or_refuse"]


def test_connectors_refuse_when_not_configured():
    snap = dxb_data.area_snapshot("Business Bay")
    assert snap["ok"] is False
    assert snap["status"] == "not_configured"
    assert "DXB_DATA_MCP_URL" in snap["error"]

    stats = dld.sales_stats("Marina")
    assert stats["ok"] is False
    assert stats["status"] == "not_configured"
    assert "DLD_QUERY_URL" in stats["error"]

    harvest = apify_bayut.harvest_buy()
    assert harvest["ok"] is False
    assert harvest["status"] == "not_configured"
    assert "APIFY_TOKEN" in harvest["error"]


def test_market_routes_require_auth():
    resp = client.get("/v1/market/status")
    assert resp.status_code == 401
    resp = client.post("/v1/market/dxb/snapshot", json={"area": "Business Bay"})
    assert resp.status_code == 401
    resp = client.post("/v1/market/dld/sales_stats", json={"area": "Marina"})
    assert resp.status_code == 401
    resp = client.post("/v1/market/apify/bayut_buy", json={})
    assert resp.status_code == 401


def test_market_routes_not_configured_when_env_missing():
    status = client.get("/v1/market/status", headers=AUTH)
    assert status.status_code == 200
    body = status.json()
    assert body["ok"] is True
    assert set(body["not_configured"]) == {"dxb_data", "dld", "apify_bayut"}

    snap = client.post(
        "/v1/market/dxb/snapshot",
        json={"area": "Business Bay"},
        headers=AUTH,
    )
    assert snap.status_code == 200
    assert snap.json()["status"] == "not_configured"

    sales = client.post(
        "/v1/market/dld/sales_stats",
        json={"area": "Marina"},
        headers=AUTH,
    )
    assert sales.status_code == 200
    assert sales.json()["status"] == "not_configured"

    buy = client.post("/v1/market/apify/bayut_buy", json={}, headers=AUTH)
    assert buy.status_code == 200
    assert buy.json()["status"] == "not_configured"


def test_capabilities_lists_market_sources():
    resp = client.get("/v1/capabilities")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["items"], list)
    assert "market_sources" in body
    assert "market_http" in body
    assert body["market_http"]["dxb_snapshot"] == "POST /v1/market/dxb/snapshot"
    assert body["market_http"]["apify_bayut_buy"] == "POST /v1/market/apify/bayut_buy"


def test_dxb_area_alias_jbr_to_marsa_dubai():
    alias = dxb_data.resolve_area("JBR")
    assert alias["resolved"] == "Marsa Dubai"
    assert alias["alias_applied"] == "jbr"
    marina = dxb_data.resolve_area("Dubai Marina")
    assert marina["resolved"] == "Marsa Dubai"


def test_dxb_snapshot_mocked(monkeypatch):
    monkeypatch.setenv("DXB_DATA_MCP_URL", "https://dxbdata.io/mcp")

    def fake_request(url, *, method="GET", body=None, headers=None, timeout=30.0, query=None):
        assert "dxbdata.io" in url
        assert body["method"] == "tools/call"
        assert body["params"]["name"] == "area_snapshot"
        assert body["params"]["arguments"]["area"] == "Marsa Dubai"
        payload = {
            "area": "Marsa Dubai",
            "property_type": "Flat",
            "sample_size": 10,
            "median_price_aed": 2500000,
            "source": "Dubai Land Department (official transactions)",
        }
        rpc = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"content": [{"type": "text", "text": json.dumps(payload)}]},
        }
        return 200, rpc, {"content-type": "application/json"}

    monkeypatch.setattr("app.connectors.dxb_data.json_request", fake_request)
    out = dxb_data.area_snapshot("JBR")
    assert out["ok"] is True
    assert out["data"]["median_price_aed"] == 2500000
    assert out["area"]["resolved"] == "Marsa Dubai"


def test_dxb_compare_and_yield_routes_mocked(monkeypatch):
    monkeypatch.setenv("DXB_DATA_MCP_URL", "https://dxbdata.io/mcp")

    def fake_request(url, *, method="GET", body=None, headers=None, timeout=30.0, query=None):
        tool = body["params"]["name"]
        if tool == "rental_yield":
            data = {"area": "Business Bay", "gross_rental_yield_pct": 4.9}
        else:
            data = {"areas": body["params"]["arguments"]["areas"], "ok": True}
        rpc = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"content": [{"type": "text", "text": json.dumps(data)}]},
        }
        return 200, rpc, {"content-type": "application/json"}

    monkeypatch.setattr("app.connectors.dxb_data.json_request", fake_request)

    y = client.post(
        "/v1/market/dxb/yield",
        json={"area": "Business Bay"},
        headers=AUTH,
    )
    assert y.status_code == 200
    assert y.json()["ok"] is True
    assert y.json()["data"]["gross_rental_yield_pct"] == 4.9

    c = client.post(
        "/v1/market/dxb/compare",
        json={"areas": ["Business Bay", "Palm Jumeirah"]},
        headers=AUTH,
    )
    assert c.status_code == 200
    assert c.json()["ok"] is True


def test_dld_sales_stats_mocked(monkeypatch):
    monkeypatch.setenv("DLD_QUERY_URL", "https://offerbrief.com/api")

    def fake_request(url, *, method="GET", body=None, headers=None, timeout=30.0, query=None):
        assert url.endswith("/query")
        assert query["area"] == "Marina"
        assert query["type"] == "sales"
        assert query["metric"] == "stats"
        return (
            200,
            {
                "area": "Marsa Dubai",
                "median_price": 3050000,
                "count": 2157,
                "match_type": "community_alias",
                "type": "sales",
            },
            {"content-type": "application/json"},
        )

    monkeypatch.setattr("app.connectors.dld.json_request", fake_request)
    out = dld.sales_stats("Marina", property_type="apartment")
    assert out["ok"] is True
    assert out["data"]["median_price"] == 3050000
    assert out["data"]["area"] == "Marsa Dubai"

    resp = client.post(
        "/v1/market/dld/sales_stats",
        json={"area": "Marina", "property_type": "apartment"},
        headers=AUTH,
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_dld_rejects_bad_enums(monkeypatch):
    monkeypatch.setenv("DLD_QUERY_URL", "https://offerbrief.com/api")
    bad = dld.query_dld("Marina", type="leases")
    assert bad["ok"] is False
    assert "sales" in bad["error"]


def test_apify_bayut_harvest_mocked(monkeypatch):
    monkeypatch.setenv("APIFY_TOKEN", "test-token")

    def fake_run(actor_input):
        assert actor_input["maxItems"] == 10
        assert actor_input["startUrls"][0]["url"].startswith("https://www.bayut.com/")
        return {
            "data": {
                "id": "run-1",
                "defaultDatasetId": "ds-1",
                "status": "SUCCEEDED",
            }
        }

    def fake_items(dataset_id):
        assert dataset_id == "ds-1"
        return [
            {"id": 1, "price": 2_000_000, "location": "Marina"},
            {"id": 2, "price": 2_100_000, "location": "JBR"},
            {"id": 3, "price": 2_200_000, "location": "JLT"},
        ]

    out = apify_bayut.harvest_buy(
        start_urls=["https://www.bayut.com/for-sale/apartments/dubai/dubai-marina/"],
        max_items=10,
        _transport_run=fake_run,
        _transport_items=fake_items,
    )
    assert out["ok"] is True
    assert out["count"] == 3
    assert out["capped_at"] == 10
    assert out["actor"] == "memo23/apify-bayut-scraper"


def test_apify_caps_max_items(monkeypatch):
    monkeypatch.setenv("APIFY_TOKEN", "test-token")

    def fake_run(actor_input):
        assert actor_input["maxItems"] == apify_bayut.HARD_MAX_ITEMS
        return {"data": {"id": "r", "defaultDatasetId": "d", "status": "SUCCEEDED"}}

    def fake_items(_dataset_id):
        return [{"id": i} for i in range(100)]

    out = apify_bayut.harvest_buy(
        max_items=999,
        _transport_run=fake_run,
        _transport_items=fake_items,
    )
    assert out["ok"] is True
    assert out["capped_at"] == apify_bayut.HARD_MAX_ITEMS
    assert out["count"] == apify_bayut.HARD_MAX_ITEMS


def test_apify_refuses_non_bayut_url(monkeypatch):
    monkeypatch.setenv("APIFY_TOKEN", "test-token")
    out = apify_bayut.harvest_buy(start_urls=["https://example.com/for-sale"])
    assert out["ok"] is False
    assert "Bayut" in out["error"]


@pytest.mark.pilot
def test_pilot_dxb_connector_happy_path(monkeypatch):
    """Pilot: connector happy path with transport mock (no live egress)."""
    monkeypatch.setenv("DXB_DATA_MCP_URL", "https://dxbdata.io/mcp")

    def fake_request(url, *, method="GET", body=None, headers=None, timeout=30.0, query=None):
        data = {
            "area": "Business Bay",
            "median_price_aed": 1762250,
            "source": "Dubai Land Department (official transactions)",
        }
        rpc = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"content": [{"type": "text", "text": json.dumps(data)}]},
        }
        return 200, rpc, {"content-type": "application/json"}

    monkeypatch.setattr("app.connectors.dxb_data.json_request", fake_request)
    out = dxb_data.area_snapshot("Business Bay")
    assert out["ok"] and out["data"]["median_price_aed"] == 1762250


@pytest.mark.pilot
def test_pilot_dld_connector_happy_path(monkeypatch):
    monkeypatch.setenv("DLD_QUERY_URL", "https://offerbrief.com/api")

    def fake_request(url, *, method="GET", body=None, headers=None, timeout=30.0, query=None):
        return 200, {"area": "Marsa Dubai", "median_price": 3050000, "count": 100}, {}

    monkeypatch.setattr("app.connectors.dld.json_request", fake_request)
    out = dld.query_dld("Marina", type="sales", metric="stats")
    assert out["ok"] and out["data"]["count"] == 100


@pytest.mark.pilot
def test_pilot_apify_connector_happy_path(monkeypatch):
    monkeypatch.setenv("APIFY_TOKEN", "pilot-token")
    out = apify_bayut.harvest_buy(
        max_items=5,
        _transport_run=lambda _inp: {
            "data": {"id": "run", "defaultDatasetId": "ds", "status": "SUCCEEDED"}
        },
        _transport_items=lambda _ds: [{"price": 1}],
    )
    assert out["ok"] and out["count"] == 1
