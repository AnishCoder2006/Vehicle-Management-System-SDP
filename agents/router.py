"""Intent-based router for multi-agent dispatch.

Classifies incoming user messages into fixed intents and routes to appropriate specialist agents:
- Vehicle Operations Agent (Member 3)
- Analytics Agent (Member 4)
- Automation Agent (Member 6)
- Master Agent (multi-agent coordination)
- Clarification handler (unclear requests)
"""

from enum import Enum
import re
from typing import Any, Optional
from pydantic import BaseModel, Field


class Intent(str, Enum):
    """Fixed list of supported system intents."""
    VEHICLE_OPERATIONS = "vehicle_operations"
    ANALYTICS = "analytics"
    AUTOMATION = "automation"
    MULTI_AGENT = "multi_agent"
    UNCLEAR = "unclear"


class RouteDecision(BaseModel):
    """Output decision returned by the router."""
    intent: Intent
    target_agents: list[str]
    confidence: float = 1.0
    reasoning: str
    clarifying_question: Optional[str] = None


# Routing Table mapping intent -> agent details
ROUTING_TABLE = {
    Intent.VEHICLE_OPERATIONS: {
        "agent": "vehicle_agent",
        "owner": "Member 3",
        "description": "Vehicles, drivers, assignments, service bookings, status transitions, cost entries",
    },
    Intent.ANALYTICS: {
        "agent": "analytics_agent",
        "owner": "Member 4",
        "description": "Aggregated fleet statistics, cost summaries by vehicle/month, cost listings",
    },
    Intent.AUTOMATION: {
        "agent": "automation_agent",
        "owner": "Member 6",
        "description": "Due service detection (within 7 days or overdue), maintenance alerts, notifications",
    },
    Intent.MULTI_AGENT: {
        "agent": "master_agent",
        "owner": "Member 1",
        "description": "Cross-domain workflows requiring coordination between multiple specialist agents",
    },
    Intent.UNCLEAR: {
        "agent": "master_agent",
        "owner": "Member 1",
        "description": "Vague or incomplete requests requiring a single clarifying question",
    },
}


# 16 standard benchmark messages demonstrating routing table coverage
ROUTING_EXAMPLES: list[dict[str, Any]] = [
    # Vehicle Operations
    {
        "message": "Which vehicles are currently available?",
        "expected_intent": Intent.VEHICLE_OPERATIONS,
        "expected_agents": ["vehicle_agent"],
    },
    {
        "message": "Show me all registered drivers.",
        "expected_intent": Intent.VEHICLE_OPERATIONS,
        "expected_agents": ["vehicle_agent"],
    },
    {
        "message": "Assign vehicle 11 to driver 1.",
        "expected_intent": Intent.VEHICLE_OPERATIONS,
        "expected_agents": ["vehicle_agent"],
    },
    {
        "message": "Release assignment 2.",
        "expected_intent": Intent.VEHICLE_OPERATIONS,
        "expected_agents": ["vehicle_agent"],
    },
    {
        "message": "Book an oil change service for vehicle 3.",
        "expected_intent": Intent.VEHICLE_OPERATIONS,
        "expected_agents": ["vehicle_agent"],
    },
    {
        "message": "Update service record 1 status to completed.",
        "expected_intent": Intent.VEHICLE_OPERATIONS,
        "expected_agents": ["vehicle_agent"],
    },
    {
        "message": "Log a fuel cost of $65 for vehicle 2.",
        "expected_intent": Intent.VEHICLE_OPERATIONS,
        "expected_agents": ["vehicle_agent"],
    },
    # Analytics
    {
        "message": "What are the overall fleet statistics and vehicle counts?",
        "expected_intent": Intent.ANALYTICS,
        "expected_agents": ["analytics_agent"],
    },
    {
        "message": "Give me the total expense summary grouped by vehicle and month.",
        "expected_intent": Intent.ANALYTICS,
        "expected_agents": ["analytics_agent"],
    },
    {
        "message": "Show cost entries for vehicle 4.",
        "expected_intent": Intent.ANALYTICS,
        "expected_agents": ["analytics_agent"],
    },
    # Automation
    {
        "message": "Which vehicles are due for service or overdue?",
        "expected_intent": Intent.AUTOMATION,
        "expected_agents": ["automation_agent"],
    },
    {
        "message": "Check overdue vehicles and send maintenance alerts.",
        "expected_intent": Intent.AUTOMATION,
        "expected_agents": ["automation_agent"],
    },
    {
        "message": "List vehicles due for maintenance within the next 7 days.",
        "expected_intent": Intent.AUTOMATION,
        "expected_agents": ["automation_agent"],
    },
    # Multi-Agent
    {
        "message": "Show due vehicles and book services for them.",
        "expected_intent": Intent.MULTI_AGENT,
        "expected_agents": ["automation_agent", "vehicle_agent"],
    },
    {
        "message": "List available vans and give me the total costs summary.",
        "expected_intent": Intent.MULTI_AGENT,
        "expected_agents": ["vehicle_agent", "analytics_agent"],
    },
    # Unclear
    {
        "message": "Update it please.",
        "expected_intent": Intent.UNCLEAR,
        "expected_agents": [],
    },
    {
        "message": "Check the status.",
        "expected_intent": Intent.UNCLEAR,
        "expected_agents": [],
    },
]


