"""Front-desk domain behaviour: check-in, arrival board, double booking."""

from __future__ import annotations

import importlib

import pytest

from app.models import MODELS
from tests.helpers import sample_for

record_checkin = importlib.import_module("app.actions.record_checkin")
board = importlib.import_module("app.actions.todays_arrivals_board")
availability = importlib.import_module("app.actions.room_availability_check")
notes = importlib.import_module("app.actions.guest_notes_and_preferences")
notify = importlib.import_module("app.actions.checkin_notifications")
summary = importlib.import_module("app.actions.daily_checkin_summary")
audit = importlib.import_module("app.actions.audit_trail")

HANDLERS = {
    "record_checkin": record_checkin,
    "todays_arrivals_board": board,
    "room_availability_check": availability,
    "guest_notes_and_preferences": notes,
    "checkin_notifications": notify,
    "daily_checkin_summary": summary,
    "audit_trail": audit,
}


def test_every_capability_invokes_every_block_it_declares():
    """A declared block that is never invoked is a build error (F11)."""
    for capability_id, module in HANDLERS.items():
        outcome = module.handle(sample_for(capability_id))
        results = outcome.get("results") or {}
        for block_id in module.BLOCK_IDS:
            assert block_id in results, (capability_id, block_id)


def test_check_in_refuses_an_unknown_room_label():
    payload = sample_for("record_checkin")
    payload["room_number"] = "!!not-a-room!!"
    out = record_checkin.handle(payload)
    assert out["ok"] is False
    assert "room_number" in out["error"]


def test_check_in_refuses_a_stay_longer_than_the_house_allows():
    payload = sample_for("record_checkin")
    payload["nights"] = 99
    out = record_checkin.handle(payload)
    assert out["ok"] is False
    assert "nights" in out["error"]


def test_check_in_reports_the_room_the_nights_and_the_capture():
    payload = sample_for("record_checkin")
    payload.update({"guest_name": "Ada Lovelace", "room_number": "101", "nights": 2})
    out = record_checkin.handle(payload)
    assert out["ok"] is True, out
    assert out["check_in"]["guest_name"] == "Ada Lovelace"
    assert out["check_in"]["nights"] == 2
    assert out["capture"]["capture_id"]
    assert out["front_desk"]["house_rooms"] == 40


def test_room_availability_computes_nights_and_charge():
    payload = sample_for("room_availability_check")
    payload.update({"check_in_date": "2026-09-03", "check_out_date": "2026-09-06"})
    out = availability.handle(payload)
    assert out["ok"] is True, out
    assert out["availability"]["nights"] == 3
    assert out["stay"]["estimated_charge"] == 3 * out["stay"]["nightly_rate"]
    assert out["availability"]["is_available"] is True


def test_room_availability_refuses_a_reversed_date_range():
    payload = sample_for("room_availability_check")
    payload.update({"check_in_date": "2026-09-06", "check_out_date": "2026-09-03"})
    out = availability.handle(payload)
    assert out["ok"] is False
    assert "check_out_date" in out["error"]


def test_arrival_board_reports_arrived_state():
    payload = sample_for("todays_arrivals_board")
    payload["arrived"] = True
    out = board.handle(payload)
    assert out["ok"] is True, out
    assert out["board"]["arrived"] is True
    assert out["board"]["status"] == "arrived"


def test_guest_note_needs_a_preference_or_a_note():
    payload = sample_for("guest_notes_and_preferences")
    payload["preference"] = ""
    payload["note"] = ""
    out = notes.handle(payload)
    assert out["ok"] is False
    assert "preference or a note" in out["error"]


def test_check_in_notification_is_a_prepared_mcp_event():
    payload = sample_for("checkin_notifications")
    payload.update({"guest_name": "Ada Lovelace", "room_number": "101"})
    out = notify.handle(payload)
    assert out["ok"] is True, out
    step = notify.event_bus_step(payload)
    assert step["block"] == "event_bus"
    assert step["action"] == "publish"
    bus_input = step["input"]
    assert bus_input["channel"] == "mcp"
    assert bus_input["tool"] == "event_bus"
    assert isinstance(bus_input["payload"], dict)
    assert bus_input["channel"] == "mcp"
    assert bus_input["tool"] == "event_bus"
    assert isinstance(bus_input["payload"], dict)
    assert bus_input["topic"].startswith("hospitality.checkin")
    assert out["notification"]["published"] is True
    assert out["follow_up"]["job_id"]


def test_check_in_notification_refuses_email_without_a_recipient():
    payload = sample_for("checkin_notifications")
    payload["channel"] = "email"
    payload["recipient"] = ""
    out = notify.handle(payload)
    assert out["ok"] is False
    assert "recipient" in out["error"]


def test_daily_summary_computes_occupancy_from_the_house_size():
    payload = sample_for("daily_checkin_summary")
    payload["arrivals_count"] = 20
    payload.pop("occupancy_percent", None)
    out = summary.handle(payload)
    assert out["ok"] is True, out
    assert out["summary"]["occupancy_percent"] == 50.0
    assert out["summary"]["house_rooms"] == 40


def test_daily_summary_refuses_an_impossible_occupancy():
    payload = sample_for("daily_checkin_summary")
    payload["occupancy_percent"] = 140
    out = summary.handle(payload)
    assert out["ok"] is False
    assert "occupancy_percent" in out["error"]


def test_audit_trail_labels_the_actor_and_the_change():
    payload = sample_for("audit_trail")
    payload.update({"actor": "duty.manager", "change_type": "update"})
    out = audit.handle(payload)
    assert out["ok"] is True, out
    assert out["accountability"]["actor"] == "duty.manager"
    assert out["accountability"]["change_type"] == "update"
    assert out["audit"]["event_id"]
    assert out["audit"]["immutable"] is True


def test_audit_trail_refuses_an_unknown_change_type():
    payload = sample_for("audit_trail")
    payload["change_type"] = "rewritten"
    out = audit.handle(payload)
    assert out["ok"] is False
    assert "change_type" in out["error"]
