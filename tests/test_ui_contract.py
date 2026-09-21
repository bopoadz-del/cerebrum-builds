"""Every route the console calls answers. A facade fails here."""

from __future__ import annotations

from tests.callops_helpers import (  # noqa: F401 - client is a fixture
    AUTH, client, payload_for,
)

#: The build's own kernel and schema surfaces. They answer without a bearer
#: token on purpose: they describe this tree and its contract -- the roster,
#: the blocks, the gates, the provenance -- and never one tenant's records, so
#: there is no tenant to resolve them under. Every route that touches a
#: record is authenticated, and the anonymous probes below prove it.
PUBLIC_SURFACES = (
    "/v1/jobs",
    "/v1/catalog",
    "/v1/inventory",
    "/v1/capabilities",
    "/v1/gates",
    "/v1/provenance",
)


def _is_public(path: str) -> bool:
    return path.split("?")[0] in PUBLIC_SURFACES


CONSOLE_ROUTES = [
    ("GET", "/v1/auth/whoami", None),
    ("GET", "/v1/capabilities", None),
    ("GET", "/v1/connectors", None),
    ("GET", "/v1/dial-queue", None),
    ("GET", "/v1/dashboard", None),
    ("GET", "/v1/formulas", None),
    ("GET", "/v1/blocks", None),
    ("GET", "/v1/authority", None),
    ("GET", "/v1/settings", None),
    ("GET", "/v1/rag/corpus", None),
    ("GET", "/v1/rag/ingest", None),
    ("GET", "/v1/rag/ground", None),
    ("GET", "/v1/rag/query?question=starting+price%3F", None),
    ("GET", "/v1/leads/import", None),
    ("GET", "/v1/ledger/verify", None),
    ("POST", "/v1/ledger/verify", {"call_sid": "CAui00000000000000000000000001"}),
    ("POST", "/v1/rag/ingest", {"text": "Console sheet: one bedroom from AED 1,250,000."}),
    ("POST", "/v1/rag/ground", {"project_tag": "az-zahra", "question": "price?"}),
    ("POST", "/v1/formulas/calls_remaining", {"daily_cap": 10, "attempted_today": 2}),
    ("POST", "/v1/formulas/retry_backoff", {"attempt": 1}),
    ("POST", "/v1/leads/import", {"text": "name,phone\nUI Lead,+971500001111\n", "campaign": "ui"}),
    ("POST", "/v1/qualification_and_broker_summary", payload_for("qualification_and_broker_summary")),
    ("POST", "/v1/warm_transfer", payload_for("warm_transfer")),
    ("POST", "/v1/mcp", {"method": "tools/list", "params": {}}),
]


def test_every_console_route_answers_for_a_tenant(client):
    client.post("/v1/rag/ingest", json={"text": "Az Zahra price from AED 1,250,000.", "project_tag": "az-zahra"}, headers=AUTH)
    for method, path, body in CONSOLE_ROUTES:
        response = (
            client.get(path, headers=AUTH)
            if method == "GET"
            else client.post(path, json=body, headers=AUTH)
        )
        assert response.status_code < 500, f"{method} {path} -> {response.status_code}: {response.text[:200]}"
        assert response.status_code in (200, 404, 409), f"{method} {path} -> {response.status_code}"
        if response.status_code == 200:
            assert "authority" in response.json() or path.endswith("whoami")


def test_every_console_route_refuses_an_anonymous_caller(client):
    for method, path, body in CONSOLE_ROUTES:
        if _is_public(path):
            continue  # the kernel/schema surfaces carry no tenant data
        response = (
            client.get(path)
            if method == "GET"
            else client.post(path, json=body or {})
        )
        assert response.status_code == 401, f"{method} {path} answered {response.status_code}"


def test_the_console_shows_the_authority_layer_on_every_answer(client):
    dashboard = client.get("/v1/dashboard", headers=AUTH).json()
    assert dashboard["authority"]["precedence"] == "precedence.v1"
    assert dashboard["authority"]["layer"] in ("certified", "documents", "formulas", "procedures")
    formula = client.post("/v1/formulas/calls_remaining", json={"daily_cap": 5, "attempted_today": 1}, headers=AUTH).json()
    assert formula["authority"]["layer"] == "formulas"
    authority = client.get("/v1/authority", headers=AUTH).json()
    assert [layer["layer"] for layer in authority["precedence"]["layers"]] == [
        "certified",
        "documents",
        "formulas",
        "procedures",
    ]


def test_no_v1_route_is_open_without_a_token(client):
    """The doctrine holds for every route that carries a record.

    The kernel surfaces (see PUBLIC_SURFACES) are the documented exception:
    they answer the build's own description and read no tenant's row, and the
    anonymous probe of every other /v1 path is what keeps the exception from
    spreading.
    """
    public_checked = set()
    for route in client.get("/openapi.json", headers=AUTH).json()["paths"]:
        if not route.startswith("/v1/") or "{" in route:
            continue
        if _is_public(route):
            public_checked.add(route)
            continue
        method = "get" if "post" not in client.get("/openapi.json").json()["paths"][route] else "post"
        response = client.get(route, headers=None) if method == "get" else client.post(route, json={})
        assert response.status_code == 401, f"{method.upper()} {route} answered {response.status_code}"
    assert public_checked == set(PUBLIC_SURFACES), (
        "the public kernel surfaces changed: " + repr(sorted(public_checked))
    )


def test_the_api_description_lives_outside_v1(client):
    assert client.get("/openapi.json").status_code == 200
    # /v1 is authenticated without exception, so the mirror on that path is
    # not a second, open way in.
    assert client.get("/v1/openapi.json").status_code == 401
    assert client.get("/v1/openapi.json", headers=AUTH).status_code == 404


def test_every_domain_route_refuses_a_malformed_body_without_a_500(client):
    """Malformed input is a refusal with a reason, on every path."""
    payloads = [
        (b"{not json", "application/json"),
        (b"[1, 2]", "application/json"),
        (b'"a string"', "application/json"),
        (b"3", "application/json"),
        (b'{"a": ' + b"[" * 2000 + b"]" * 2000 + b"}", "application/json"),
    ]
    for path in (
        "/v1/rag/ingest",
        "/v1/rag/query",
        "/v1/rag/ground",
        "/v1/leads/import",
        "/v1/connectors/webhook/probe",
        "/v1/ledger/verify",
        "/v1/formulas/calls_remaining",
        "/v1/mcp",
        "/v1/notification",
    ):
        for raw, content_type in payloads:
            response = client.post(path, content=raw, headers={**AUTH, "Content-Type": content_type})
            assert response.status_code != 500, (path, raw[:20], response.text[:200])
            assert 400 <= response.status_code < 500, (path, response.status_code)


def test_bad_query_parameters_are_refused_not_raised(client):
    assert client.get("/v1/dial-queue?attempted_today=abc", headers=AUTH).status_code == 422
    assert client.get("/v1/dial-queue?attempted_today=-5", headers=AUTH).status_code == 422
    assert client.get("/v1/dial-queue?attempted_today=7", headers=AUTH).status_code == 200


def test_an_oversized_body_is_refused(client):
    body = {"text": "x" * (600 * 1024)}
    response = client.post("/v1/rag/ingest", json=body, headers=AUTH)
    assert response.status_code == 422
    assert "too large" in response.json()["detail"]
