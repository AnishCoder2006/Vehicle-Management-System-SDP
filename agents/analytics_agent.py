"""Analytics Agent (Member 4).

Read-only agent providing:
- Overall fleet metrics and counts (/stats/summary)
- Grouped expense summaries by vehicle, month, and grand total (/costs/summary)
- Filtered cost logs (/costs)
Future home for ML predictive maintenance models.
"""

import re
from typing import Optional

from agents.errors import get_agent_logger, handle_agent_error, set_current_request_id
from agents.schemas import AgentRequest, AgentResponse
from agents.tools import operations

logger = get_agent_logger("analytics_agent")


def run_analytics_agent(request: AgentRequest) -> AgentResponse:
    """Entrypoint for the Analytics Agent.
    
    Accepts standardized AgentRequest and returns AgentResponse.
    Working on mock tools out of the box.
    """
    req_id = set_current_request_id(request.context.get("request_id"))
    logger.info(f"Processing analytics request: '{request.message}'", extra={"request_id": req_id})
    tools_called: list[str] = []

    try:
        # TODO (Member 4): Integrate your ML predictive maintenance pipeline and LangGraph analytical loop here.
        text = request.message.lower().strip()

        # 1. Costs summary: e.g. "total expense summary grouped by vehicle and month"
        if any(kw in text for kw in ["cost summary", "costs summary", "expense summary", "total expense"]):
            tools_called.append("get_costs_summary")
            summary = operations.get_costs_summary()
            ans = (
                f"Fleet Financial Overview: Grand total expenses to date: ${summary.grand_total:.2f}. "
                f"Active vehicles with logged expenses: {len(summary.by_vehicle)}."
            )
            return AgentResponse(
                status="success",
                answer=ans,
                data=summary.model_dump(),
                agent_used="analytics_agent",
                tools_called=tools_called,
            )

        # 2. Filtered Cost Entries for a specific vehicle: e.g. "Show cost entries for vehicle 4"
        v_match = re.search(r"costs?\s+(?:entries\s+)?(?:for\s+)?vehicle\s+(\d+)", text)
        if v_match:
            v_id = int(v_match.group(1))
            tools_called.append("get_costs")
            logs = operations.get_costs(vehicle_id=v_id)
            if not logs:
                return AgentResponse(
                    status="success",
                    answer=f"No expense or cost records found for vehicle {v_id}.",
                    data=[],
                    agent_used="analytics_agent",
                    tools_called=tools_called,
                )
            total = sum(c.amount for c in logs)
            return AgentResponse(
                status="success",
                answer=f"Found {len(logs)} cost log(s) for vehicle {v_id} totaling ${total:.2f}.",
                data=[c.model_dump() for c in logs],
                agent_used="analytics_agent",
                tools_called=tools_called,
            )

        # 3. Overall fleet statistics: e.g. "What are the overall fleet statistics and vehicle counts?"
        if any(kw in text for kw in ["statistic", "stats", "count", "fleet"]):
            tools_called.append("get_stats_summary")
            stats = operations.get_stats_summary()
            ans = (
                f"Fleet Statistics: {stats.total_vehicles} total vehicles "
                f"({stats.available} available, {stats.assigned} assigned, {stats.in_service} in service). "
                f"Pending services: {stats.pending_services}, Services due soon or overdue: {stats.services_due_soon}."
            )
            return AgentResponse(
                status="success",
                answer=ans,
                data=stats.model_dump(),
                agent_used="analytics_agent",
                tools_called=tools_called,
            )

        # Fallback default to stats summary
        tools_called.append("get_stats_summary")
        stats = operations.get_stats_summary()
        return AgentResponse(
            status="success",
            answer=f"Fleet Summary: {stats.total_vehicles} vehicles total, {stats.available} available, {stats.services_due_soon} due for service.",
            data=stats.model_dump(),
            agent_used="analytics_agent",
            tools_called=tools_called,
        )

    except Exception as exc:
        return handle_agent_error(
            exc=exc,
            agent_name="analytics_agent",
            tools_called=tools_called,
            request_id=req_id,
        )
