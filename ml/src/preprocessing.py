from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd


FEATURE_COLUMNS = [
    "mileage",
    "vehicle_age",
    "days_until_next_service",
    "total_services",
    "pending_services",
    "in_progress_services",
    "completed_services",
    "total_cost",
    "service_cost",
    "parts_cost",
    "fuel_cost",
    "cost_last_30_days",
    "cost_last_90_days",
]


def build_vehicle_features(
    vehicle: dict[str, Any],
    services: list[dict[str, Any]],
    costs: list[dict[str, Any]],
    reference_date: date | None = None,
) -> dict[str, float]:
    """
    Build FleetFlow-specific features for one vehicle.

    These features are derived only from:
    - vehicle metadata
    - service history
    - cost history

    No SCANIA sensor features are used.
    """

    if reference_date is None:
        reference_date = date.today()

    vehicle_id = vehicle["id"]

    vehicle_services = [
        service
        for service in services
        if service["vehicle_id"] == vehicle_id
    ]

    vehicle_costs = [
        cost
        for cost in costs
        if cost["vehicle_id"] == vehicle_id
    ]

    # -----------------------------
    # Vehicle features
    # -----------------------------

    year = int(vehicle["year"])
    mileage = float(vehicle["mileage"] or 0)

    vehicle_age = max(
        0,
        reference_date.year - year,
    )

    next_service_date = vehicle.get("next_service_date")

    if next_service_date:
        if isinstance(next_service_date, str):
            next_service_date = date.fromisoformat(next_service_date)

        days_until_next_service = (
            next_service_date - reference_date
        ).days
    else:
        # No scheduled service date.
        # Use a neutral value rather than inventing a date.
        days_until_next_service = 999

    # -----------------------------
    # Service features
    # -----------------------------

    total_services = len(vehicle_services)

    pending_services = sum(
        1
        for service in vehicle_services
        if service["status"] == "pending"
    )

    in_progress_services = sum(
        1
        for service in vehicle_services
        if service["status"] == "in_progress"
    )

    completed_services = sum(
        1
        for service in vehicle_services
        if service["status"] == "completed"
    )

    # -----------------------------
    # Cost features
    # -----------------------------

    total_cost = 0.0
    service_cost = 0.0
    parts_cost = 0.0
    fuel_cost = 0.0

    cost_last_30_days = 0.0
    cost_last_90_days = 0.0

    for cost in vehicle_costs:
        amount = float(cost["amount"] or 0)

        total_cost += amount

        category = str(cost["category"]).lower()

        if category == "service":
            service_cost += amount
        elif category == "parts":
            parts_cost += amount
        elif category == "fuel":
            fuel_cost += amount

        log_date = cost["log_date"]

        if isinstance(log_date, str):
            log_date = date.fromisoformat(log_date)

        days_old = (reference_date - log_date).days

        if 0 <= days_old <= 30:
            cost_last_30_days += amount

        if 0 <= days_old <= 90:
            cost_last_90_days += amount

    return {
        "mileage": mileage,
        "vehicle_age": float(vehicle_age),
        "days_until_next_service": float(days_until_next_service),
        "total_services": float(total_services),
        "pending_services": float(pending_services),
        "in_progress_services": float(in_progress_services),
        "completed_services": float(completed_services),
        "total_cost": total_cost,
        "service_cost": service_cost,
        "parts_cost": parts_cost,
        "fuel_cost": fuel_cost,
        "cost_last_30_days": cost_last_30_days,
        "cost_last_90_days": cost_last_90_days,
    }


def build_feature_dataframe(
    vehicles: list[dict[str, Any]],
    services: list[dict[str, Any]],
    costs: list[dict[str, Any]],
    reference_date: date | None = None,
) -> pd.DataFrame:
    """
    Build a feature dataframe for all vehicles.
    """

    rows = []

    for vehicle in vehicles:
        features = build_vehicle_features(
            vehicle=vehicle,
            services=services,
            costs=costs,
            reference_date=reference_date,
        )

        features["vehicle_id"] = vehicle["id"]

        rows.append(features)

    df = pd.DataFrame(rows)

    if df.empty:
        return pd.DataFrame(columns=["vehicle_id"] + FEATURE_COLUMNS)

    return df[["vehicle_id"] + FEATURE_COLUMNS]