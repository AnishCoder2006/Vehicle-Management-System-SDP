"""Tests verifying that every agent returns a strictly valid AgentResponse.
"""

import pytest
from agents.analytics_agent import run_analytics_agent
from agents.automation_agent import run_automation_agent
from agents.master_agent import run_master_agent
from agents.schemas import AgentRequest, AgentResponse
from agents.tools.mock_data import reset_mock_db
from agents.vehicle_agent import run_vehicle_agent


@pytest.fixture(autouse=True)
def setup_mock_db():
    reset_mock_db()


def assert_valid_agent_response(resp: AgentResponse, expected_agent: str):
    """Helper asserting strict conformance to the AgentResponse schema."""
    assert isinstance(resp, AgentResponse)
    assert resp.status in ("success", "partial", "needs_confirmation", "error")
    assert isinstance(resp.answer, str) and len(resp.answer) > 0
    assert resp.agent_used == expected_agent or resp.agent_used == "master_agent"
    assert isinstance(resp.tools_called, list)
    if resp.status == "error":
        assert resp.error is not None
    else:
        assert resp.error is None


def test_vehicle_agent_read_response():
    req = AgentRequest(session_id="s1", message="Which vehicles are currently available?")
    resp = run_vehicle_agent(req)
    assert_valid_agent_response(resp, "vehicle_agent")
    assert resp.status == "success"
    assert len(resp.data) > 0


def test_vehicle_agent_write_unconfirmed_response():
    req = AgentRequest(session_id="s2", message="Assign vehicle 11 to driver 1.")
    resp = run_vehicle_agent(req)
    assert_valid_agent_response(resp, "vehicle_agent")
    assert resp.status == "needs_confirmation"
    assert "assign vehicle 11" in resp.answer.lower()
    assert resp.data["action"] == "create_assignment"


def test_vehicle_agent_write_confirmed_response():
    req = AgentRequest(
        session_id="s3",
        message="Assign vehicle 11 to driver 1.",
        context={"confirmed": True},
    )
    resp = run_vehicle_agent(req)
    assert_valid_agent_response(resp, "vehicle_agent")
    assert resp.status == "success"
    assert resp.data["vehicle_id"] == 11
    assert resp.data["driver_id"] == 1


def test_analytics_agent_stats_response():
    req = AgentRequest(session_id="s4", message="What are the overall fleet statistics and vehicle counts?")
    resp = run_analytics_agent(req)
    assert_valid_agent_response(resp, "analytics_agent")
    assert resp.status == "success"
    assert "total_vehicles" in resp.data


def test_analytics_agent_costs_summary_response():
    req = AgentRequest(session_id="s5", message="Give me the total expense summary grouped by vehicle and month.")
    resp = run_analytics_agent(req)
    assert_valid_agent_response(resp, "analytics_agent")
    assert resp.status == "success"
    assert "grand_total" in resp.data


def test_automation_agent_due_service_response():
    req = AgentRequest(session_id="s6", message="Which vehicles are due for service or overdue?")
    resp = run_automation_agent(req)
    assert_valid_agent_response(resp, "automation_agent")
    assert resp.status == "success"
    assert len(resp.data) > 0


def test_master_agent_delegation_response():
    req = AgentRequest(session_id="s7", message="Show me all registered drivers.")
    resp = run_master_agent(req)
    assert_valid_agent_response(resp, "vehicle_agent")
    assert resp.status == "success"


def test_master_agent_unclear_response():
    req = AgentRequest(session_id="s8", message="Update it please.")
    resp = run_master_agent(req)
    assert_valid_agent_response(resp, "master_agent")
    assert resp.status == "partial"
    assert "?" in resp.answer
