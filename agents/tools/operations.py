"""Core tool implementations wrapping backend API endpoints.

Supports mock execution (USE_MOCK_TOOLS=true) and live API calls (USE_MOCK_TOOLS=false).
Implements pre-validation and write-action safety requiring confirmation before execution.
"""

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Optional, Union

from agents.tools.base import (
    ConfirmationRequired,
    ToolError,
    is_mock_enabled,
)
from agents.tools.client import request_api
from agents.tools.mock_data import MOCK_STORE
from agents.tools.models import (
    AssignmentOutput,
    ConfirmationRequiredOutput,
    CostLogOutput,
    CostSummaryOutput,
    DriverOutput,
    ServiceRecordOutput,
    StatsSummaryOutput,
    VehicleHistoryOutput,
    VehicleOutput,
)


# --- 1. GET /vehicles ---
def get_vehicles(
    status: Optional[str] = None,
    vehicle_type: Optional[str] = None,
) -> list[VehicleOutput]:
    """List vehicles with optional filters for status and vehicle type."""
    if is_mock_enabled():
        res = MOCK_STORE["vehicles"]
        if status:
            res = [v for v in res if v["status"] == status]
        if vehicle_type:
            res = [v for v in res if v["vehicle_type"] == vehicle_type]
        return [VehicleOutput.model_validate(v) for v in res]

    data = request_api("GET", "/vehicles", params={"status": status, "vehicle_type": vehicle_type})
    return [VehicleOutput.model_validate(v) for v in data]


# --- 2. GET /vehicles/available ---
def get_available_vehicles() -> list[VehicleOutput]:
    """List only vehicles with status 'available'."""
    if is_mock_enabled():
        res = [v for v in MOCK_STORE["vehicles"] if v["status"] == "available"]
        return [VehicleOutput.model_validate(v) for v in res]

    data = request_api("GET", "/vehicles/available")
    return [VehicleOutput.model_validate(v) for v in data]


# --- 3. GET /vehicles/due-service ---
def get_due_service_vehicles() -> list[VehicleOutput]:
    """List vehicles whose next_service_date is within 7 days or overdue."""
    cutoff = date.today() + timedelta(days=7)
    if is_mock_enabled():
        res = [
            v for v in MOCK_STORE["vehicles"]
            if v["next_service_date"] is not None and v["next_service_date"] <= cutoff
        ]
        return [VehicleOutput.model_validate(v) for v in res]

    data = request_api("GET", "/vehicles/due-service")
    return [VehicleOutput.model_validate(v) for v in data]


# --- 4. GET /vehicles/{id} ---
def get_vehicle_by_id(id: int) -> VehicleOutput:
    """Get a single vehicle by its primary ID."""
    if is_mock_enabled():
        match = next((v for v in MOCK_STORE["vehicles"] if v["id"] == id), None)
        if not match:
            raise ToolError(f"Vehicle with id {id} not found", status_code=404, endpoint=f"/vehicles/{id}")
        return VehicleOutput.model_validate(match)

    data = request_api("GET", f"/vehicles/{id}")
    return VehicleOutput.model_validate(data)


# --- 5. GET /vehicles/{id}/history ---
def get_vehicle_history(id: int) -> VehicleHistoryOutput:
    """Retrieve service records and cost history for a specific vehicle."""
    # Ensure vehicle exists first
    _ = get_vehicle_by_id(id)

    if is_mock_enabled():
        services = [s for s in MOCK_STORE["services"] if s["vehicle_id"] == id]
        costs = [c for c in MOCK_STORE["costs"] if c["vehicle_id"] == id]
        return VehicleHistoryOutput(
            vehicle_id=id,
            service_records=[ServiceRecordOutput.model_validate(s) for s in services],
            cost_logs=[CostLogOutput.model_validate(c) for c in costs],
        )

    data = request_api("GET", f"/vehicles/{id}/history")
    return VehicleHistoryOutput.model_validate(data)


