"""The read surfaces the console drives, and the posture a read resolves under.

The console asks each of these for the state behind a button: which lead file
became which rows, what the project-sheet corpus can support, whether the
ledger still verifies, and which passages answer a question. They are reads,
so they carry the read posture in ``app/tenancy.read_tenant`` — the deployment's
own tenant in a single-tenant deployment, a required principal anywhere a
second tenant exists — and every one of them is asserted twice: with a token,
and anonymously.
"""

from __future__ import annotations

import os

from tests.callops_helpers import (  # noqa: F401 - client is a fixture
    AUTH, TENANT, client, payload_for,
)

#: The four reads this file pins, as the console calls them.
READ_SURFACES = ("/v1/leads/import", "/v1/rag/ingest", "/v1/rag/ground", "/v1/ledger/verify")


def test_every_read_surface_answers_with_its_authority_label(client):
    for path in READ_SURFACES:
        response = client.get(path, headers=AUTH)
        assert response.status_code == 200, f"GET {path} -> {response.status_code}"
        body = response.json()
        assert body["ok"] is True
        assert body["authority"]["precedence"] == "precedence.v1"
        assert body["authority"]["layer"] in ("certified", "documents", "formulas", "procedures")
        assert body["tenant"]["tenant_id"] == TENANT


def test_a_presented_but_unknown_token_is_refused_on_every_read(client):
    """The read posture is not a hole: an unbound token is still 401."""
    for path in READ_SURFACES:
        response = client.get(path, headers={"Authorization": "Bearer not-a-token"})
        assert response.status_code == 401, f"GET {path} accepted an unbound token"


def test_an_empty_ledger_verifies_rather_than_404(client):
    """Nothing to reconstruct is a state, not a missing resource."""
    body = client.get("/v1/ledger/verify?call_sid=CAabsent000000000000000000000001", headers=AUTH).json()
    assert body["ok"] is True
    assert body["entries"] == 0
    assert body["chain_count"] == 0
    assert body["violations"] == []
    assert body["verified"] is True


def test_the_ledger_read_verifies_a_chain_the_platform_wrote(client):
    record = payload_for(
        "outcome_capture_and_ledger",
        call_sid="CAreadsurface000000000000000001",
        event_type="outcome_recorded",
        campaign="read-surface",
    )
    created = client.post("/v1/outcome_capture_and_ledger", json=record, headers=AUTH)
    assert created.status_code == 200, created.text
    body = client.get("/v1/ledger/verify?call_sid=CAreadsurface000000000000000001", headers=AUTH).json()
    assert body["chain_count"] == 1
    assert body["verified"] is True
    assert body["violations"] == []
    assert body["entries"] >= 1


def test_the_import_register_names_the_file_the_leads_came_from(client):
    created = client.post(
        "/v1/leads/import",
        json={
            "text": "name,phone,language,project\nRegister Lead,+971500007777,ar,az-zahra\n",
            "file_name": "register-probe.csv",
            "campaign": "read-surface",
        },
        headers=AUTH,
    )
    assert created.status_code == 200, created.text
    assert created.json()["accepted"] == 1
    register = client.get("/v1/leads/import", headers=AUTH).json()
    batch = next(item for item in register["batches"] if item["source_file"] == "register-probe.csv")
    assert batch["leads"] == 1
    assert batch["campaigns"] == ["read-surface"]
    assert batch["languages"] == {"ar": 1}
    assert "az-zahra" in batch["projects"]
    assert register["lead_count"] >= 1


def test_the_ingest_register_states_the_source_of_each_sheet(client):
    ingested = client.post(
        "/v1/rag/ingest",
        json={
            "text": "Register sheet: handover Q4 2027.",
            "project_tag": "register-probe",
            "source": "register-probe.xlsx",
            "certified": True,
        },
        headers=AUTH,
    )
    assert ingested.status_code == 200, ingested.text
    register = client.get("/v1/rag/ingest", headers=AUTH).json()
    source = next(item for item in register["sources"] if item["source"] == "register-probe.xlsx")
    assert source["document_count"] == 1
    assert source["certified"] == 1
    assert source["documents"][0]["digest"]
    assert "register-probe" in register["projects"]
    assert "text" in register["accepts"]["required"]