def classify_intent(message: str, context: Optional[dict[str, Any]] = None) -> RouteDecision:
    """Classify user message into a fixed intent and route to agent(s).
    
    Handles:
    - Single-agent requests
    - Multi-agent requests (e.g. 'show due vehicles and book services')
    - Unclear requests (asks 1 clarifying question)
    """
    text = (message or "").strip().lower()

    # 1. Unclear / Too short / Ambiguous requests
    if len(text.split()) <= 3:
        unclear_patterns = [
            r"^(update|do|check|change|fix|run|show)\s+(it|this|that|status)(\s+please)?\.?$",
            r"^(status|help|service|car|driver)\.?$",
            r"^(please\s+)?(do\s+it|update\s+it|check\s+it)\.?$",
        ]
        for pat in unclear_patterns:
            if re.match(pat, text):
                return RouteDecision(
                    intent=Intent.UNCLEAR,
                    target_agents=[],
                    confidence=0.95,
                    reasoning="Request lacks essential details (vehicle ID, driver ID, or specific action).",
                    clarifying_question="Could you please specify which vehicle, driver, or service record you would like to view or update?",
                )

    if not text:
        return RouteDecision(
            intent=Intent.UNCLEAR,
            target_agents=[],
            confidence=1.0,
            reasoning="Empty message.",
            clarifying_question="How can I assist you with vehicle management today?",
        )

    # 2. Check for Multi-Agent coordination patterns
    # (requests combining due/alert check with booking/assigning, or ops with analytics)
    has_due_check = any(w in text for w in ["due for service", "due vehicles", "overdue", "due soon", "maintenance alert"])
    has_booking = any(w in text for w in ["book", "service booking", "schedule service"])
    has_cost_summary = any(w in text for w in ["costs summary", "cost summary", "expense summary", "total expense"])
    has_vehicle_ops = any(w in text for w in ["available", "assign", "release", "list vehicles", "drivers"])

    if (has_due_check and has_booking) or (has_cost_summary and has_vehicle_ops and ("and" in text or "then" in text)):
        agents = []
        if has_due_check:
            agents.append("automation_agent")
        if has_booking or has_vehicle_ops:
            agents.append("vehicle_agent")
        if has_cost_summary:
            agents.append("analytics_agent")

        return RouteDecision(
            intent=Intent.MULTI_AGENT,
            target_agents=agents,
            confidence=0.9,
            reasoning=f"Request spans multiple specialist domains: {', '.join(agents)}",
        )

    # 3. Automation Agent patterns: due services, overdue, alerts
    automation_keywords = [
        "due for service",
        "due-service",
        "due service",
        "overdue",
        "services due",
        "maintenance alert",
        "send maintenance alerts",
        "trigger service alert",
        "next 7 days",
    ]
    if any(kw in text for kw in automation_keywords):
        return RouteDecision(
            intent=Intent.AUTOMATION,
            target_agents=["automation_agent"],
            confidence=0.95,
            reasoning="Query targets service due date detection or maintenance alerts.",
        )

    # 4. Analytics Agent patterns: summary stats, cost summaries, financial aggregations
    analytics_keywords = [
        "fleet statistics",
        "stats summary",
        "stats/summary",
        "overall statistics",
        "vehicle counts",
        "cost summary",
        "costs summary",
        "costs/summary",
        "expense summary",
        "total expense",
        "cost entries",
        "grouped by vehicle",
        "by month",
    ]
    if any(kw in text for kw in analytics_keywords):
        return RouteDecision(
            intent=Intent.ANALYTICS,
            target_agents=["analytics_agent"],
            confidence=0.95,
            reasoning="Query asks for aggregated stats or cost summaries.",
        )

    # 5. Vehicle Operations Agent patterns: vehicles, drivers, assignments, services, costs
    ops_keywords = [
        "available",
        "driver",
        "assign",
        "release",
        "book",
        "service record",
        "service status",
        "log cost",
        "log a fuel",
        "log a service",
        "vehicle",
        "car",
        "van",
        "truck",
        "bike",
        "history",
    ]
    if any(kw in text for kw in ops_keywords):
        return RouteDecision(
            intent=Intent.VEHICLE_OPERATIONS,
            target_agents=["vehicle_agent"],
            confidence=0.9,
            reasoning="Query involves operational vehicle, driver, assignment, or service data.",
        )

    # Fallback to Unclear if unable to map
    return RouteDecision(
        intent=Intent.UNCLEAR,
        target_agents=[],
        confidence=0.5,
        reasoning="Message does not match known fleet operations, analytics, or automation intents.",
        clarifying_question="I'm here to help with vehicle operations, analytics, or service maintenance alerts. Could you clarify your request?",
    )