# --- 6. GET /drivers ---
def get_drivers() -> list[DriverOutput]:
    """List all registered drivers in the system."""
    if is_mock_enabled():
        return [DriverOutput.model_validate(d) for d in MOCK_STORE["drivers"]]

    data = request_api("GET", "/drivers")
    return [DriverOutput.model_validate(d) for d in data]


# --- 7. GET /drivers/{id} ---
def get_driver_by_id(id: int) -> DriverOutput:
    """Get driver details by ID."""
    if is_mock_enabled():
        match = next((d for d in MOCK_STORE["drivers"] if d["id"] == id), None)
        if not match:
            raise ToolError(f"Driver with id {id} not found", status_code=404, endpoint=f"/drivers/{id}")
        return DriverOutput.model_validate(match)

    data = request_api("GET", f"/drivers/{id}")
    return DriverOutput.model_validate(data)


# --- 8. POST /assignments ---
def create_assignment(
    vehicle_id: int,
    driver_id: int,
    confirmed: bool = False,
) -> Union[AssignmentOutput, ConfirmationRequiredOutput]:
    """Assign an available vehicle to a driver.
    
    Requires confirmation before execution.
    Validates that the vehicle exists and is currently 'available'.
    """
    # Pre-validation
    vehicle = get_vehicle_by_id(vehicle_id)
    driver = get_driver_by_id(driver_id)

    if vehicle.status != "available":
        raise ToolError(
            f"Vehicle with id {vehicle_id} is not available (current status: {vehicle.status})",
            status_code=400,
            endpoint="/assignments",
        )

    if not confirmed:
        summary = (
            f"Assign vehicle {vehicle_id} ({vehicle.make or ''} {vehicle.model or ''}, "
            f"plate {vehicle.plate_number}) to driver {driver_id} ({driver.name}). "
            f"Vehicle status will change from 'available' to 'assigned'."
        ).strip()
        return ConfirmationRequiredOutput(
            action="create_assignment",
            summary=summary,
            parameters={"vehicle_id": vehicle_id, "driver_id": driver_id},
            precheck_passed=True,
        )

    # Execution
    if is_mock_enabled():
        new_id = max([a["id"] for a in MOCK_STORE["assignments"]], default=0) + 1
        new_assignment = {
            "id": new_id,
            "vehicle_id": vehicle_id,
            "driver_id": driver_id,
            "assigned_at": datetime.now(),
            "released_at": None,
            "is_active": True,
        }
        MOCK_STORE["assignments"].append(new_assignment)
        # Update vehicle status in mock store
        for v in MOCK_STORE["vehicles"]:
            if v["id"] == vehicle_id:
                v["status"] = "assigned"
        return AssignmentOutput.model_validate(new_assignment)

    data = request_api("POST", "/assignments", json_data={"vehicle_id": vehicle_id, "driver_id": driver_id})
    return AssignmentOutput.model_validate(data)


# --- 9. POST /assignments/{id}/release ---
def release_assignment(
    id: int,
    confirmed: bool = False,
) -> Union[AssignmentOutput, ConfirmationRequiredOutput]:
    """Release an active vehicle assignment and return the vehicle to available status.
    
    Requires confirmation before execution.
    """
    # Pre-validation
    if is_mock_enabled():
        assignment = next((a for a in MOCK_STORE["assignments"] if a["id"] == id), None)
        if not assignment:
            raise ToolError(f"Assignment with id {id} not found", status_code=404, endpoint=f"/assignments/{id}/release")
        if not assignment["is_active"]:
            raise ToolError(f"Assignment with id {id} is already released", status_code=400, endpoint=f"/assignments/{id}/release")
        v_id = assignment["vehicle_id"]
    else:
        # Check active status via assignments list
        active_list = request_api("GET", "/assignments", params={"is_active": True})
        assignment = next((a for a in active_list if a["id"] == id), None)
        if not assignment:
            # Check if it exists at all
            all_list = request_api("GET", "/assignments")
            exists = any(a["id"] == id for a in all_list)
            if not exists:
                raise ToolError(f"Assignment with id {id} not found", status_code=404, endpoint=f"/assignments/{id}/release")
            raise ToolError(f"Assignment with id {id} is already released", status_code=400, endpoint=f"/assignments/{id}/release")
        v_id = assignment["vehicle_id"]

    if not confirmed:
        summary = f"Release assignment #{id} for vehicle {v_id}. The vehicle status will revert to 'available'."
        return ConfirmationRequiredOutput(
            action="release_assignment",
            summary=summary,
            parameters={"id": id},
            precheck_passed=True,
        )

    if is_mock_enabled():
        assignment["is_active"] = False
        assignment["released_at"] = datetime.now()
        for v in MOCK_STORE["vehicles"]:
            if v["id"] == v_id:
                v["status"] = "available"
        return AssignmentOutput.model_validate(assignment)

    data = request_api("POST", f"/assignments/{id}/release")
    return AssignmentOutput.model_validate(data)


