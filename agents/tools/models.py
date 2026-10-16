"""Pydantic models for tool inputs and outputs.

Wraps API schemas into tool-level contracts for all agents.
"""

from datetime import date, datetime
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field, ConfigDict


# Vehicle models
VehicleType = Literal["car", "van", "truck", "bike"]
VehicleStatus = Literal["available", "assigned", "in_service"]


class VehicleOutput(BaseModel):
    id: int
    plate_number: str
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    vehicle_type: VehicleType = "car"
    mileage: int = 0
    status: VehicleStatus = "available"
    next_service_date: Optional[date] = None

    model_config = ConfigDict(from_attributes=True)


class GetVehiclesInput(BaseModel):
    status: Optional[VehicleStatus] = Field(None, description="Filter by status (available, assigned, in_service)")
    vehicle_type: Optional[VehicleType] = Field(None, description="Filter by vehicle type (car, van, truck, bike)")


class GetVehicleByIdInput(BaseModel):
    id: int = Field(..., description="Vehicle database ID", examples=[1])


# Driver models
class DriverOutput(BaseModel):
    id: int
    name: str
    phone: str
    license_number: str

    model_config = ConfigDict(from_attributes=True)


class GetDriverByIdInput(BaseModel):
    id: int = Field(..., description="Driver database ID", examples=[1])


# Assignment models
class AssignmentOutput(BaseModel):
    id: int
    vehicle_id: int
    driver_id: int
    assigned_at: datetime
    released_at: Optional[datetime] = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class CreateAssignmentInput(BaseModel):
    vehicle_id: int = Field(..., description="ID of vehicle to assign (must have status 'available')")
    driver_id: int = Field(..., description="ID of driver to receive assignment")
    confirmed: bool = Field(False, description="Explicit confirmation flag for write execution")


class ReleaseAssignmentInput(BaseModel):
    id: int = Field(..., description="Assignment ID to release")
    confirmed: bool = Field(False, description="Explicit confirmation flag for write execution")


class GetAssignmentsInput(BaseModel):
    vehicle_id: Optional[int] = Field(None, description="Filter by vehicle ID")
    driver_id: Optional[int] = Field(None, description="Filter by driver ID")
    is_active: Optional[bool] = Field(None, description="Filter by active status (true/false)")


# Service record models
ServiceStatus = Literal["pending", "in_progress", "completed"]


class ServiceRecordOutput(BaseModel):
    id: int
    vehicle_id: int
    customer_name: str
    service_type: str
    description: Optional[str] = None
    status: str
    booked_date: date
    completed_date: Optional[date] = None

    model_config = ConfigDict(from_attributes=True)


class CreateServiceInput(BaseModel):
    vehicle_id: int = Field(..., description="ID of vehicle for service")
    customer_name: str = Field(..., min_length=1, description="Customer or company requesting service")
    service_type: str = Field(..., min_length=1, description="Service type, e.g. Oil change, Brake check")
    description: Optional[str] = Field(None, description="Detailed notes on service needed")
    booked_date: Optional[date] = Field(None, description="Booking date (defaults to today)")
    confirmed: bool = Field(False, description="Explicit confirmation flag for write execution")


class GetServicesInput(BaseModel):
    status: Optional[str] = Field(None, description="Filter by status: pending, in_progress, completed")
    vehicle_id: Optional[int] = Field(None, description="Filter by vehicle ID")


class GetServiceByIdInput(BaseModel):
    id: int = Field(..., description="Service record ID", examples=[1])


class UpdateServiceStatusInput(BaseModel):
    id: int = Field(..., description="Service record ID")
    status: ServiceStatus = Field(..., description="Target status (in_progress or completed)")
    confirmed: bool = Field(False, description="Explicit confirmation flag for write execution")


# Cost log models
CostCategory = Literal["service", "fuel", "parts"]


class CostLogOutput(BaseModel):
    id: int
    vehicle_id: int
    category: str
    amount: float
    description: Optional[str] = None
    log_date: date

    model_config = ConfigDict(from_attributes=True)


class CreateCostInput(BaseModel):
    vehicle_id: int = Field(..., description="Vehicle ID to attach expense")
    category: CostCategory = Field(..., description="Cost category: service, fuel, or parts")
    amount: float = Field(..., ge=0, description="Amount in currency")
    description: Optional[str] = Field(None, description="Expense description")
    log_date: Optional[date] = Field(None, description="Date of expense (defaults to today)")
    confirmed: bool = Field(False, description="Explicit confirmation flag for write execution")


class GetCostsInput(BaseModel):
    vehicle_id: Optional[int] = Field(None, description="Filter by vehicle ID")
    category: Optional[str] = Field(None, description="Filter by category (service, fuel, parts)")


# Aggregated / History models
class VehicleHistoryOutput(BaseModel):
    vehicle_id: int
    service_records: list[ServiceRecordOutput]
    cost_logs: list[CostLogOutput]


class StatsSummaryOutput(BaseModel):
    total_vehicles: int
    available: int
    assigned: int
    in_service: int
    pending_services: int
    services_due_soon: int


class CostSummaryOutput(BaseModel):
    by_vehicle: dict[str, float]
    by_month: dict[str, float]
    grand_total: float


# Write confirmation output
class ConfirmationRequiredOutput(BaseModel):
    requires_confirmation: bool = True
    action: str
    summary: str
    parameters: dict[str, Any]
    precheck_passed: bool = True
