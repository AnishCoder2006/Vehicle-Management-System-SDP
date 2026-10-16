"""Tests verifying write-action safety and pre-validations across tools.
"""

import pytest
from agents.tools import operations
from agents.tools.base import ToolError
from agents.tools.mock_data import reset_mock_db
from agents.tools.models import ConfirmationRequiredOutput
from agents.tools.registry import TOOL_REGISTRY, list_all_tools


@pytest.fixture(autouse=True)
def setup_mock_db():
    reset_mock_db()


def test_registry_has_all_18_tools():
    """Verify that all 18 backend endpoints are wrapped and registered."""
    tools = list_all_tools()
    assert len(tools) == 18, f"Expected 18 registered tools, found {len(tools)}"


def test_create_assignment_requires_confirmation():
    """Write tool create_assignment must return ConfirmationRequiredOutput when unconfirmed."""
    res = operations.create_assignment(vehicle_id=11, driver_id=1, confirmed=False)
    assert isinstance(res, ConfirmationRequiredOutput)
    assert res.requires_confirmation is True
    assert res.action == "create_assignment"
    assert "vehicle 11" in res.summary.lower()


def test_create_assignment_prevalidates_vehicle_availability():
    """Assignment must fail if vehicle is in_service or assigned."""
    # Vehicle 4 has status 'in_service' in mock seed
    with pytest.raises(ToolError) as exc_info:
        operations.create_assignment(vehicle_id=4, driver_id=1, confirmed=False)
    assert exc_info.value.status_code == 400
    assert "not available" in exc_info.value.message.lower()


def test_service_status_transition_rules():
    """Service record transition must strictly enforce pending -> in_progress -> completed."""
    # Service 3 is pending in mock seed
    # Cannot jump pending -> completed
    with pytest.raises(ToolError) as exc_info:
        operations.update_service_status(id=3, status="completed", confirmed=False)
    assert exc_info.value.status_code == 400
    assert "pending" in exc_info.value.message.lower()

    # Valid step 1: pending -> in_progress returns confirmation
    conf1 = operations.update_service_status(id=3, status="in_progress", confirmed=False)
    assert isinstance(conf1, ConfirmationRequiredOutput)

    # Execute step 1 with confirmed=True
    rec1 = operations.update_service_status(id=3, status="in_progress", confirmed=True)
    assert rec1.status == "in_progress"

    # Step 2: in_progress -> completed
    conf2 = operations.update_service_status(id=3, status="completed", confirmed=False)
    assert isinstance(conf2, ConfirmationRequiredOutput)
    rec2 = operations.update_service_status(id=3, status="completed", confirmed=True)
    assert rec2.status == "completed"
    assert rec2.completed_date is not None

    # Step 3: completed cannot transition further
    with pytest.raises(ToolError) as exc_info2:
        operations.update_service_status(id=3, status="in_progress", confirmed=False)
    assert exc_info2.value.status_code == 400
    assert "already completed" in exc_info2.value.message.lower()


def test_create_cost_requires_confirmation_and_validates_category():
    """Cost logging requires confirmation and rejects invalid category."""
    # Invalid category
    with pytest.raises(ToolError) as exc_info:
        operations.create_cost(vehicle_id=1, category="luxury", amount=100.0, confirmed=False)
    assert exc_info.value.status_code == 400
    assert "invalid cost category" in exc_info.value.message.lower()

    # Valid category requires confirmation
    conf = operations.create_cost(vehicle_id=1, category="fuel", amount=50.0, confirmed=False)
    assert isinstance(conf, ConfirmationRequiredOutput)
    assert conf.parameters["amount"] == 50.0

    # Confirmed execution
    cost = operations.create_cost(vehicle_id=1, category="fuel", amount=50.0, confirmed=True)
    assert cost.amount == 50.0
