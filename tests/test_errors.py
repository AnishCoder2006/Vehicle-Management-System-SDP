"""Tests verifying that known API errors are translated into clean user messages.
"""

import pytest
from agents.errors import (
    ErrorCategory,
    classify_error,
    handle_agent_error,
)
from agents.tools.base import ToolError


def test_404_not_found_clean_message():
    err = ToolError("Vehicle with id 999 not found", status_code=404, endpoint="/vehicles/999")
    cat, _ = classify_error(err)
    assert cat == ErrorCategory.NOT_FOUND_404

    resp = handle_agent_error(err, agent_name="vehicle_agent")
    assert resp.status == "error"
    assert "Not Found: Vehicle with id 999 not found" in resp.answer
    assert resp.error is not None


def test_409_conflict_clean_message():
    err = ToolError(
        "Vehicle with plate number 'KAA-1001' already exists",
        status_code=409,
        endpoint="/vehicles",
    )
    cat, _ = classify_error(err)
    assert cat == ErrorCategory.CONFLICT_409

    resp = handle_agent_error(err, agent_name="vehicle_agent")
    assert resp.status == "error"
    assert "Conflict:" in resp.answer
    assert "already exists" in resp.answer


def test_400_business_rule_violation_clean_message():
    err = ToolError(
        "Vehicle with id 4 is not available (current status: in_service)",
        status_code=400,
        endpoint="/assignments",
    )
    cat, _ = classify_error(err)
    assert cat == ErrorCategory.RULE_VIOLATION_400

    resp = handle_agent_error(err, agent_name="vehicle_agent")
    assert resp.status == "error"
    assert "Validation Error: Vehicle with id 4 is not available" in resp.answer


def test_503_api_down_clean_message():
    err = ToolError(
        "Cannot reach backend API at http://localhost:8000. Please ensure FastAPI is running on port 8000.",
        status_code=503,
        endpoint="/vehicles",
    )
    cat, _ = classify_error(err)
    assert cat == ErrorCategory.API_DOWN

    resp = handle_agent_error(err, agent_name="vehicle_agent")
    assert resp.status == "error"
    assert "currently unreachable" in resp.answer


def test_504_timeout_clean_message():
    err = ToolError(
        "Backend API request to /costs/summary timed out after 10.0 seconds.",
        status_code=504,
        endpoint="/costs/summary",
    )
    cat, _ = classify_error(err)
    assert cat == ErrorCategory.TIMEOUT

    resp = handle_agent_error(err, agent_name="analytics_agent")
    assert resp.status == "error"
    assert "timed out" in resp.answer