# --- 10. GET /assignments ---
def get_assignments(
    vehicle_id: Optional[int] = None,
    driver_id: Optional[int] = None,
    is_active: Optional[bool] = None,
) -> list[AssignmentOutput]:
    """List assignments with optional filters."""
    if is_mock_enabled():
        res = MOCK_STORE["assignments"]
        if vehicle_id is not None:
            res = [a for a in res if a["vehicle_id"] == vehicle_id]
        if driver_id is not None:
            res = [a for a in res if a["driver_id"] == driver_id]
        if is_active is not None:
            res = [a for a in res if a["is_active"] == is_active]
        return [AssignmentOutput.model_validate(a) for a in res]

    data = request_api("GET", "/assignments", params={"vehicle_id": vehicle_id, "driver_id": driver_id, "is_active": is_active})
    return [AssignmentOutput.model_validate(a) for a in data]


# --- 11. POST /services ---
def create_service(
    vehicle_id: int,
    customer_name: str,
    service_type: str,
    description: Optional[str] = None,
    booked_date: Optional[date] = None,
    confirmed: bool = False,
) -> Union[ServiceRecordOutput, ConfirmationRequiredOutput]:
    """Create a new service booking with initial 'pending' status.
    
    Requires confirmation before execution.
    """
    # Pre-validation: verify vehicle exists
    vehicle = get_vehicle_by_id(vehicle_id)

    if not confirmed:
        summary = (
            f"Book '{service_type}' service for vehicle {vehicle_id} ({vehicle.plate_number}) "
            f"for customer '{customer_name}'. Initial status will be 'pending'."
        )
        return ConfirmationRequiredOutput(
            action="create_service",
            summary=summary,
            parameters={
                "vehicle_id": vehicle_id,
                "customer_name": customer_name,
                "service_type": service_type,
                "description": description,
                "booked_date": str(booked_date) if booked_date else str(date.today()),
            },
            precheck_passed=True,
        )

    b_date = booked_date or date.today()

    if is_mock_enabled():
        new_id = max([s["id"] for s in MOCK_STORE["services"]], default=0) + 1
        new_record = {
            "id": new_id,
            "vehicle_id": vehicle_id,
            "customer_name": customer_name,
            "service_type": service_type,
            "description": description,
            "status": "pending",
            "booked_date": b_date,
            "completed_date": None,
        }
        MOCK_STORE["services"].append(new_record)
        return ServiceRecordOutput.model_validate(new_record)

    payload = {
        "vehicle_id": vehicle_id,
        "customer_name": customer_name,
        "service_type": service_type,
        "description": description,
        "booked_date": str(b_date),
    }
    data = request_api("POST", "/services", json_data=payload)
    return ServiceRecordOutput.model_validate(data)


# --- 12. GET /services ---
def get_services(
    status: Optional[str] = None,
    vehicle_id: Optional[int] = None,
) -> list[ServiceRecordOutput]:
    """List service records with optional status or vehicle_id filters."""
    if is_mock_enabled():
        res = MOCK_STORE["services"]
        if status:
            res = [s for s in res if s["status"] == status]
        if vehicle_id is not None:
            res = [s for s in res if s["vehicle_id"] == vehicle_id]
        return [ServiceRecordOutput.model_validate(s) for s in res]

    data = request_api("GET", "/services", params={"status": status, "vehicle_id": vehicle_id})
    return [ServiceRecordOutput.model_validate(s) for s in data]


