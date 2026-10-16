"""Common schemas for the multi-agent system.

Defines the universal request and response interfaces for all agents
(Master Agent, Vehicle Operations Agent, Analytics Agent, Automation Agent),
as well as write-action confirmation payloads.
"""

from datetime import date, datetime
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field, ConfigDict


# Status options for AgentResponse
AgentStatus = Literal["success", "partial", "needs_confirmation", "error"]


class AgentRequest(BaseModel):
    """Input payload sent to the agent system by the user or client UI."""

    session_id: str = Field(
        ...,
        description="Unique session identifier for multi-turn conversations",
        examples=["sess-12345"],
    )
    message: str = Field(
        ...,
        description="User text prompt or message",
        examples=["Which vehicles are due for service?"],
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional session context (e.g. pending confirmation states, user roles)",
        examples=[{"confirmed": True, "action": "assign_vehicle"}],
    )


class ConfirmationDetails(BaseModel):
    """Structured details for actions requiring explicit user confirmation before execution."""

    action: str = Field(
        ...,
        description="Identifier of the write tool to be executed",
        examples=["create_assignment"],
    )
    summary: str = Field(
        ...,
        description="Plain-language human readable explanation of the pending change",
        examples=["Assign vehicle 11 (Toyota HiAce) to driver 1 (John Doe). Vehicle status will change to 'assigned'."],
    )
    parameters: dict[str, Any] = Field(
        ...,
        description="Exact payload/arguments that will be sent upon confirmation",
        examples=[{"vehicle_id": 11, "driver_id": 1}],
    )
    precheck_passed: bool = Field(
        True,
        description="Indicates whether business rule pre-validation succeeded",
    )


class AgentResponse(BaseModel):
    """Standardized response schema returned by every agent.
    
    Member 5 (Frontend) builds the chat UI components based on this shape.
    """

    status: AgentStatus = Field(
        ...,
        description="Execution status: 'success', 'partial', 'needs_confirmation', or 'error'",
        examples=["success"],
    )
    answer: str = Field(
        ...,
        description="Natural language message presented to the user in chat",
        examples=["There are 3 vehicles currently due for service or overdue."],
    )
    data: Optional[Any] = Field(
        None,
        description="Structured data returned by tools, or ConfirmationDetails if needs_confirmation",
    )
    agent_used: Optional[str] = Field(
        None,
        description="Name of the specialist or master agent handling the request",
        examples=["automation_agent"],
    )
    tools_called: list[str] = Field(
        default_factory=list,
        description="List of tool names invoked during request processing",
        examples=["get_due_service_vehicles"],
    )
    error: Optional[str] = Field(
        None,
        description="User-friendly error message if status is 'error', else None",
    )

    model_config = ConfigDict(extra="ignore")
