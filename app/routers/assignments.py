from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Assignment, Driver, Vehicle
from app.schemas import AssignmentCreate, AssignmentResponse

router = APIRouter(prefix="/assignments", tags=["assignments"])


@router.post("", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED, summary="Assign vehicle to driver")
def create_assignment(assignment_in: AssignmentCreate, db: Session = Depends(get_db)):
    vehicle = db.query(Vehicle).filter(Vehicle.id == assignment_in.vehicle_id).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle with id {assignment_in.vehicle_id} not found",
        )

    driver = db.query(Driver).filter(Driver.id == assignment_in.driver_id).first()
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Driver with id {assignment_in.driver_id} not found",
        )

    if vehicle.status != "available":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Vehicle with id {vehicle.id} is not available (current status: {vehicle.status})",
        )

    assignment = Assignment(
        vehicle_id=assignment_in.vehicle_id,
        driver_id=assignment_in.driver_id,
        assigned_at=datetime.now(),
        is_active=True,
    )
    vehicle.status = "assigned"

    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.post("/{id}/release", response_model=AssignmentResponse, summary="Release active assignment")
def release_assignment(id: int, db: Session = Depends(get_db)):
    assignment = db.query(Assignment).filter(Assignment.id == id).first()
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assignment with id {id} not found",
        )

    if not assignment.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Assignment with id {id} is already released",
        )

    assignment.is_active = False
    assignment.released_at = datetime.now()

    vehicle = db.query(Vehicle).filter(Vehicle.id == assignment.vehicle_id).first()
    if vehicle:
        vehicle.status = "available"

    db.commit()
    db.refresh(assignment)
    return assignment


@router.get("", response_model=list[AssignmentResponse], summary="List assignments with optional filters")
def list_assignments(
    vehicle_id: Optional[int] = None,
    driver_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Assignment)
    if vehicle_id is not None:
        query = query.filter(Assignment.vehicle_id == vehicle_id)
    if driver_id is not None:
        query = query.filter(Assignment.driver_id == driver_id)
    if is_active is not None:
        query = query.filter(Assignment.is_active == is_active)
    return query.all()
