"""Automation Agent (Member 6).

Read-only agent on fleet data:
- Monitors upcoming and overdue maintenance (/vehicles/due-service)
- Dispatches proactive alerts and notifications
"""

from datetime import date
from typing import Optional

from agents.errors import get_agent_logger, handle_agent_error, set_current_request_id
from agents.schemas import AgentRequest, AgentResponse
from agents.tools import operations

logger = get_agent_logger("automation_agent")


def run_automation_agent(request: AgentRequest) -> AgentResponse:
    """Entrypoint for the Automation Agent.
    
    Accepts standardized AgentRequest and returns AgentResponse.
    Working on mock tools out of the box.
    """
    req_id = set_current_request_id(request.context.get("request_id"))
    logger.info(f"Processing automation request: '{request.message}'", extra={"request_id": req_id})
    tools_called: list[str] = []

    try:
        # TODO (Member 6): Plug in your webhook notifications, SMS/Email alert dispatchers,
        # or automated cron triggers here.
        text = request.message.lower().strip()
        today = date.today()

        tools_called.append("get_due_service_vehicles")
        due_vehicles = operations.get_due_service_vehicles()

        if not due_vehicles:
            return AgentResponse(
                status="success",
                answer="All vehicles are currently up to date on maintenance. There are no vehicles overdue or due for service within the next 7 days.",
                data=[],
                agent_used="automation_agent",
                tools_called=tools_called,
            )

        # Categorize into overdue vs due soon
        overdue_list = []
        due_soon_list = []

        for v in due_vehicles:
            if v.next_service_date:
                days_diff = (v.next_service_date - today).days
                if days_diff < 0:
                    overdue_list.append(f"{v.plate_number} ({v.make or ''} {v.model or ''}) - OVERDUE by {abs(days_diff)} days (due: {v.next_service_date})")
                else:
                    due_soon_list.append(f"{v.plate_number} ({v.make or ''} {v.model or ''}) - Due in {days_diff} days (due: {v.next_service_date})")
            else:
                due_soon_list.append(f"{v.plate_number} ({v.make or ''} {v.model or ''}) - Service date pending")

        # Check if user requested triggering an alert
        if any(w in text for w in ["alert", "notify", "trigger"]):
            ans = (
                f"Automated Alert Dispatched: {len(due_vehicles)} vehicle(s) require scheduled maintenance "
                f"({len(overdue_list)} overdue, {len(due_soon_list)} due soon). Notifications sent to fleet managers."
            )
            return AgentResponse(
                status="success",
                answer=ans,
                data={
                    "alerts_dispatched": len(due_vehicles),
                    "overdue": overdue_list,
                    "due_soon": due_soon_list,
                },
                agent_used="automation_agent",
                tools_called=tools_called,
            )

        # Standard due service report
        items = overdue_list + due_soon_list
        bullet_points = "\n".join(f"- {item}" for item in items)
        ans = (
            f"Maintenance Alert: Found {len(due_vehicles)} vehicle(s) requiring attention:\n"
            f"{bullet_points}"
        )
        return AgentResponse(
            status="success",
            answer=ans,
            data=[v.model_dump() for v in due_vehicles],
            agent_used="automation_agent",
            tools_called=tools_called,
        )

    except Exception as exc:
        return handle_agent_error(
            exc=exc,
            agent_name="automation_agent",
            tools_called=tools_called,
            request_id=req_id,
        )
