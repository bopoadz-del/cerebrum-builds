"""One tenant per request; answers carry precedence labels and divergences.

Written by the factory WRITER role (codewhale exec)
"""

from __future__ import annotations

import pytest

from helpers import AUTH, client


def test_tenancy_binding_reports_the_authenticated_principal():
    with client() as api:
        resp = api.get("/v1/tenancy", headers=AUTH)
        assert resp.status_code == 200
        body = resp.json()
        assert body["tenant"] == "local"
        assert body["tenant_source"] == "authenticated principal"
        assert set(body["roles"]) == {"operator", "admin"}


def test_a_client_supplied_tenant_is_refused():
    headers = dict(AUTH)
    headers["X-Tenant"] = "someone-else"
    with client() as api:
        resp = api.get("/v1/tenancy", headers=headers)
        assert resp.status_code == 403
        assert "tenant_override_refused" in resp.text


def test_corpus_ingest_is_tenant_scoped():
    with client() as api:
        resp = api.post(
            "/v1/corpus/documents",
            json={
                "title": "Organic certification",
                "body": "Certified organic production for the north block. "
                "Pesticide application must be logged within 24 hours.",
                "source_kind": "certified",
                "certified": True,
            },
            headers=AUTH,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["stored"]["layer"] == 1
        listed = api.get("/v1/corpus/documents", headers=AUTH)
        assert listed.status_code == 200
        assert any(
            item["title"] == "Organic certification" for item in listed.json()["items"]
        )


def test_corpus_rows_are_only_visible_to_their_tenant():
    from app import retrieval

    retrieval.ingest(
        tenant="tenant-a",
        title="Tenant A house rule",
        body="Quiet hours run from 22:00 to 07:00 on every floor of the house.",
        source_kind="procedure",
    )
    retrieval.ingest(
        tenant="tenant-b",
        title="Tenant B house rule",
        body="Breakfast is served in the dining room from 07:00 to 10:00.",
        source_kind="procedure",
    )
    a_hits = retrieval.retrieve("quiet hours", tenant="tenant-a")
    b_hits = retrieval.retrieve("quiet hours", tenant="tenant-b")
    assert a_hits and all(hit["title"] == "Tenant A house rule" for hit in a_hits)
    assert b_hits == []
    assert retrieval.list_documents("tenant-a")["total"] == 1


def test_answers_carry_labels_and_divergences():
    with client() as api:
        api.post(
            "/v1/corpus/documents",
            json={
                "title": "Quiet hours rule (certified)",
                "body": "Quiet hours run from 22:00 to 07:00 on every floor of the house.",
                "source_kind": "certified",
                "certified": True,
            },
            headers=AUTH,
        )
        api.post(
            "/v1/corpus/documents",
            json={
                "title": "Draft house procedure",
                "body": "Quiet hours run from 22:00 to 07:00 except on the ground floor.",
                "source_kind": "procedure",
            },
            headers=AUTH,
        )
        resp = api.get("/v1/answers?q=quiet hours", headers=AUTH)
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["grounded"] is True
        assert body["precedence"] == "precedence.v1"
        assert body["winner"]["layer"] == 1
        assert body["winner"]["layer_name"] == "certified"
        assert body["labels"]
        assert all(label["precedence"] == "precedence.v1" for label in body["labels"])
        assert body["answer_id"] > 0
        assert body["provider"] == "offline-deterministic"
        assert body["network"] is False


def test_ungrounded_question_says_so():
    with client() as api:
        resp = api.get("/v1/answers?q=unobtainium%20quota", headers=AUTH)
        assert resp.status_code == 200
        body = resp.json()
        assert body["grounded"] is False
        assert body["winner"] is None
        assert "No grounded source" in body["answer"]


def test_precedence_declaration_order():
    with client() as api:
        body = api.get("/v1/precedence", headers=AUTH).json()
        assert body["precedence"] == "precedence.v1"
        assert [layer["name"] for layer in body["layers"]] == [
            "certified",
            "documents",
            "formulas",
            "procedures",
        ]


def test_llm_status_is_honest_about_running_offline():
    with client() as api:
        body = api.get("/v1/llm", headers=AUTH).json()
        assert body["provider"] == "offline-deterministic"
        assert body["network"] is False
