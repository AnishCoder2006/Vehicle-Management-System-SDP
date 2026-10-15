from datetime import date, datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


# --- VEHICLE SCHEMAS ---

VehicleType = Literal["car", "van", "truck", "bike"]
VehicleStatus = Literal["available", "assigned", "in_service"]


class VehicleBase(BaseModel):
    plate_number: str = Field(..., min_length=3, max_length=20, description="Unique license plate number", examples=["ABC-1234"])
    make: Optional[str] = Field(None, examples=["Toyota"])
    model: Optional[str] = Field(None, examples=["Corolla"])
    year: Optional[int] = Field(None, ge=1990, le=2030, description="Manufacture year between 1990 and 2030", examples=[2022])
    vehicle_type: VehicleType = Field("car", description="Vehicle type: car, van, truck, bike", examples=["car"])
    mileage: int = Field(0, ge=0, description="Odometer mileage (>= 0)", examples=[15000])
    status: VehicleStatus = Field("available", description="Status: available, assigned, in_service", examples=["available"])
    next_service_date: Optional[date] = Field(None, description="Next scheduled service date (YYYY-MM-DD)", examples=["2026-11-01"])

    @field_validator("plate_number")
    @classmethod
    def validate_plate(cls, v: str) -> str:
        cleaned = v.strip().upper()
        if not (3 <= len(cleaned) <= 20):
            raise ValueError("plate_number must be between 3 and 20 characters")
        return cleaned


class VehicleCreate(VehicleBase):
    pass


class VehicleUpdate(BaseModel):
    plate_number: Optional[str] = Field(None, min_length=3, max_length=20, examples=["ABC-1234"])
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = Field(None, ge=1990, le=2030)
    vehicle_type: Optional[VehicleType] = None
    mileage: Optional[int] = Field(None, ge=0)
    status: Optional[VehicleStatus] = None
    next_service_date: Optional[date] = None

    @field_validator("plate_number")
    @classmethod
    def validate_plate(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        cleaned = v.strip().upper()
        if not (3 <= len(cleaned) <= 20):
            raise ValueError("plate_number must be between 3 and 20 characters")
        return cleaned


class VehicleResponse(VehicleBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# --- DRIVER SCHEMAS ---

class DriverBase(BaseModel):
    name: str = Field(..., min_length=1, description="Driver full name", examples=["John Doe"])
    phone: str = Field(..., min_length=1, description="Driver phone number", examples=["555-0199"])
    license_number: str = Field(..., min_length=1, description="Unique driver license number", examples=["DL-98765"])

    @field_validator("name", "phone", "license_number")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()


class DriverCreate(DriverBase):
    pass


class DriverUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    phone: Optional[str] = Field(None, min_length=1)
    license_number: Optional[str] = Field(None, min_length=1)

    @field_validator("name", "phone", "license_number")
    @classmethod
    def validate_optional_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip() if v is not None else None


class DriverResponse(DriverBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# --- ASSIGNMENT SCHEMAS ---

class AssignmentCreate(BaseModel):
    vehicle_id: int = Field(..., description="ID of the vehicle to assign", examples=[1])
    driver_id: int = Field(..., description="ID of the driver to assign", examples=[1])


class AssignmentResponse(BaseModel):
    id: int
    vehicle_id: int
    driver_id: int
    assigned_at: datetime
    released_at: Optional[datetime] = None
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


# --- SERVICE RECORD SCHEMAS ---

ServiceStatus = Literal["pending", "in_progress", "completed"]


class ServiceRecordCreate(BaseModel):
    vehicle_id: int = Field(..., description="ID of vehicle for service", examples=[1])
    customer_name: str = Field(..., min_length=1, description="Customer name", examples=["Alice Smith"])
    service_type: str = Field(..., min_length=1, description="Type of service (e.g., Oil change)", examples=["Oil change"])
    description: Optional[str] = Field(None, description="Optional service notes", examples=["Full synthetic oil replacement"])
    booked_date: Optional[date] = Field(None, description="Booking date (defaults to today)", examples=["2026-10-15"])

    @field_validator("customer_name", "service_type")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()


class ServiceStatusUpdate(BaseModel):
    status: ServiceStatus = Field(..., description="Target status: in_progress or completed", examples=["in_progress"])


class ServiceRecordResponse(BaseModel):
    id: int
    vehicle_id: int
    customer_name: str
    service_type: str
    description: Optional[str] = None
    status: str
    booked_date: date
    completed_date: Optional[date] = None
    model_config = ConfigDict(from_attributes=True)


# --- COST LOG SCHEMAS ---

CostCategory = Literal["service", "fuel", "parts"]


class CostLogCreate(BaseModel):
    vehicle_id: int = Field(..., description="ID of the vehicle", examples=[1])
    category: CostCategory = Field(..., description="Cost category: service, fuel, or parts", examples=["fuel"])
    amount: float = Field(..., ge=0, description="Cost amount (>= 0)", examples=[45.50])
    description: Optional[str] = Field(None, description="Optional description of the cost", examples=["50L Diesel"])
    log_date: Optional[date] = Field(None, description="Date of the cost (defaults to today)", examples=["2026-10-15"])


class CostLogResponse(BaseModel):
    id: int
    vehicle_id: int
    category: str
    amount: float
    description: Optional[str] = None
    log_date: date
    model_config = ConfigDict(from_attributes=True)


# --- HISTORY & STATS SCHEMAS ---

class VehicleHistoryResponse(BaseModel):
    vehicle_id: int
    service_records: list[ServiceRecordResponse]
    cost_logs: list[CostLogResponse]


class StatsSummaryResponse(BaseModel):
    total_vehicles: int
    available: int
    assigned: int
    in_service: int
    pending_services: int
    services_due_soon: int


class CostSummaryResponse(BaseModel):
    by_vehicle: dict[str, float]
    by_month: dict[str, float]
    grand_total: float
