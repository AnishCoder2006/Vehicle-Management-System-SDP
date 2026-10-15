from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ServiceRecord, Vehicle
from app.schemas import ServiceRecordCreate, ServiceRecordResponse, ServiceStatusUpdate

router = APIRouter(prefix="/services", tags=["services"])


@router.post("", response_model=ServiceRecordResponse, status_code=status.HTTP_201_CREATED, summary="Create service booking")
def create_service(service_in: ServiceRecordCreate, db: Session = Depends(get_db)):
    vehicle = db.query(Vehicle).filter(Vehicle.id == service_in.vehicle_id).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle with id {service_in.vehicle_id} not found",
        )

    booked_date = service_in.booked_date or date.today()

    record = ServiceRecord(
        vehicle_id=service_in.vehicle_id,
        customer_name=service_in.customer_name,
        service_type=service_in.service_type,
        description=service_in.description,
        status="pending",
        booked_date=booked_date,
        completed_date=None,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("", response_model=list[ServiceRecordResponse], summary="List service records with optional filters")
def list_services(
    status: Optional[str] = None,
    vehicle_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    query = db.query(ServiceRecord)
    if status:
        query = query.filter(ServiceRecord.status == status)
    if vehicle_id is not None:
        query = query.filter(ServiceRecord.vehicle_id == vehicle_id)
    return query.all()


@router.get("/{id}", response_model=ServiceRecordResponse, summary="Get one service record by ID")
def get_service(id: int, db: Session = Depends(get_db)):
    record = db.query(ServiceRecord).filter(ServiceRecord.id == id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service record with id {id} not found",
        )
    return record


@router.patch("/{id}/status", response_model=ServiceRecordResponse, summary="Update service status")
def update_service_status(id: int, status_update: ServiceStatusUpdate, db: Session = Depends(get_db)):
    record = db.query(ServiceRecord).filter(ServiceRecord.id == id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service record with id {id} not found",
        )

    target_status = status_update.status
    current_status = record.status

    # Validate transition: pending -> in_progress -> completed
    if current_status == "pending":
        if target_status != "in_progress":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status transition from 'pending' to '{target_status}'. Must transition to 'in_progress'.",
            )
    elif current_status == "in_progress":
        if target_status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status transition from 'in_progress' to '{target_status}'. Must transition to 'completed'.",
            )
    elif current_status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Service record is already completed and cannot be transitioned further.",
        )

    # Apply side effects
    vehicle = db.query(Vehicle).filter(Vehicle.id == record.vehicle_id).first()
    if target_status == "in_progress":
        record.status = "in_progress"
        if vehicle:
            vehicle.status = "in_service"
    elif target_status == "completed":
        record.status = "completed"
        record.completed_date = date.today()
        if vehicle:
            vehicle.status = "available"

    db.commit()
    db.refresh(record)
    return record
