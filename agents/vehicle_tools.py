"""Vehicle Operations tool extensions + tool catalog (Member 3).

Adds the vehicle-lifecycle tools that the shared 18-tool registry does not cover
(Vehicle CRUD and maintenance), and exposes one catalog that the Vehicle
Operations Agent uses for both rule-based dispatch and LLM function calling.

Extra tools (same mock/live + confirmation conventions as agents/tools/operations.py):
- find_vehicle_by_plate(plate_number)            read   -> GET /vehicles (filtered)
- get_vehicle_maintenance(id)                    read   -> GET /vehicles/{id} + /history
- create_vehicle(..., confirmed)                 write  -> POST /vehicles
- update_vehicle(id, ..., confirmed)             write  -> PUT /vehicles/{id}

These live here (not in agents/tools/registry.py) so the shared registry stays
exactly the 18 backend-endpoint wrappers that Member 1's tests pin.
"""

from datetime import date, timedelta
from typing import Any, Callable, Optional, Union

from pydantic import BaseModel, Field

from agents.tools import operations
from agents.tools.base import ToolError, is_mock_enabled
from agents.tools.client import request_api
from agents.tools.mock_data import MOCK_STORE
from agents.tools.models import (
    ConfirmationRequiredOutput,
    VehicleOutput,
    VehicleStatus,
    VehicleType,
)
from agents.tools.registry import EmptyInput, list_tools_for_agent

DUE_SOON_DAYS = 7


# ---------------------------------------------------------------------------
# Input models for the extension tools
# ---------------------------------------------------------------------------
class FindVehicleByPlateInput(BaseModel):
    plate_number: str = Field(..., min_length=3, description="License plate, e.g. KBZ-4567 (case-insensitive)")


class GetVehicleMaintenanceInput(BaseModel):
    id: int = Field(..., description="Vehicle database ID")


class CreateVehicleInput(BaseModel):
    plate_number: str = Field(..., min_length=3, max_length=20, description="Unique license plate")
    make: Optional[str] = Field(None, description="Manufacturer, e.g. Toyota")
    model: Optional[str] = Field(None, description="Model, e.g. HiAce")
    year: Optional[int] = Field(None, ge=1990, le=2030, description="Manufacture year (1990-2030)")
    vehicle_type: VehicleType = Field("car", description="car, van, truck or bike")
    mileage: int = Field(0, ge=0, description="Odometer reading")
    next_service_date: Optional[date] = Field(None, description="Next scheduled service date (YYYY-MM-DD)")
    confirmed: bool = Field(False, description="Explicit confirmation flag for write execution")


class UpdateVehicleInput(BaseModel):
    id: int = Field(..., description="Vehicle database ID")
    plate_number: Optional[str] = Field(None, min_length=3, max_length=20)
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = Field(None, ge=1990, le=2030)
    vehicle_type: Optional[VehicleType] = None
    mileage: Optional[int] = Field(None, ge=0, description="New odometer reading (cannot decrease)")
    next_service_date: Optional[date] = Field(None, description="New next service date (YYYY-MM-DD)")
    confirmed: bool = Field(False, description="Explicit confirmation flag for write execution")


class VehicleMaintenanceOutput(BaseModel):
    vehicle: VehicleOutput
    next_service_date: Optional[date]
    days_until_service: Optional[int]
    maintenance_state: str  # overdue | due_soon | ok | unscheduled
    open_service_records: list[dict[str, Any]]
    completed_service_count: int
    total_cost_logged: float


# ---------------------------------------------------------------------------
# Extension tool implementations
# ---------------------------------------------------------------------------
def _normalize_plate(plate: str) -> str:
    return plate.strip().upper()


def find_vehicle_by_plate(plate_number: str) -> VehicleOutput:
    """Look up a vehicle by license plate (the backend has no plate filter, so filter client-side)."""
    plate = _normalize_plate(plate_number)
    match = next((v for v in operations.get_vehicles() if v.plate_number.upper() == plate), None)
    if match is None:
        raise ToolError(f"No vehicle with plate number '{plate}' found", status_code=404, endpoint="/vehicles")
    return match