# --- 13. GET /services/{id} ---
def get_service_by_id(id: int) -> ServiceRecordOutput:
    """Get a service record by its ID."""
    if is_mock_enabled():
        match = next((s for s in MOCK_STORE["services"] if s["id"] == id), None)
        if not match:
            raise ToolError(f"Service record with id {id} not found", status_code=404, endpoint=f"/services/{id}")
        return ServiceRecordOutput.model_validate(match)

    data = request_api("GET", f"/services/{id}")
    return ServiceRecordOutput.model_validate(data)


# --- 14. PATCH /services/{id}/status ---
def update_service_status(
    id: int,
    status: str,
    confirmed: bool = False,
) -> Union[ServiceRecordOutput, ConfirmationRequiredOutput]:
    """Update service record status following the strict progression:
    pending -> in_progress -> completed.
    
    Requires confirmation before execution.
    """
    record = get_service_by_id(id)
    current_status = record.status
    target_status = status

    # Enforce strict progression rule: pending -> in_progress -> completed
    if current_status == "pending":
        if target_status != "in_progress":
            raise ToolError(
                f"Invalid status transition from 'pending' to '{target_status}'. Must transition to 'in_progress'.",
                status_code=400,
                endpoint=f"/services/{id}/status",
            )
    elif current_status == "in_progress":
        if target_status != "completed":
            raise ToolError(
                f"Invalid status transition from 'in_progress' to '{target_status}'. Must transition to 'completed'.",
                status_code=400,
                endpoint=f"/services/{id}/status",
            )
    elif current_status == "completed":
        raise ToolError(
            "Service record is already completed and cannot be transitioned further.",
            status_code=400,
            endpoint=f"/services/{id}/status",
        )

    if not confirmed:
        side_effect = (
            "Vehicle status will be updated to 'in_service'."
            if target_status == "in_progress"
            else "Vehicle will be marked 'available' and completion date recorded."
        )
        summary = (
            f"Transition service record #{id} for vehicle {record.vehicle_id} from "
            f"'{current_status}' to '{target_status}'. {side_effect}"
        )
        return ConfirmationRequiredOutput(
            action="update_service_status",
            summary=summary,
            parameters={"id": id, "status": target_status},
            precheck_passed=True,
        )

    if is_mock_enabled():
        for s in MOCK_STORE["services"]:
            if s["id"] == id:
                s["status"] = target_status
                if target_status == "completed":
                    s["completed_date"] = date.today()
                # Update vehicle status
                for v in MOCK_STORE["vehicles"]:
                    if v["id"] == s["vehicle_id"]:
                        if target_status == "in_progress":
                            v["status"] = "in_service"
                        elif target_status == "completed":
                            v["status"] = "available"
                return ServiceRecordOutput.model_validate(s)

    data = request_api("PATCH", f"/services/{id}/status", json_data={"status": target_status})
    return ServiceRecordOutput.model_validate(data)


