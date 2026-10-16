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
        text = request.message.lower().strip()

        # 0. Predictive maintenance — read-only ML operation
        maintenance_keywords = [
            "predict maintenance",
            "predictive maintenance",
            "maintenance prediction",
            "maintenance risk",
            "predict risk",
            "risk score",
            "failure prediction",
            "predict failure",
            "component failure",
            "breakdown risk",
            "maintenance probability",
        ]

        if any(keyword in text for keyword in maintenance_keywords):
            context = request.context or {}
            vehicle_id = context.get("vehicle_id")

            if vehicle_id is None:
                match = re.search(
                    r"\bvehicle\s+(\d+)\b",
                    text,
                )
                if match:
                    vehicle_id = int(match.group(1))

            if vehicle_id is None:
                return AgentResponse(
                    status="partial",
                    answer="Please specify a vehicle ID, for example: 'Predict maintenance risk for vehicle 0'.",
                    agent_used="analytics_agent",
                )

            features = context.get("features")

            if not isinstance(features, dict) or not features:
                return AgentResponse(
                    status="partial",
                    answer=(
                        f"I identified vehicle {vehicle_id}, but its "
                        "operational sensor features were not provided. "
                        "The model requires 106 features. No prediction was made."
                    ),
                    data={
                        "vehicle_id": vehicle_id,
                        "required_feature_count": 106,
                    },
                    agent_used="analytics_agent",
                )

            tools_called.append("predict_vehicle_maintenance")

            result = operations.predict_vehicle_maintenance(
                vehicle_id=int(vehicle_id),
                features=features,
            )

            risk = result["maintenance_risk"]
            score = float(result["risk_score"])

            return AgentResponse(
                status="success",
                answer=(
                    f"Maintenance risk for vehicle {vehicle_id}: {risk}. "
                    f"Estimated risk score: {score:.2%}. "
                    "This is a model estimate, not a guarantee of the "
                    "vehicle's mechanical condition."
                ),
                data=result,
                agent_used="analytics_agent",
                tools_called=tools_called,
            )


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


