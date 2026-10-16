"""Master Orchestrator Agent (Member 1 - AI/Agent Architect).

Orchestrates the multi-agent system using LangGraph:
- Reads user message
- Classifies intent using the router
- Handles unclear queries with a single clarifying question
- Dispatches to specialist agents (vehicle_agent, analytics_agent, automation_agent)
- Aggregates multi-agent answers into a unified AgentResponse
- Never accesses the backend database or calls API tools directly
"""

from typing import Any, Optional, TypedDict
from langgraph.graph import END, StateGraph

from agents.analytics_agent import run_analytics_agent
from agents.automation_agent import run_automation_agent
from agents.errors import get_agent_logger, handle_agent_error, set_current_request_id
from agents.router import Intent, RouteDecision, classify_intent
from agents.schemas import AgentRequest, AgentResponse
from agents.vehicle_agent import run_vehicle_agent

logger = get_agent_logger("master_agent")


# LangGraph State Schema
class MasterState(TypedDict):
    request: AgentRequest
    request_id: str
    route_decision: Optional[RouteDecision]
    specialist_responses: list[AgentResponse]
    final_response: Optional[AgentResponse]


def router_node(state: MasterState) -> dict[str, Any]:
    """Node: Classifies user intent into fixed categories."""
    req = state["request"]
    decision = classify_intent(req.message, req.context)
    logger.info(
        f"Router classified intent: {decision.intent.value} (agents: {decision.target_agents})",
        extra={"request_id": state["request_id"]},
    )
    return {"route_decision": decision}


def route_branch(state: MasterState) -> str:
    """Conditional Edge: Determines next step based on router decision."""
    decision = state["route_decision"]
    if not decision or decision.intent == Intent.UNCLEAR:
        return "clarification_node"
    return "dispatch_specialists_node"


def clarification_node(state: MasterState) -> dict[str, Any]:
    """Node: Generates a single targeted clarifying question for unclear requests."""
    decision = state["route_decision"]
    question = (
        decision.clarifying_question
        if decision and decision.clarifying_question
        else "Could you please clarify your request regarding vehicles, drivers, or maintenance?"
    )
    resp = AgentResponse(
        status="partial",
        answer=question,
        data=None,
        agent_used="master_agent",
        tools_called=[],
        error=None,
    )
    return {"final_response": resp}


def dispatch_specialists_node(state: MasterState) -> dict[str, Any]:
    """Node: Dispatches task to designated specialist agents."""
    decision = state["route_decision"]
    req = state["request"]
    responses: list[AgentResponse] = []

    target_agents = decision.target_agents if decision else []

    for agent_name in target_agents:
        if agent_name == "vehicle_agent":
            r = run_vehicle_agent(req)
            responses.append(r)
        elif agent_name == "analytics_agent":
            r = run_analytics_agent(req)
            responses.append(r)
        elif agent_name == "automation_agent":
            r = run_automation_agent(req)
            responses.append(r)

    return {"specialist_responses": responses}


def aggregator_node(state: MasterState) -> dict[str, Any]:
    """Node: Merges outputs from one or more specialists into unified AgentResponse."""
    responses = state["specialist_responses"]

    if not responses:
        resp = AgentResponse(
            status="error",
            answer="No specialist agent was able to process this request.",
            agent_used="master_agent",
            tools_called=[],
            error="Empty specialist response",
        )
        return {"final_response": resp}

    # If single specialist was invoked, preserve its exact status and data
    if len(responses) == 1:
        single = responses[0]
        return {
            "final_response": AgentResponse(
                status=single.status,
                answer=single.answer,
                data=single.data,
                agent_used=single.agent_used or "master_agent",
                tools_called=single.tools_called,
                error=single.error,
            )
        }

    # Multi-agent coordination: merge answers, tool lists, and structured data
    combined_answers = []
    all_tools: list[str] = []
    combined_data: dict[str, Any] = {}
    any_needs_confirmation = any(r.status == "needs_confirmation" for r in responses)
    any_error = any(r.status == "error" for r in responses)

    for idx, r in enumerate(responses):
        agent_key = r.agent_used or f"specialist_{idx}"
        combined_answers.append(f"[{agent_key}]: {r.answer}")
        all_tools.extend(r.tools_called)
        if r.data is not None:
            combined_data[agent_key] = r.data

    final_status = "needs_confirmation" if any_needs_confirmation else ("partial" if any_error else "success")

    resp = AgentResponse(
        status=final_status,
        answer="\n\n".join(combined_answers),
        data=combined_data if combined_data else None,
        agent_used="master_agent",
        tools_called=all_tools,
        error=None,
    )
    return {"final_response": resp}


# Build LangGraph StateGraph
def build_master_graph():
    builder = StateGraph(MasterState)
    builder.add_node("router_node", router_node)
    builder.add_node("clarification_node", clarification_node)
    builder.add_node("dispatch_specialists_node", dispatch_specialists_node)
    builder.add_node("aggregator_node", aggregator_node)

    builder.set_entry_point("router_node")
    builder.add_conditional_edges(
        "router_node",
        route_branch,
        {
            "clarification_node": "clarification_node",
            "dispatch_specialists_node": "dispatch_specialists_node",
        },
    )
    builder.add_edge("clarification_node", END)
    builder.add_edge("dispatch_specialists_node", "aggregator_node")
    builder.add_edge("aggregator_node", END)

    return builder.compile()


# Compiled LangGraph Workflow
MASTER_GRAPH = build_master_graph()


def run_master_agent(request: AgentRequest) -> AgentResponse:
    """Main entrypoint for user interaction.
    
    Accepts an AgentRequest, runs LangGraph orchestration, and returns AgentResponse.
    """
    req_id = set_current_request_id(request.context.get("request_id"))
    logger.info(f"Master Agent received: '{request.message}'", extra={"request_id": req_id})

    try:
        initial_state: MasterState = {
            "request": request,
            "request_id": req_id,
            "route_decision": None,
            "specialist_responses": [],
            "final_response": None,
        }

        final_state = MASTER_GRAPH.invoke(initial_state)
        response = final_state.get("final_response")
        if response:
            return response

        return AgentResponse(
            status="error",
            answer="Pipeline failed to produce a final response.",
            agent_used="master_agent",
            tools_called=[],
            error="Missing final_response in state",
        )

    except Exception as exc:
        return handle_agent_error(
            exc=exc,
            agent_name="master_agent",
            tools_called=[],
            request_id=req_id,
        )