# --- 15. POST /costs ---
def create_cost(
    vehicle_id: int,
    category: str,
    amount: float,
    description: Optional[str] = None,
    log_date: Optional[date] = None,
    confirmed: bool = False,
) -> Union[CostLogOutput, ConfirmationRequiredOutput]:
    """Create a new cost entry for a vehicle (category: service, fuel, parts).
    
    Requires confirmation before execution.
    """
    # Pre-validation: verify vehicle exists
    vehicle = get_vehicle_by_id(vehicle_id)

    if category not in ("service", "fuel", "parts"):
        raise ToolError(
            f"Invalid cost category '{category}'. Allowed categories: service, fuel, parts.",
            status_code=400,
            endpoint="/costs",
        )

    if amount < 0:
        raise ToolError("Cost amount must be greater than or equal to 0.", status_code=400, endpoint="/costs")

    if not confirmed:
        summary = (
            f"Log cost entry of ${amount:.2f} ({category}) for vehicle {vehicle_id} "
            f"({vehicle.plate_number}): '{description or 'No description'}'. Date: {log_date or date.today()}."
        )
        return ConfirmationRequiredOutput(
            action="create_cost",
            summary=summary,
            parameters={
                "vehicle_id": vehicle_id,
                "category": category,
                "amount": amount,
                "description": description,
                "log_date": str(log_date) if log_date else str(date.today()),
            },
            precheck_passed=True,
        )

    l_date = log_date or date.today()

    if is_mock_enabled():
        new_id = max([c["id"] for c in MOCK_STORE["costs"]], default=0) + 1
        new_cost = {
            "id": new_id,
            "vehicle_id": vehicle_id,
            "category": category,
            "amount": float(amount),
            "description": description,
            "log_date": l_date,
        }
        MOCK_STORE["costs"].append(new_cost)
        return CostLogOutput.model_validate(new_cost)

    payload = {
        "vehicle_id": vehicle_id,
        "category": category,
        "amount": amount,
        "description": description,
        "log_date": str(l_date),
    }
    data = request_api("POST", "/costs", json_data=payload)
    return CostLogOutput.model_validate(data)


# --- 16. GET /costs ---
def get_costs(
    vehicle_id: Optional[int] = None,
    category: Optional[str] = None,
) -> list[CostLogOutput]:
    """List cost entries with optional vehicle_id or category filter."""
    if is_mock_enabled():
        res = MOCK_STORE["costs"]
        if vehicle_id is not None:
            res = [c for c in res if c["vehicle_id"] == vehicle_id]
        if category:
            res = [c for c in res if c["category"] == category]
        return [CostLogOutput.model_validate(c) for c in res]

    data = request_api("GET", "/costs", params={"vehicle_id": vehicle_id, "category": category})
    return [CostLogOutput.model_validate(c) for c in data]


# --- 17. GET /costs/summary ---
def get_costs_summary() -> CostSummaryOutput:
    """Get aggregated cost summary grouped by vehicle, month (YYYY-MM), and grand total."""
    if is_mock_enabled():
        by_vehicle: dict[str, float] = defaultdict(float)
        by_month: dict[str, float] = defaultdict(float)
        grand_total = 0.0

        for log in MOCK_STORE["costs"]:
            v_key = str(log["vehicle_id"])
            m_key = log["log_date"].strftime("%Y-%m")
            amt = float(log["amount"])
            by_vehicle[v_key] += amt
            by_month[m_key] += amt
            grand_total += amt

        rounded_by_vehicle = {k: round(v, 2) for k, v in sorted(by_vehicle.items())}
        rounded_by_month = {k: round(v, 2) for k, v in sorted(by_month.items())}
        return CostSummaryOutput(
            by_vehicle=rounded_by_vehicle,
            by_month=rounded_by_month,
            grand_total=round(grand_total, 2),
        )

    data = request_api("GET", "/costs/summary")
    return CostSummaryOutput.model_validate(data)


# --- 18. GET /stats/summary ---
def get_stats_summary() -> StatsSummaryOutput:
    """Get fleet-wide high level counts and pending services summary."""
    if is_mock_enabled():
        vehicles = MOCK_STORE["vehicles"]
        services = MOCK_STORE["services"]
        cutoff = date.today() + timedelta(days=7)

        total_vehicles = len(vehicles)
        available = sum(1 for v in vehicles if v["status"] == "available")
        assigned = sum(1 for v in vehicles if v["status"] == "assigned")
        in_service = sum(1 for v in vehicles if v["status"] == "in_service")
        pending_services = sum(1 for s in services if s["status"] == "pending")
        services_due_soon = sum(
            1 for v in vehicles
            if v["next_service_date"] is not None and v["next_service_date"] <= cutoff
        )

        return StatsSummaryOutput(
            total_vehicles=total_vehicles,
            available=available,
            assigned=assigned,
            in_service=in_service,
            pending_services=pending_services,
            services_due_soon=services_due_soon,
        )

    data = request_api("GET", "/stats/summary")
    return StatsSummaryOutput.model_validate(data)