def get_vehicle_maintenance(id: int) -> VehicleMaintenanceOutput:
    """Maintenance snapshot: next service date, days left, open service jobs, cost total."""
    vehicle = operations.get_vehicle_by_id(id)
    history = operations.get_vehicle_history(id)

    days: Optional[int] = None
    if vehicle.next_service_date is None:
        state = "unscheduled"
    else:
        days = (vehicle.next_service_date - date.today()).days
        state = "overdue" if days < 0 else ("due_soon" if days <= DUE_SOON_DAYS else "ok")

    open_records = [s.model_dump(mode="json") for s in history.service_records if s.status != "completed"]
    return VehicleMaintenanceOutput(
        vehicle=vehicle,
        next_service_date=vehicle.next_service_date,
        days_until_service=days,
        maintenance_state=state,
        open_service_records=open_records,
        completed_service_count=sum(1 for s in history.service_records if s.status == "completed"),
        total_cost_logged=round(sum(c.amount for c in history.cost_logs), 2),
    )


def create_vehicle(
    plate_number: str,
    make: Optional[str] = None,
    model: Optional[str] = None,
    year: Optional[int] = None,
    vehicle_type: str = "car",
    mileage: int = 0,
    next_service_date: Optional[date] = None,
    confirmed: bool = False,
) -> Union[VehicleOutput, ConfirmationRequiredOutput]:
    """Register a new fleet vehicle (status starts as 'available'). Requires confirmation."""
    plate = _normalize_plate(plate_number)
    if any(v.plate_number.upper() == plate for v in operations.get_vehicles()):
        raise ToolError(f"Vehicle with plate number '{plate}' already exists", status_code=409, endpoint="/vehicles")

    payload = {
        "plate_number": plate,
        "make": make,
        "model": model,
        "year": year,
        "vehicle_type": vehicle_type,
        "mileage": mileage,
        "status": "available",
        "next_service_date": str(next_service_date) if next_service_date else None,
    }

    if not confirmed:
        desc = " ".join(str(p) for p in (year, make, model) if p) or "vehicle"
        due = f", next service {next_service_date}" if next_service_date else ""
        return ConfirmationRequiredOutput(
            action="create_vehicle",
            summary=f"Register new {vehicle_type} '{desc}' with plate {plate} (mileage {mileage}{due}). "
                    f"It will start with status 'available'.",
            parameters=payload,
            precheck_passed=True,
        )

    if is_mock_enabled():
        new = {**payload, "id": max((v["id"] for v in MOCK_STORE["vehicles"]), default=0) + 1,
               "next_service_date": next_service_date}
        MOCK_STORE["vehicles"].append(new)
        return VehicleOutput.model_validate(new)

    return VehicleOutput.model_validate(request_api("POST", "/vehicles", json_data=payload))


def update_vehicle(
    id: int,
    plate_number: Optional[str] = None,
    make: Optional[str] = None,
    model: Optional[str] = None,
    year: Optional[int] = None,
    vehicle_type: Optional[str] = None,
    mileage: Optional[int] = None,
    next_service_date: Optional[date] = None,
    confirmed: bool = False,
) -> Union[VehicleOutput, ConfirmationRequiredOutput]:
    """Update vehicle details (partial). Status is deliberately NOT editable here:
    it only changes through assignment and service workflows. Requires confirmation."""
    current = operations.get_vehicle_by_id(id)
    changes: dict[str, Any] = {
        k: v for k, v in {
            "plate_number": _normalize_plate(plate_number) if plate_number else None,
            "make": make, "model": model, "year": year, "vehicle_type": vehicle_type,
            "mileage": mileage, "next_service_date": next_service_date,
        }.items() if v is not None and v != getattr(current, k)
    }
    if not changes:
        raise ToolError(f"No changes to apply to vehicle {id}", status_code=400, endpoint=f"/vehicles/{id}")
    if "mileage" in changes and changes["mileage"] < current.mileage:
        raise ToolError(
            f"Mileage cannot decrease (current {current.mileage}, requested {changes['mileage']})",
            status_code=400, endpoint=f"/vehicles/{id}",
        )
    if "plate_number" in changes and any(
        v.plate_number.upper() == changes["plate_number"] and v.id != id for v in operations.get_vehicles()
    ):
        raise ToolError(f"Vehicle with plate number '{changes['plate_number']}' already exists",
                        status_code=409, endpoint=f"/vehicles/{id}")

    if not confirmed:
        diff = ", ".join(f"{k}: {getattr(current, k)} -> {v}" for k, v in changes.items())
        return ConfirmationRequiredOutput(
            action="update_vehicle",
            summary=f"Update vehicle {id} ({current.plate_number}): {diff}.",
            parameters={"id": id, **{k: str(v) if isinstance(v, date) else v for k, v in changes.items()}},
            precheck_passed=True,
        )

    if is_mock_enabled():
        for v in MOCK_STORE["vehicles"]:
            if v["id"] == id:
                v.update(changes)
                return VehicleOutput.model_validate(v)

    body = {k: str(v) if isinstance(v, date) else v for k, v in changes.items()}
    return VehicleOutput.model_validate(request_api("PUT", f"/vehicles/{id}", json_data=body))


