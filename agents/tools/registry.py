"""Tool registry containing metadata, input/output schemas, and owning agent bindings.
"""

from typing import Optional
from pydantic import BaseModel

from agents.tools.base import ToolDefinition
from agents.tools.models import (
    AssignmentOutput,
    ConfirmationRequiredOutput,
    CostLogOutput,
    CostSummaryOutput,
    CreateAssignmentInput,
    CreateCostInput,
    CreateServiceInput,
    DriverOutput,
    GetAssignmentsInput,
    GetCostsInput,
    GetDriverByIdInput,
    GetServiceByIdInput,
    GetServicesInput,
    GetVehicleByIdInput,
    GetVehiclesInput,
    ReleaseAssignmentInput,
    ServiceRecordOutput,
    StatsSummaryOutput,
    UpdateServiceStatusInput,
    VehicleHistoryOutput,
    VehicleOutput,
)
from agents.tools import operations


class EmptyInput(BaseModel):
    """Empty schema for tools taking no input parameters."""
    pass


# Global Tool Registry mapping tool_name -> ToolDefinition
TOOL_REGISTRY: dict[str, ToolDefinition] = {
    # 1. GET /vehicles
    "get_vehicles": ToolDefinition(
        name="get_vehicles",
        description="List vehicles with optional filters for status ('available', 'assigned', 'in_service') and vehicle_type ('car', 'van', 'truck', 'bike').",
        endpoint="GET /vehicles",
        method="GET",
        action_type="read",
        owning_agent="vehicle_agent",
        input_model=GetVehiclesInput,
        output_model=VehicleOutput,
        func=operations.get_vehicles,
    ),
    # 2. GET /vehicles/available
    "get_available_vehicles": ToolDefinition(
        name="get_available_vehicles",
        description="List only vehicles that currently have status 'available' and are ready for assignment.",
        endpoint="GET /vehicles/available",
        method="GET",
        action_type="read",
        owning_agent="vehicle_agent",
        input_model=EmptyInput,
        output_model=VehicleOutput,
        func=operations.get_available_vehicles,
    ),
    # 3. GET /vehicles/due-service
    "get_due_service_vehicles": ToolDefinition(
        name="get_due_service_vehicles",
        description="List vehicles whose next service date is within the next 7 days or is already overdue.",
        endpoint="GET /vehicles/due-service",
        method="GET",
        action_type="read",
        owning_agent="automation_agent",
        input_model=EmptyInput,
        output_model=VehicleOutput,
        func=operations.get_due_service_vehicles,
    ),
    # 4. GET /vehicles/{id}
    "get_vehicle_by_id": ToolDefinition(
        name="get_vehicle_by_id",
        description="Retrieve complete details for a specific vehicle by its database ID.",
        endpoint="GET /vehicles/{id}",
        method="GET",
        action_type="read",
        owning_agent="vehicle_agent",
        input_model=GetVehicleByIdInput,
        output_model=VehicleOutput,
        func=operations.get_vehicle_by_id,
    ),
    # 5. GET /vehicles/{id}/history
    "get_vehicle_history": ToolDefinition(
        name="get_vehicle_history",
        description="Get service records and cost history associated with a vehicle.",
        endpoint="GET /vehicles/{id}/history",
        method="GET",
        action_type="read",
        owning_agent="vehicle_agent",
        input_model=GetVehicleByIdInput,
        output_model=VehicleHistoryOutput,
        func=operations.get_vehicle_history,
    ),
    # 6. GET /drivers
    "get_drivers": ToolDefinition(
        name="get_drivers",
        description="List all drivers in the system.",
        endpoint="GET /drivers",
        method="GET",
        action_type="read",
        owning_agent="vehicle_agent",
        input_model=EmptyInput,
        output_model=DriverOutput,
        func=operations.get_drivers,
    ),
    # 7. GET /drivers/{id}
    "get_driver_by_id": ToolDefinition(
        name="get_driver_by_id",
        description="Get details of a single driver by their database ID.",
        endpoint="GET /drivers/{id}",
        method="GET",
        action_type="read",
        owning_agent="vehicle_agent",
        input_model=GetDriverByIdInput,
        output_model=DriverOutput,
        func=operations.get_driver_by_id,
    ),
    # 8. POST /assignments
    "create_assignment": ToolDefinition(
        name="create_assignment",
        description="Assign an available vehicle to a driver. Requires confirmation before execution. Vehicle must be 'available'.",
        endpoint="POST /assignments",
        method="POST",
        action_type="write",
        owning_agent="vehicle_agent",
        input_model=CreateAssignmentInput,
        output_model=AssignmentOutput,
        func=operations.create_assignment,
    ),
    # 9. POST /assignments/{id}/release
    "release_assignment": ToolDefinition(
        name="release_assignment",
        description="Release an active assignment and return vehicle to 'available' status. Requires confirmation before execution.",
        endpoint="POST /assignments/{id}/release",
        method="POST",
        action_type="write",
        owning_agent="vehicle_agent",
        input_model=ReleaseAssignmentInput,
        output_model=AssignmentOutput,
        func=operations.release_assignment,
    ),
    # 10. GET /assignments
    "get_assignments": ToolDefinition(
        name="get_assignments",
        description="List assignments with optional filters for vehicle_id, driver_id, and is_active.",
        endpoint="GET /assignments",
        method="GET",
        action_type="read",
        owning_agent="vehicle_agent",
        input_model=GetAssignmentsInput,
        output_model=AssignmentOutput,
        func=operations.get_assignments,
    ),
    # 11. POST /services
    "create_service": ToolDefinition(
        name="create_service",
        description="Book a service for a vehicle with initial status 'pending'. Requires confirmation before execution.",
        endpoint="POST /services",
        method="POST",
        action_type="write",
        owning_agent="vehicle_agent",
        input_model=CreateServiceInput,
        output_model=ServiceRecordOutput,
        func=operations.create_service,
    ),
    # 12. GET /services
    "get_services": ToolDefinition(
        name="get_services",
        description="List service records with optional status ('pending', 'in_progress', 'completed') and vehicle_id filters.",
        endpoint="GET /services",
        method="GET",
        action_type="read",
        owning_agent="vehicle_agent",
        input_model=GetServicesInput,
        output_model=ServiceRecordOutput,
        func=operations.get_services,
    ),
    # 13. GET /services/{id}
    "get_service_by_id": ToolDefinition(
        name="get_service_by_id",
        description="Get details of a specific service record by ID.",
        endpoint="GET /services/{id}",
        method="GET",
        action_type="read",
        owning_agent="vehicle_agent",
        input_model=GetServiceByIdInput,
        output_model=ServiceRecordOutput,
        func=operations.get_service_by_id,
    ),
    # 14. PATCH /services/{id}/status
    "update_service_status": ToolDefinition(
        name="update_service_status",
        description="Update service status strictly following pending -> in_progress -> completed. Requires confirmation before execution.",
        endpoint="PATCH /services/{id}/status",
        method="PATCH",
        action_type="write",
        owning_agent="vehicle_agent",
        input_model=UpdateServiceStatusInput,
        output_model=ServiceRecordOutput,
        func=operations.update_service_status,
    ),
    # 15. POST /costs
    "create_cost": ToolDefinition(
        name="create_cost",
        description="Log an expense for a vehicle (category: 'service', 'fuel', or 'parts'). Requires confirmation before execution.",
        endpoint="POST /costs",
        method="POST",
        action_type="write",
        owning_agent="vehicle_agent",
        input_model=CreateCostInput,
        output_model=CostLogOutput,
        func=operations.create_cost,
    ),
    # 16. GET /costs
    "get_costs": ToolDefinition(
        name="get_costs",
        description="List cost entries with optional filters for vehicle_id and category ('service', 'fuel', 'parts').",
        endpoint="GET /costs",
        method="GET",
        action_type="read",
        owning_agent="analytics_agent",
        input_model=GetCostsInput,
        output_model=CostLogOutput,
        func=operations.get_costs,
    ),
    # 17. GET /costs/summary
    "get_costs_summary": ToolDefinition(
        name="get_costs_summary",
        description="Get high-level summary of costs grouped by vehicle ID, grouped by month (YYYY-MM), and grand total.",
        endpoint="GET /costs/summary",
        method="GET",
        action_type="read",
        owning_agent="analytics_agent",
        input_model=EmptyInput,
        output_model=CostSummaryOutput,
        func=operations.get_costs_summary,
    ),
    # 18. GET /stats/summary
    "get_stats_summary": ToolDefinition(
        name="get_stats_summary",
        description="Get fleet breakdown metrics: total_vehicles, available, assigned, in_service, pending_services, and services_due_soon.",
        endpoint="GET /stats/summary",
        method="GET",
        action_type="read",
        owning_agent="analytics_agent",
        input_model=EmptyInput,
        output_model=StatsSummaryOutput,
        func=operations.get_stats_summary,
    ),
}


def get_tool(name: str) -> ToolDefinition:
    """Retrieve a tool definition by name from the registry."""
    if name not in TOOL_REGISTRY:
        raise KeyError(f"Tool '{name}' is not registered in TOOL_REGISTRY")
    return TOOL_REGISTRY[name]


def list_tools_for_agent(agent_name: str) -> list[ToolDefinition]:
    """Return all tool definitions registered for a given agent."""
    return [t for t in TOOL_REGISTRY.values() if t.owning_agent == agent_name]


def list_all_tools() -> list[ToolDefinition]:
    """Return all tool definitions in the system."""
    return list(TOOL_REGISTRY.values())
