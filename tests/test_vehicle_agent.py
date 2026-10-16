"""Tests for the Vehicle Operations Agent (Member 3).

Runs in mock mode with the LLM disabled, so results are deterministic. A fake
OpenAI client covers the function-calling loop and its write-safety guarantees.
"""

import json
from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from agents import vehicle_agent
from agents.schemas import AgentRequest
from agents.tools.mock_data import MOCK_STORE, reset_mock_db
from agents.vehicle_agent import run_vehicle_agent
from agents.vehicle_tools import VEHICLE_TOOLS, call_tool


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    reset_mock_db()
    monkeypatch.setenv("USE_MOCK_TOOLS", "true")
    monkeypatch.setenv("VEHICLE_AGENT_LLM", "off")


def ask(message: str, **context):
    return run_vehicle_agent(AgentRequest(session_id="t", message=message, context=context))


def vehicle(vid: int) -> dict:
    return next(v for v in MOCK_STORE["vehicles"] if v["id"] == vid)


# --- Confirmation flow -------------------------------------------------------
def test_two_turn_confirmation_with_parameters_payload():
    first = ask("Assign vehicle 11 to driver 1")
    assert first.status == "needs_confirmation"
    assert vehicle(11)["status"] == "available"  # nothing written yet

    second = ask("yes", confirmed=True, action=first.data["action"], parameters=first.data["parameters"])
    assert second.status == "success"
    assert vehicle(11)["status"] == "assigned"


def test_confirmation_with_flat_context_keys_from_handoff_doc():
    resp = ask("Yes, proceed", confirmed=True, action="create_assignment", vehicle_id=11, driver_id=1)
    assert resp.status == "success"
    assert resp.data["vehicle_id"] == 11


def test_declined_confirmation_makes_no_changes():
    resp = ask("no", confirmed=False, action="create_assignment", vehicle_id=11, driver_id=1)
    assert resp.status == "success"
    assert "no changes" in resp.answer.lower()
    assert vehicle(11)["status"] == "available"


def test_cannot_confirm_read_or_unknown_action():
    resp = ask("yes", confirmed=True, action="get_drivers")
    assert resp.status == "error"


# --- Vehicle CRUD -------------------------------------------------------------
def test_update_mileage_requires_confirmation_then_applies():
    pending = ask("Set mileage of vehicle 6 to 99,000")
    assert pending.status == "needs_confirmation"
    assert pending.data["parameters"] == {"id": 6, "mileage": 99000}

    done = ask("yes", confirmed=True, action="update_vehicle", parameters=pending.data["parameters"])
    assert done.status == "success"
    assert vehicle(6)["mileage"] == 99000


def test_mileage_cannot_decrease():
    resp = ask("Set mileage of vehicle 6 to 5")
    assert resp.status == "error"
    assert "cannot decrease" in resp.answer.lower()


def test_reschedule_next_service_date():
    pending = ask("Reschedule next service for vehicle 7 to 2027-01-15")
    assert pending.status == "needs_confirmation"
    done = ask("yes", confirmed=True, action="update_vehicle", parameters=pending.data["parameters"])
    assert done.status == "success"
    assert vehicle(7)["next_service_date"] == date(2027, 1, 15)


def test_create_vehicle_and_duplicate_plate():
    params = {"plate_number": "kxx-1234", "make": "Tata", "model": "Ace", "vehicle_type": "truck", "mileage": 10}
    pending = call_tool("create_vehicle", params, confirmed=False)
    assert pending.action == "create_vehicle"
    assert pending.parameters["plate_number"] == "KXX-1234"

    resp = ask("yes", confirmed=True, action="create_vehicle", parameters=pending.parameters)
    assert resp.status == "success"
    assert resp.data["status"] == "available"

    dup = ask("yes", confirmed=True, action="create_vehicle", parameters=pending.parameters)
    assert dup.status == "error"
    assert "already exists" in dup.answer.lower()


def test_vehicle_details_and_availability_check():
    details = ask("Show details for vehicle 4")
    assert details.status == "success" and details.data["id"] == 4
    avail = ask("Is vehicle 4 available?")
    assert "not available" in avail.answer
    assert ask("Is vehicle 11 available?").answer.endswith("is available.")


def test_plate_lookup_fallback():
    resp = ask("What is the status of KBZ-4567?")
    assert resp.status == "success"
    assert resp.data["id"] == 11


