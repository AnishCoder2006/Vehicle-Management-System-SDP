from collections import defaultdict
from datetime import date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CostLog, ServiceRecord, Vehicle
from app.schemas import (
    CostLogCreate,
    CostLogResponse,
    CostSummaryResponse,
    StatsSummaryResponse,
)

router = APIRouter()


@router.post(
    "/costs",
    response_model=CostLogResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add cost entry",
    tags=["costs"],
)
def create_cost_log(cost_in: CostLogCreate, db: Session = Depends(get_db)):
    vehicle = db.query(Vehicle).filter(Vehicle.id == cost_in.vehicle_id).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle with id {cost_in.vehicle_id} not found",
        )

    log_date = cost_in.log_date or date.today()

    cost_log = CostLog(
        vehicle_id=cost_in.vehicle_id,
        category=cost_in.category,
        amount=cost_in.amount,
        description=cost_in.description,
        log_date=log_date,
    )
    db.add(cost_log)
    db.commit()
    db.refresh(cost_log)
    return cost_log


@router.get(
    "/costs/summary",
    response_model=CostSummaryResponse,
    summary="Get cost summary grouped by vehicle, month, and grand total",
    tags=["costs"],
)
def get_costs_summary(db: Session = Depends(get_db)):
    cost_logs = db.query(CostLog).all()

    by_vehicle: dict[str, float] = defaultdict(float)
    by_month: dict[str, float] = defaultdict(float)
    grand_total = 0.0

    for log in cost_logs:
        v_key = str(log.vehicle_id)
        m_key = log.log_date.strftime("%Y-%m")
        amt = float(log.amount)

        by_vehicle[v_key] += amt
        by_month[m_key] += amt
        grand_total += amt

    # Round all values to 2 decimal places
    rounded_by_vehicle = {k: round(v, 2) for k, v in sorted(by_vehicle.items())}
    rounded_by_month = {k: round(v, 2) for k, v in sorted(by_month.items())}
    rounded_grand_total = round(grand_total, 2)

    return CostSummaryResponse(
        by_vehicle=rounded_by_vehicle,
        by_month=rounded_by_month,
        grand_total=rounded_grand_total,
    )


@router.get(
    "/costs",
    response_model=list[CostLogResponse],
    summary="List cost logs with optional vehicle_id and category filters",
    tags=["costs"],
)
def list_cost_logs(
    vehicle_id: Optional[int] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(CostLog)
    if vehicle_id is not None:
        query = query.filter(CostLog.vehicle_id == vehicle_id)
    if category is not None:
        query = query.filter(CostLog.category == category)
    return query.all()


@router.get(
    "/stats/summary",
    response_model=StatsSummaryResponse,
    summary="Get overall vehicle and service statistics",
    tags=["stats"],
)
def get_stats_summary(db: Session = Depends(get_db)):
    total_vehicles = db.query(Vehicle).count()
    available = db.query(Vehicle).filter(Vehicle.status == "available").count()
    assigned = db.query(Vehicle).filter(Vehicle.status == "assigned").count()
    in_service = db.query(Vehicle).filter(Vehicle.status == "in_service").count()
    pending_services = db.query(ServiceRecord).filter(ServiceRecord.status == "pending").count()

    cutoff_date = date.today() + timedelta(days=7)
    services_due_soon = (
        db.query(Vehicle)
        .filter(Vehicle.next_service_date.isnot(None), Vehicle.next_service_date <= cutoff_date)
        .count()
    )

    return StatsSummaryResponse(
        total_vehicles=total_vehicles,
        available=available,
        assigned=assigned,
        in_service=in_service,
        pending_services=pending_services,
        services_due_soon=services_due_soon,
    )
