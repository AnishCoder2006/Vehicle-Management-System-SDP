from datetime import date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Assignment, CostLog, ServiceRecord, Vehicle
from app.schemas import (
    CostLogResponse,
    ServiceRecordResponse,
    VehicleCreate,
    VehicleHistoryResponse,
    VehicleResponse,
    VehicleUpdate,
)

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.post("", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED, summary="Add vehicle")
def create_vehicle(vehicle_in: VehicleCreate, db: Session = Depends(get_db)):
    existing = db.query(Vehicle).filter(Vehicle.plate_number == vehicle_in.plate_number).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Vehicle with plate number '{vehicle_in.plate_number}' already exists",
        )

    vehicle = Vehicle(**vehicle_in.model_dump())
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle


@router.get("", response_model=list[VehicleResponse], summary="List vehicles with optional filters")
def list_vehicles(
    status: Optional[str] = None,
    vehicle_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Vehicle)
    if status:
        query = query.filter(Vehicle.status == status)
    if vehicle_type:
        query = query.filter(Vehicle.vehicle_type == vehicle_type)
    return query.all()


@router.get("/available", response_model=list[VehicleResponse], summary="List available vehicles")
def list_available_vehicles(db: Session = Depends(get_db)):
    return db.query(Vehicle).filter(Vehicle.status == "available").all()


@router.get("/due-service", response_model=list[VehicleResponse], summary="List vehicles due for service soon or overdue")
def list_due_service_vehicles(db: Session = Depends(get_db)):
    cutoff_date = date.today() + timedelta(days=7)
    return (
        db.query(Vehicle)
        .filter(Vehicle.next_service_date.isnot(None), Vehicle.next_service_date <= cutoff_date)
        .all()
    )


@router.get("/{id}", response_model=VehicleResponse, summary="Get one vehicle by ID")
def get_vehicle(id: int, db: Session = Depends(get_db)):
    vehicle = db.query(Vehicle).filter(Vehicle.id == id).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle with id {id} not found",
        )
    return vehicle


@router.put("/{id}", response_model=VehicleResponse, summary="Update vehicle details")
def update_vehicle(id: int, vehicle_in: VehicleUpdate, db: Session = Depends(get_db)):
    vehicle = db.query(Vehicle).filter(Vehicle.id == id).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle with id {id} not found",
        )

    update_data = vehicle_in.model_dump(exclude_unset=True)
    if "plate_number" in update_data and update_data["plate_number"] != vehicle.plate_number:
        existing = db.query(Vehicle).filter(Vehicle.plate_number == update_data["plate_number"]).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Vehicle with plate number '{update_data['plate_number']}' already exists",
            )

    for field, value in update_data.items():
        setattr(vehicle, field, value)

    db.commit()
    db.refresh(vehicle)
    return vehicle


@router.delete("/{id}", summary="Delete a vehicle")
def delete_vehicle(id: int, db: Session = Depends(get_db)):
    vehicle = db.query(Vehicle).filter(Vehicle.id == id).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle with id {id} not found",
        )

    # Cannot delete if it has an active assignment
    active_assignment = (
        db.query(Assignment)
        .filter(Assignment.vehicle_id == id, Assignment.is_active == True)
        .first()
    )
    if active_assignment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete vehicle with active assignment",
        )

    db.delete(vehicle)
    db.commit()
    return {"message": f"Vehicle with id {id} deleted successfully"}


@router.get("/{id}/history", response_model=VehicleHistoryResponse, summary="Get service records and costs for a vehicle")
def get_vehicle_history(id: int, db: Session = Depends(get_db)):
    vehicle = db.query(Vehicle).filter(Vehicle.id == id).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle with id {id} not found",
        )

    services = db.query(ServiceRecord).filter(ServiceRecord.vehicle_id == id).all()
    costs = db.query(CostLog).filter(CostLog.vehicle_id == id).all()

    return VehicleHistoryResponse(
        vehicle_id=id,
        service_records=[ServiceRecordResponse.model_validate(s) for s in services],
        cost_logs=[CostLogResponse.model_validate(c) for c in costs],
    )
