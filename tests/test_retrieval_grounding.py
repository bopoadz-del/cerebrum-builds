"""Cite-or-refuse: a claim is quoted from a sheet, or withheld."""

from __future__ import annotations

import uuid

from tests.callops_helpers import (  # noqa: F401 - client is a fixture
    AUTH, OTHER_AUTH, client, payload_for,
)

SHEET = (
    "Az Zahra Tower price list.\n\n"
    "One bedroom apartments start from AED 1,250,000. Two bedroom from AED 1,890,000.\n\n"
    "Payment plan: 20% down payment and 60 monthly instalments.\n\n"
    "Handover Q4 2027.\n"
)


def _ingest(client, **overrides):
    body = {"text": SHEET, "project_tag": "az-zahra", "title": "Az Zahra price list", "certified": True}
    body.update(overrides)
    return client.post("/v1/rag/ingest", json=body, headers=AUTH)


def test_an_ingested_sheet_is_findable_again_and_carries_its_authority(client):
    nonce = uuid.uuid4().hex[:12]
    marker = f"ACCEPTANCE-PLANT-{nonce} the reorder threshold procedure"
    planted = client.post("/v1/rag/ingest", json={"text": marker}, headers=AUTH)
    assert planted.status_code == 200
    hit = client.post("/v1/rag/query", json={"q": marker}, headers=AUTH)
    assert hit.status_code == 200
    assert nonce in str(hit.json()["hits"]).lower()
    assert hit.json()["authority"]["layer"] in ("documents", "certified")
    absent = client.post("/v1/rag/query", json={"q": uuid.uuid4().hex[:12]}, headers=AUTH)
    assert absent.json()["hits"] == [], "a never-planted term must not be a hit"


def test_a_price_question_is_answered_with_a_verbatim_quote_and_citation(client):
    _ingest(client)
    response = client.post(
        "/v1/rag/ground",
        json={"project_tag": "az-zahra", "question": "what is the starting price", "claim_type": "price"},
        headers=AUTH,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["withheld"] is False
    assert "1,250,000" in body["answer"]
    assert body["citations"]
    assert body["authority"]["label"].startswith("certified:")


def test_a_claim_with_no_supporting_sheet_is_withheld_not_improvised(client):
    response = client.post(
        "/v1/rag/ground",
        json={"project_tag": "marina-gate", "question": "what is the handover date", "claim_type": "handover_date"},
        headers=AUTH,
    )
    body = response.json()
    assert body["withheld"] is True
    assert body["answer"] is None
    assert "handover_date" in body["withheld_claims"]


def test_the_capability_wraps_the_same_discipline(client):
    _ingest(client)
    answered = client.post(
        "/v1/project_knowledge_grounding",
        json=payload_for(
            "project_knowledge_grounding",
            project_tag="az-zahra",
            question="what is the payment plan",
            claim_type="payment_plan",
        ),
        headers=AUTH,
    ).json()
    assert answered["result"]["decision"] == "cited"
    assert answered["result"]["record"]["citations"]
    withheld = client.post(
        "/v1/project_knowledge_grounding",
        json=payload_for(
            "project_knowledge_grounding",
            project_tag="unknown-project",
            question="what is the price",
            claim_type="price",
        ),
        headers=AUTH,
    ).json()
    assert withheld["result"]["withheld"] is True
    assert withheld["result"]["record"]["answer"] is None


def test_a_second_tenants_corpus_is_invisible(client):
    _ingest(client, document_id="tenant-a-sheet")
    mine = client.get("/v1/rag/corpus", headers=AUTH).json()
    theirs = client.get("/v1/rag/corpus", headers=OTHER_AUTH).json()
    assert any(doc["document_id"] == "tenant-a-sheet" for doc in mine["documents"])
    assert all(doc["document_id"] != "tenant-a-sheet" for doc in theirs["documents"])
    query = client.post(
        "/v1/rag/query", json={"q": "starting price az zahra"}, headers=OTHER_AUTH
    ).json()
    assert query["hits"] == []


def test_the_dialogue_withholds_when_the_model_has_no_evidence(client):
    from app import llm

    turn = llm.dialogue_turn(
        "psi",
        {
            "call_sid": "CAground00000000000000000000001",
            "project_tag": "nothing-ingested",
            "language": "ar",
            "utterance": "what is the price",
        },
    )
    assert turn["withheld"] is True
    assert turn["say"]
    assert turn["mode"] == "deterministic"
    assert turn["outcome"] is None


def test_the_grounding_check_refuses_a_figure_retrieval_never_supplied():
    from app.llm import unsupported_claims

    assert unsupported_claims("starts from AED 1,250,000", ["one bedrooms start from AED 1,250,000"]) == []
    assert unsupported_claims("handover 2029", ["handover Q4 2027"]) == ["2029"]


def test_llm_falls_back_to_the_deterministic_planner_without_a_provider(monkeypatch):
    from app import config, llm

    monkeypatch.setattr(config, "LLM_PROVIDER", None)
    monkeypatch.setattr(config, "LLM_API_KEY", None)
    assert llm._model_turn(question="price?", evidence=["x"], language="en", project_tag="p") is None


def test_the_price_lane_names_no_currency_the_operator_did_not_supply():
    """The brief states no country, so no currency is assumed in retrieval."""
    import importlib

    from app import config, retrieval

    fresh = importlib.reload(retrieval)
    assert fresh.price_currency_tokens() == set()

    # the operator's own token turns the same sentence into the price one
    monkeypatched = {"env": lambda name, default=None: ("AED" if name == "CURRENCY" else default)}
    import unittest.mock as mock

    with mock.patch.object(config, "env", monkeypatched["env"]):
        assert "aed" in fresh.price_currency_tokens()
    with mock.patch.object(
        config, "PRICE_CURRENCY_TOKENS", ("QAR", "SAR")
    ), mock.patch.object(config, "env", lambda name, default=None: default):
        assert fresh.price_currency_tokens() == {"qar", "sar"}

    sentence = fresh.relevant_sentence(
        "Handover is Q4 2027. One bedroom apartments start from AED 1,250,000.",
        "how much is a one bedroom",
        "price",
    )
    assert "1,250,000" in sentence
    importlib.reload(retrieval)
