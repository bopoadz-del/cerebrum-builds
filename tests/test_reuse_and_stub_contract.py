"""REUSE and stub-declaration contracts.

Two rules the platform must hold to, measured here rather than asserted in a
comment:

* **a bound block is dispatched with a keyword action.** Every handler that
  names a block in ``BLOCK_DEFAULT_ACTIONS`` must supply a non-empty action
  for each block its capability binds, so the call site can pass
  ``action=BLOCK_DEFAULT_ACTIONS.get(block_id)`` instead of ``action=None``
  (the Store answers ``Unknown action: None``).
* **what is unavailable is stated once, at the top, or not at all.** A block
  that cannot reach its provider names the missing setting; the envelope
  restates every one of those names in a single non-empty
  ``blocks_unavailable`` list and never leaves an empty declaration behind,
  because an empty one reads as a stub the operator cannot act on.
"""

from __future__ import annotations

import importlib
import json
from typing import Any, List

import pytest

from app import dispatch
from app.block_inputs import default_block_action
from app.models import MODELS
from tests.callops_helpers import AUTH, client, payload_for  # noqa: F401

CAPS = list(MODELS)


def _module(capability_id: str):
    return importlib.import_module(f"app.actions.{capability_id}")


def _declaration_sites(node: Any, found: List[Any] = None) -> List[Any]:
    """Every ``blocks_unavailable`` value anywhere in an envelope."""
    found = [] if found is None else found
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "blocks_unavailable":
                found.append(value)
            else:
                _declaration_sites(value, found)
    elif isinstance(node, (list, tuple)):
        for value in node:
            _declaration_sites(value, found)
    return found


@pytest.mark.parametrize("capability", CAPS)
def test_every_bound_block_has_a_declared_keyword_action(capability):
    """A handler feeds the blocks it binds -- with an action, never None."""
    module = _module(capability)
    declared = dict(getattr(module, "BLOCK_DEFAULT_ACTIONS", {}) or {})
    if not declared and not MODELS[capability].BLOCKS:
        pytest.skip(f"{capability} binds no Store block")
    for block_id in MODELS[capability].BLOCKS:
        assert default_block_action(block_id, declared), (
            f"{capability}: no BLOCK_DEFAULT_ACTIONS entry for {block_id} "
            "would call execute() with action=None"
        )


@pytest.mark.parametrize("capability", CAPS)
def test_the_response_states_what_is_unavailable_once_and_never_empty(client, capability):
    """No capability answers with an empty or nested-only stub declaration."""
    response = client.post(f"/v1/{capability}", json=payload_for(capability), headers=AUTH)
    assert response.status_code == 200, response.text
    body = response.json()
    result = body.get("result") or {}
    assert "blocks_unavailable" not in body, "the declaration belongs on the result"
    sites = _declaration_sites(result)
    if not sites:
        return
    assert len(sites) == 1, (
        f"{capability}: the declaration is restated at the top level only, "
        f"found {len(sites)} copies"
    )
    unavailable = sites[0]
    assert isinstance(unavailable, list) and unavailable, (
        f"{capability}: blocks_unavailable must be a non-empty list"
    )
    assert all(isinstance(name, str) and name for name in unavailable)


def test_an_unconfigured_provider_is_reported_as_a_stub_not_a_failure(client, monkeypatch):
    """Twilio with no account is a declared stub: ok true, the setting named."""
    from app import config

    # The edge reads its settings when it is constructed, so clearing the
    # account is enough to put this call in the stubbed position.
    monkeypatch.setattr(config, "TWILIO_ACCOUNT_SID", "")
    response = client.post(
        "/v1/voice_gateway",
        json=payload_for("voice_gateway", call_sid="CAstub000000000000000000000001"),
        headers=AUTH,
    )
    assert response.status_code == 200, response.text
    result = response.json()["result"]
    assert result["decision"] == "stubbed"
    assert "TWILIO_ACCOUNT_SID" in result["blocks_unavailable"]


def test_a_block_that_errors_is_never_reported_as_success(client, monkeypatch):
    """Forced block failure: the capability refuses rather than answering ok."""
    def _always_errors(block_id, action=None, payload=None, **kwargs):
        return {"status": "error", "block": block_id, "error": "refused (test)"}

    monkeypatch.setattr(dispatch, "execute", _always_errors)
    for capability in ("notification", "local_drive", "call_state_machine"):
        response = client.post(
            f"/v1/{capability}", json=payload_for(capability), headers=AUTH
        )
        assert response.status_code == 409, (
            f"{capability} answered {response.status_code} while its block errored: "
            f"{response.text[:160]}"
        )
        assert response.json()["ok"] is False


def test_call_state_machine_publishes_a_prepared_event_bus_step(client):
    """A transition writes its call event through a fully constructed step."""
    body = payload_for(
        "call_state_machine",
        call_sid="CAstep000000000000000000000001",
        event="answer",
        previous_state="dialing",
    )
    response = client.post("/v1/call_state_machine", json=body, headers=AUTH)
    assert response.status_code == 200, response.text
    event = response.json()["result"]["event"]
    assert event["published"] is True
    assert event["channel"] == "mcp"
    assert event["tool"] == "event_bus"
    assert event["topic"].startswith("call.transition.")

    from app.actions.call_state_machine import WORKFLOW_STEPS, event_step

    step = WORKFLOW_STEPS[0]
    assert set(step) == {"block", "action", "input"}
    assert step["block"] == "event_bus"
    assert step["action"] == "publish"
    assert step["input"]["channel"] == "mcp"
    assert step["input"]["tool"] == "event_bus"
    assert step["input"]["topic"] and step["input"]["message"]
    # populating the template never forwards the caller's record as a step input
    populated = event_step(
        {"call_sid": "CAstep1", "event": "pitch"},
        {
            "event": "pitch",
            "previous_state": "answered",
            "current_state": "pitched",
            "transition_allowed": True,
        },
    )
    assert isinstance(populated["input"]["payload"], dict)
    assert "CAstep1" in json.dumps(populated["input"]["payload"])
    assert populated["input"]["topic"] == "call.transition.pitch"
