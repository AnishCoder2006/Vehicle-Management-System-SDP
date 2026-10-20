from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from fleetflow_data import get_fleet_data
from preprocessing import FEATURE_COLUMNS, build_feature_dataframe


BASE_DIR = Path(__file__).resolve().parents[1]

MODEL_DIR = BASE_DIR / "models"
ARTIFACT_DIR = BASE_DIR / "artifacts"

MODEL_PATH = MODEL_DIR / "maintenance_model.joblib"
METADATA_PATH = ARTIFACT_DIR / "model_metadata.json"


def create_development_target(
    vehicles: list[dict],
    services: list[dict],
) -> pd.Series:
    """
    Development-only target.

    A vehicle is labelled 1 when it currently has an active
    maintenance requirement:

        pending service
        OR
        in-progress service

    This target is useful for pipeline development, but it is NOT
    a real future-failure label.

    A future version should use historical time-based records to
    define something like:
        "maintenance required within next 30 days"
    """

    service_by_vehicle = {}

    for vehicle in vehicles:
        service_by_vehicle[vehicle["id"]] = False

    for service in services:
        if service["status"] in {"pending", "in_progress"}:
            service_by_vehicle[service["vehicle_id"]] = True

    return pd.Series(
        [
            int(service_by_vehicle.get(vehicle["id"], False))
            for vehicle in vehicles
        ]
    )


def train_model():
    print("Loading FleetFlow data from backend...")

    data = get_fleet_data()

    vehicles = data["vehicles"]
    services = data["services"]
    costs = data["costs"]

    print(f"Vehicles: {len(vehicles)}")
    print(f"Services: {len(services)}")
    print(f"Costs: {len(costs)}")

    if len(vehicles) < 10:
        raise RuntimeError(
            "Not enough vehicles to build the development dataset."
        )

    # -----------------------------
    # Feature engineering
    # -----------------------------

    X = build_feature_dataframe(
        vehicles=vehicles,
        services=services,
        costs=costs,
    )

    y = create_development_target(
        vehicles=vehicles,
        services=services,
    )

    X = X.drop(columns=["vehicle_id"])

    print("\nFeatures:")
    print(list(X.columns))

    print("\nTarget distribution:")
    print(y.value_counts().to_dict())

    # Need both classes for Logistic Regression.
    if y.nunique() < 2:
        raise RuntimeError(
            "The current FleetFlow seed data contains only one target class. "
            "Add more historical/service examples before training."
        )

    # -----------------------------
    # Preprocessing
    # -----------------------------

    numeric_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(strategy="median"),
            ),
            (
                "scaler",
                StandardScaler(),
            ),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "numeric",
                numeric_pipeline,
                FEATURE_COLUMNS,
            )
        ],
        remainder="drop",
    )

    # -----------------------------
    # Model
    # -----------------------------

    model = Pipeline(
        steps=[
            (
                "preprocessor",
                preprocessor,
            ),
            (
                "classifier",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=1000,
                    random_state=42,
                ),
            ),
        ]
    )

    model.fit(X, y)

    # -----------------------------
    # Save model
    # -----------------------------

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    joblib.dump(model, MODEL_PATH)

    metadata = {
        "model_name": "fleetflow_maintenance_risk_model",
        "model_version": "2.0.0",
        "algorithm": "LogisticRegression",
        "feature_count": len(FEATURE_COLUMNS),
        "features": FEATURE_COLUMNS,
        "training_rows": len(X),
        "target": "active_maintenance_requirement",
        "target_definition": (
            "1 if the vehicle currently has a pending or "
            "in-progress service, otherwise 0"
        ),
        "training_type": "development_prototype",
        "warning": (
            "This model is trained on the current FleetFlow seed data. "
            "It is not a validated future-maintenance prediction model."
        ),
        "training_date": date.today().isoformat(),
    }

    with open(METADATA_PATH, "w", encoding="utf-8") as file:
        json.dump(metadata, file, indent=4)

    print("\nModel trained successfully.")
    print(f"Model: {MODEL_PATH}")
    print(f"Metadata: {METADATA_PATH}")


if __name__ == "__main__":
    train_model()