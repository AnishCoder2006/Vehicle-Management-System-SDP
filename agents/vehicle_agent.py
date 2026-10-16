"""Vehicle Operations Agent (Member 3).

Handles:
- Vehicle listing and details
- Driver directory
- Driver assignments (requires confirmation)
- Assignment release (requires confirmation)
- Service bookings (requires confirmation)
- Service status progression: pending -> in_progress -> completed (requires confirmation)
- Cost logging (requires confirmation)
"""

import re
from typing import Optional

from agents.errors import get_agent_logger, handle_agent_error, set_current_request_id
from agents.schemas import AgentRequest, AgentResponse
from agents.tools import operations
from agents.tools.models import ConfirmationRequiredOutput

logger = get_agent_logger("vehicle_agent")


def run_vehicle_agent(request: AgentRequest) -> AgentResponse:
    """Entrypoint for the Vehicle Operations Agent.
    
    Accepts standardized AgentRequest and returns AgentResponse.
    Working on mock tools out of the box.
    """
    req_id = set_current_request_id(request.context.get("request_id"))
    logger.info(f"Processing request: '{request.message}'", extra={"request_id": req_id})
    tools_called: list[str] = []

    try:
        # TODO (Member 3): Replace or augment this rule-based router with your LangChain / LangGraph
        # LLM agent loop (e.g. create_react_agent or custom state graph with VEHICLE_SYSTEM_PROMPT).
        text = request.message.lower().strip()
        confirmed = bool(request.context.get("confirmed", False))

        # 1. Assignment creation: e.g. "Assign vehicle 11 to driver 1"
        assign_match = re.search(r"assign\s+vehicle\s+(\d+)\s+to\s+driver\s+(\d+)", text)
        if assign_match:
            v_id = int(assign_match.group(1))
            d_id = int(assign_match.group(2))
            tools_called.append("create_assignment")
            result = operations.create_assignment(vehicle_id=v_id, driver_id=d_id, confirmed=confirmed)

            if isinstance(result, ConfirmationRequiredOutput):
                return AgentResponse(
                    status="needs_confirmation",
                    answer=f"You are about to assign vehicle {v_id} to driver {d_id}. {result.summary}. Would you like to proceed?",
                    data=result.model_dump(),
                    agent_used="vehicle_agent",
                    tools_called=tools_called,
                )
            return AgentResponse(
                status="success",
                answer=f"Vehicle {v_id} successfully assigned to driver {d_id} (Assignment #{result.id}).",
                data=result.model_dump(),
                agent_used="vehicle_agent",
                tools_called=tools_called,
            )

        # 2. Assignment release: e.g. "Release assignment 2"
        release_match = re.search(r"release\s+assignment\s+(\d+)", text)
        if release_match:
            a_id = int(release_match.group(1))
            tools_called.append("release_assignment")
            result = operations.release_assignment(id=a_id, confirmed=confirmed)

            if isinstance(result, ConfirmationRequiredOutput):
                return AgentResponse(
                    status="needs_confirmation",
                    answer=f"You are about to release assignment #{a_id}. Vehicle status will revert to 'available'. Please confirm to execute.",
                    data=result.model_dump(),
                    agent_used="vehicle_agent",
                    tools_called=tools_called,
                )
            return AgentResponse(
                status="success",
                answer=f"Assignment #{a_id} has been released. Vehicle is now available.",
                data=result.model_dump(),
                agent_used="vehicle_agent",
                tools_called=tools_called,
            )

        # 3. Update Service Status: e.g. "Update service record 1 status to completed"
        status_match = re.search(r"update\s+service\s+(?:record\s+)?(\d+)\s+status\s+to\s+([a-z_]+)", text)
        if status_match:
            s_id = int(status_match.group(1))
            target_status = status_match.group(2)
            tools_called.append("update_service_status")
            result = operations.update_service_status(id=s_id, status=target_status, confirmed=confirmed)

            if isinstance(result, ConfirmationRequiredOutput):
                return AgentResponse(
                    status="needs_confirmation",
                    answer=f"{result.summary} Please confirm this status transition.",
                    data=result.model_dump(),
                    agent_used="vehicle_agent",
                    tools_called=tools_called,
                )
            return AgentResponse(
                status="success",
                answer=f"Service record #{s_id} status updated to '{target_status}'.",
                data=result.model_dump(),
                agent_used="vehicle_agent",
                tools_called=tools_called,
            )

        # 4. Service booking: e.g. "Book an oil change service for vehicle 3"
        book_match = re.search(r"book\s+(?:an?\s+)?(.+?)\s+service\s+for\s+vehicle\s+(\d+)", text)
        if book_match:
            svc_type = book_match.group(1).title()
            v_id = int(book_match.group(2))
            cust_name = request.context.get("customer_name", "Fleet Operations")
            tools_called.append("create_service")
            result = operations.create_service(
                vehicle_id=v_id,
                customer_name=cust_name,
                service_type=svc_type,
                description=f"Booked via agent: {svc_type}",
                confirmed=confirmed,
            )
            if isinstance(result, ConfirmationRequiredOutput):
                return AgentResponse(
                    status="needs_confirmation",
                    answer=f"{result.summary} Please confirm to complete booking.",
                    data=result.model_dump(),
                    agent_used="vehicle_agent",
                    tools_called=tools_called,
                )
            return AgentResponse(
                status="success",
                answer=f"Service booking #{result.id} successfully created for vehicle {v_id}.",
                data=result.model_dump(),
                agent_used="vehicle_agent",
                tools_called=tools_called,
            )

        # 5. Log cost entry: e.g. "Log a fuel cost of $65 for vehicle 2"
        cost_match = re.search(r"log\s+(?:a\s+)?(fuel|service|parts)\s+cost\s+of\s+\$?(\d+(?:\.\d+)?)\s+for\s+vehicle\s+(\d+)", text)
        if cost_match:
            cat = cost_match.group(1)
            amt = float(cost_match.group(2))
            v_id = int(cost_match.group(3))
            tools_called.append("create_cost")
            result = operations.create_cost(
                vehicle_id=v_id,
                category=cat,
                amount=amt,
                description=f"{cat.capitalize()} logged via agent",
                confirmed=confirmed,
            )
            if isinstance(result, ConfirmationRequiredOutput):
                return AgentResponse(
                    status="needs_confirmation",
                    answer=f"{result.summary} Please confirm to save this cost record.",
                    data=result.model_dump(),
                    agent_used="vehicle_agent",
                    tools_called=tools_called,
                )
            return AgentResponse(
                status="success",
                answer=f"Cost entry #{result.id} (${amt:.2f} {cat}) logged for vehicle {v_id}.",
                data=result.model_dump(),
                agent_used="vehicle_agent",
                tools_called=tools_called,
            )

        # 6. Read: Drivers list
        if "drivers" in text:
            tools_called.append("get_drivers")
            drivers = operations.get_drivers()
            if not drivers:
                return AgentResponse(
                    status="success",
                    answer="No registered drivers found in the system.",
                    data=[],
                    agent_used="vehicle_agent",
                    tools_called=tools_called,
                )
            names = [f"{d.name} (ID: {d.id}, License: {d.license_number})" for d in drivers]
            return AgentResponse(
                status="success",
                answer=f"Found {len(drivers)} registered drivers: {', '.join(names)}.",
                data=[d.model_dump() for d in drivers],
                agent_used="vehicle_agent",
                tools_called=tools_called,
            )

        # 7. Read: Available vehicles (or filtered by type, e.g. available vans)
        if "available" in text:
            # Check if specific vehicle type is mentioned
            v_type = None
            for t in ["car", "van", "truck", "bike"]:
                if t in text:
                    v_type = t
                    break
            
            if v_type:
                tools_called.append("get_vehicles")
                vehicles = operations.get_vehicles(status="available", vehicle_type=v_type)
            else:
                tools_called.append("get_available_vehicles")
                vehicles = operations.get_available_vehicles()

            if not vehicles:
                type_msg = f" of type '{v_type}'" if v_type else ""
                return AgentResponse(
                    status="success",
                    answer=f"No available vehicles found{type_msg}.",
                    data=[],
                    agent_used="vehicle_agent",
                    tools_called=tools_called,
                )
            summary_list = [f"{v.make or ''} {v.model or ''} (Plate: {v.plate_number}, ID: {v.id})" for v in vehicles]
            return AgentResponse(
                status="success",
                answer=f"Found {len(vehicles)} available vehicle(s): {', '.join(summary_list)}.",
                data=[v.model_dump() for v in vehicles],
                agent_used="vehicle_agent",
                tools_called=tools_called,
            )

        # 8. Read: Vehicle history
        hist_match = re.search(r"history\s+for\s+vehicle\s+(\d+)", text)
        if hist_match:
            v_id = int(hist_match.group(1))
            tools_called.append("get_vehicle_history")
            hist = operations.get_vehicle_history(v_id)
            return AgentResponse(
                status="success",
                answer=f"Vehicle {v_id} history: {len(hist.service_records)} service records, {len(hist.cost_logs)} cost logs.",
                data=hist.model_dump(),
                agent_used="vehicle_agent",
                tools_called=tools_called,
            )

        # 9. General vehicles listing
        tools_called.append("get_vehicles")
        all_vehicles = operations.get_vehicles()
        return AgentResponse(
            status="success",
            answer=f"Total {len(all_vehicles)} vehicles listed in fleet.",
            data=[v.model_dump() for v in all_vehicles],
            agent_used="vehicle_agent",
            tools_called=tools_called,
        )

    except Exception as exc:
        return handle_agent_error(
            exc=exc,
            agent_name="vehicle_agent",
            tools_called=tools_called,
            request_id=req_id,
        )
