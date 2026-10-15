from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Assignment, Driver
from app.schemas import DriverCreate, DriverResponse, DriverUpdate

router = APIRouter(prefix="/drivers", tags=["drivers"])


@router.post("", response_model=DriverResponse, status_code=status.HTTP_201_CREATED, summary="Add driver")
def create_driver(driver_in: DriverCreate, db: Session = Depends(get_db)):
    existing = db.query(Driver).filter(Driver.license_number == driver_in.license_number).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Driver with license number '{driver_in.license_number}' already exists",
        )

    driver = Driver(**driver_in.model_dump())
    db.add(driver)
    db.commit()
    db.refresh(driver)
    return driver


@router.get("", response_model=list[DriverResponse], summary="List all drivers")
def list_drivers(db: Session = Depends(get_db)):
    return db.query(Driver).all()


@router.get("/{id}", response_model=DriverResponse, summary="Get one driver by ID")
def get_driver(id: int, db: Session = Depends(get_db)):
    driver = db.query(Driver).filter(Driver.id == id).first()
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Driver with id {id} not found",
        )
    return driver


@router.put("/{id}", response_model=DriverResponse, summary="Update driver details")
def update_driver(id: int, driver_in: DriverUpdate, db: Session = Depends(get_db)):
    driver = db.query(Driver).filter(Driver.id == id).first()
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Driver with id {id} not found",
        )

    update_data = driver_in.model_dump(exclude_unset=True)
    if "license_number" in update_data and update_data["license_number"] != driver.license_number:
        existing = db.query(Driver).filter(Driver.license_number == update_data["license_number"]).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Driver with license number '{update_data['license_number']}' already exists",
            )

    for field, value in update_data.items():
        setattr(driver, field, value)

    db.commit()
    db.refresh(driver)
    return driver


@router.delete("/{id}", summary="Delete a driver")
def delete_driver(id: int, db: Session = Depends(get_db)):
    driver = db.query(Driver).filter(Driver.id == id).first()
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Driver with id {id} not found",
        )

    # Check if driver has an active assignment
    active_assignment = (
        db.query(Assignment)
        .filter(Assignment.driver_id == id, Assignment.is_active == True)
        .first()
    )
    if active_assignment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete driver with active assignment",
        )

    db.delete(driver)
    db.commit()
    return {"message": f"Driver with id {id} deleted successfully"}