# ---------------------------------------------------------------------------
# Tool catalog used by the Vehicle Operations Agent
# ---------------------------------------------------------------------------
class AgentTool(BaseModel):
    name: str
    description: str
    action_type: str  # read | write
    input_model: type[BaseModel]
    func: Callable[..., Any]

    model_config = {"arbitrary_types_allowed": True}

    def openai_spec(self) -> dict:
        """OpenAI function-calling spec. `confirmed` is never exposed to the LLM:
        the agent runtime alone decides when a write is confirmed."""
        schema = self.input_model.model_json_schema()
        schema.get("properties", {}).pop("confirmed", None)
        if "required" in schema:
            schema["required"] = [r for r in schema["required"] if r != "confirmed"]
        schema.pop("title", None)
        return {"type": "function",
                "function": {"name": self.name, "description": self.description, "parameters": schema}}


def _build_catalog() -> dict[str, AgentTool]:
    catalog = {
        t.name: AgentTool(name=t.name, description=t.description, action_type=t.action_type,
                          input_model=t.input_model, func=t.func)
        for t in list_tools_for_agent("vehicle_agent")
    }
    extras = [
        AgentTool(name="find_vehicle_by_plate", action_type="read", input_model=FindVehicleByPlateInput,
                  func=find_vehicle_by_plate,
                  description="Find a vehicle by its license plate number. Use when the user gives a plate instead of an ID."),
        AgentTool(name="get_vehicle_maintenance", action_type="read", input_model=GetVehicleMaintenanceInput,
                  func=get_vehicle_maintenance,
                  description="Maintenance snapshot for one vehicle: next service date, days until due, "
                              "overdue/due_soon/ok state, open service jobs, completed services, total cost logged."),
        AgentTool(name="get_due_service_vehicles", action_type="read", input_model=EmptyInput,
                  func=operations.get_due_service_vehicles,
                  description="List vehicles whose next service date is within 7 days or overdue "
                              "(use before planning maintenance bookings)."),
        AgentTool(name="create_vehicle", action_type="write", input_model=CreateVehicleInput, func=create_vehicle,
                  description="Register a new vehicle in the fleet. Requires user confirmation."),
        AgentTool(name="update_vehicle", action_type="write", input_model=UpdateVehicleInput, func=update_vehicle,
                  description="Update vehicle details such as mileage, next_service_date, make/model or plate. "
                              "Cannot change status (use assignments/services for that). Requires user confirmation."),
    ]
    catalog.update({t.name: t for t in extras})
    return catalog


VEHICLE_TOOLS: dict[str, AgentTool] = _build_catalog()
WRITE_ACTIONS = {name for name, t in VEHICLE_TOOLS.items() if t.action_type == "write"}


def call_tool(name: str, args: dict[str, Any], confirmed: bool = False) -> Any:
    """Validate args against the tool's Pydantic input model, then invoke it.

    For write tools the `confirmed` flag comes ONLY from the caller (the agent
    runtime), never from `args`, so an LLM cannot self-confirm a write.
    Raises pydantic.ValidationError, ToolError, or KeyError for unknown tools.
    """
    tool = VEHICLE_TOOLS[name]
    clean = {k: v for k, v in args.items() if k != "confirmed"}
    validated = tool.input_model.model_validate(clean)
    kwargs = validated.model_dump(exclude={"confirmed"}, exclude_unset=True)
    if tool.action_type == "write":
        return tool.func(**kwargs, confirmed=confirmed)
    return tool.func(**kwargs)


def to_jsonable(result: Any) -> Any:
    """Convert tool outputs (Pydantic models / lists of them) into JSON-safe data."""
    if isinstance(result, BaseModel):
        return result.model_dump(mode="json")
    if isinstance(result, list):
        return [to_jsonable(r) for r in result]
    return result