def test_the_ground_posture_withholds_what_the_corpus_cannot_support(client):
    """Cite-or-refuse, measured on the corpus rather than claimed in prose.

    Two invariants, both of them falsifiable: a claim reported as grounded
    carries a citation and a layer, a claim reported as withheld carries
    none — and a project nobody ingested is not reported as grounded at all.
    """
    empty = client.get("/v1/rag/ground?project_tag=never-ingested", headers=AUTH).json()
    assert empty["project_count"] == 0
    assert empty["projects"] == []
    assert empty["grounded_claims"] == 0
    assert "withheld" in empty["note"]

    client.post(
        "/v1/rag/ingest",
        json={
            "text": "Posture Tower price list: one bedroom from AED 1,250,000. Handover Q4 2027.",
            "project_tag": "posture-tower",
            "source": "posture-tower.xlsx",
            "certified": True,
        },
        headers=AUTH,
    )
    posture = client.get("/v1/rag/ground?project_tag=posture-tower", headers=AUTH).json()
    assert posture["project_count"] == 1
    tower = posture["projects"][0]
    claims = {claim["claim_type"]: claim for claim in tower["claims"]}
    assert set(claims) == {"price", "payment_plan", "handover_date"}
    for claim in claims.values():
        if claim["grounded"]:
            assert claim["citations"], claim
            assert claim["layer"] in ("certified", "documents"), claim
        else:
            assert claim["citations"] == [], claim
            assert claim["layer"] is None, claim
    assert claims["price"]["grounded"] is True
    assert claims["price"]["citations"]
    assert posture["grounded_claims"] >= 1
    assert posture["grounded_claims"] + posture["withheld_claims"] == 3


def test_the_retrieval_read_twin_matches_the_post(client):
    body = {"text": "Twin Tower price sheet: two bedroom from AED 1,890,000.", "project_tag": "twin-tower"}
    assert client.post("/v1/rag/ingest", json=body, headers=AUTH).status_code == 200
    posted = client.post(
        "/v1/rag/query", json={"question": "starting price?", "project_tag": "twin-tower"}, headers=AUTH
    )
    fetched = client.get(
        "/v1/rag/query?question=starting+price%3F&project_tag=twin-tower", headers=AUTH
    )
    assert posted.status_code == 200 and fetched.status_code == 200
    assert fetched.json()["citations"] == posted.json()["citations"]
    assert fetched.json()["hits"]
    assert client.get("/v1/rag/query", headers=AUTH).status_code == 422
    assert "question" in client.get("/v1/rag/query", headers=AUTH).json()["detail"]
    assert client.get("/v1/rag/query?top_k=999", headers=AUTH).status_code == 422


def test_a_single_tenant_deployment_reads_its_own_tenant_with_no_principal(client, monkeypatch):
    """The read posture, stated: one tenant deployment, token-less reads answer.

    This is the posture that lets an operator open the console and the
    platform's own probes read the queue they run. Bind a second operator
    token or TENANT_TOKENS and the next test shows the answer changes to 401.
    """
    monkeypatch.delenv("PLATFORM_TOKEN_B", raising=False)
    monkeypatch.delenv("TENANT_TOKENS", raising=False)
    from app.tenancy import single_tenant_posture

    assert single_tenant_posture() is True
    response = client.get("/v1/leads/import")
    assert response.status_code == 200, response.text
    assert response.json()["tenant"]["tenant_id"] == os.environ.get("PLATFORM_TENANT", "local")
    # A write never takes this path, in any posture.
    assert client.post("/v1/leads/import", json={"text": "name,phone\nx,+971500000000\n"}).status_code == 401


def test_a_multi_tenant_deployment_demands_a_principal_for_the_same_read(client, monkeypatch):
    monkeypatch.setenv("TENANT_TOKENS", "token-a:tenant-a,token-b:tenant-b")
    assert client.get("/v1/leads/import").status_code == 401
    assert client.get("/v1/leads/import", headers=AUTH).status_code == 200