def test_available_vans_filter():
    resp = ask("Which vans are available?")
    assert resp.status == "success"
    assert resp.data and all(v["vehicle_type"] == "van" and v["status"] == "available" for v in resp.data)


# --- Maintenance --------------------------------------------------------------
def test_maintenance_overdue_vehicle():
    resp = ask("Maintenance status for vehicle 1")
    assert resp.status == "success"
    assert resp.data["maintenance_state"] == "overdue"
    assert "OVERDUE by 3" in resp.answer


def test_maintenance_states():
    assert call_tool("get_vehicle_maintenance", {"id": 2}).maintenance_state == "due_soon"
    assert call_tool("get_vehicle_maintenance", {"id": 11}).maintenance_state == "ok"


def test_book_service_with_date():
    resp = ask("Book a brake check service for vehicle 2 on 2026-12-01")
    assert resp.status == "needs_confirmation"
    assert resp.data["parameters"]["booked_date"] == "2026-12-01"


def test_unknown_vehicle_returns_not_found():
    resp = ask("Maintenance for vehicle 999")
    assert resp.status == "error"
    assert "not found" in resp.answer.lower()


# --- LLM loop (fake OpenAI client) -------------------------------------------
def _tool_call(call_id, name, args):
    return SimpleNamespace(id=call_id, type="function",
                           function=SimpleNamespace(name=name, arguments=json.dumps(args)))


class FakeOpenAI:
    """Replays a scripted list of assistant messages."""

    def __init__(self, script):
        self.script = list(script)
        self.requests = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.requests.append(kwargs)
        msg = self.script.pop(0)
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])


@pytest.fixture
def fake_llm(monkeypatch):
    monkeypatch.setenv("VEHICLE_AGENT_LLM", "on")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def install(script):
        fake = FakeOpenAI(script)
        import openai
        monkeypatch.setattr(openai, "OpenAI", lambda **_: fake)
        return fake
    return install


def test_llm_read_flow(fake_llm):
    fake = fake_llm([
        SimpleNamespace(content="", tool_calls=[_tool_call("c1", "get_drivers", {})]),
        SimpleNamespace(content="There are 4 drivers.", tool_calls=None),
    ])
    resp = ask("who drives for us?")
    assert resp.status == "success"
    assert resp.answer == "There are 4 drivers."
    assert resp.tools_called == ["get_drivers"]
    assert len(resp.data) == 4
    # `confirmed` must never be exposed to the model
    specs = {t["function"]["name"]: t["function"]["parameters"] for t in fake.requests[0]["tools"]}
    assert "confirmed" not in specs["create_assignment"]["properties"]


def test_llm_cannot_self_confirm_writes(fake_llm):
    fake_llm([
        SimpleNamespace(content="", tool_calls=[
            _tool_call("c1", "create_assignment", {"vehicle_id": 11, "driver_id": 2, "confirmed": True}),
        ]),
    ])
    resp = ask("give the HiAce to Jane")
    assert resp.status == "needs_confirmation"
    assert resp.data["parameters"] == {"vehicle_id": 11, "driver_id": 2}
    assert vehicle(11)["status"] == "available"


def test_llm_tool_error_is_fed_back(fake_llm):
    fake = fake_llm([
        SimpleNamespace(content="", tool_calls=[_tool_call("c1", "create_assignment", {"vehicle_id": 4, "driver_id": 1})]),
        SimpleNamespace(content="Vehicle 4 is in service, so it can't be assigned.", tool_calls=None),
    ])
    resp = ask("give vehicle 4 to John")
    assert resp.status == "success"
    tool_msg = fake.requests[1]["messages"][-1]
    assert tool_msg["role"] == "tool" and "not available" in tool_msg["content"]


def test_llm_failure_falls_back_to_rules(fake_llm):

    def boom(**_):
        raise RuntimeError("provider down")
    fake = fake_llm([])
    fake.chat.completions.create = boom
    resp = ask("list the drivers please")
    assert resp.status == "success"
    assert resp.tools_called == ["get_drivers"]


def test_every_catalog_tool_has_valid_openai_spec():
    for tool in VEHICLE_TOOLS.values():
        spec = tool.openai_spec()["function"]
        assert spec["parameters"]["type"] == "object"
        assert "confirmed" not in spec["parameters"].get("properties", {})
