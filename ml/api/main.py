from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.fleetflow_data import get_fleet_data
from src.preprocessing import FEATURE_COLUMNS, build_vehicle_features


BASE_DIR = Path(__file__).resolve().parents[1]

MODEL_PATH = BASE_DIR / "models" / "maintenance_model.joblib"
METADATA_PATH = BASE_DIR / "artifacts" / "model_metadata.json"


app = FastAPI(
    title="FleetFlow Maintenance ML API",
    description="FleetFlow-specific predictive maintenance service",
    version="2.0.0",
)


# --------------------------------------------------
# Load model
# --------------------------------------------------

if not MODEL_PATH.exists():
    raise RuntimeError(
        f"Model file not found: {MODEL_PATH}"
    )

model = joblib.load(MODEL_PATH)


if METADATA_PATH.exists():
    with open(METADATA_PATH, "r", encoding="utf-8") as file:
        metadata = json.load(file)
else:
    metadata = {
        "model_name": "fleetflow_maintenance_risk_model",
        "model_version": "2.0.0",
        "features": FEATURE_COLUMNS,
    }


# --------------------------------------------------
# Request models
# --------------------------------------------------

class PredictionRequest(BaseModel):
    vehicle_id: int


# --------------------------------------------------
# Health
# --------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "model": metadata["model_name"],
        "model_version": metadata["model_version"],
    }


# --------------------------------------------------
# Model info
# --------------------------------------------------

@app.get("/model-info")
def model_info():
    return metadata


# --------------------------------------------------
# Prediction
# --------------------------------------------------

@app.post("/predict")
def predict(request: PredictionRequest):

    try:
        fleet_data = get_fleet_data()

        vehicles = fleet_data["vehicles"]
        services = fleet_data["services"]
        costs = fleet_data["costs"]

        vehicle = next(
            (
                vehicle
                for vehicle in vehicles
                if vehicle["id"] == request.vehicle_id
            ),
            None,
        )

        if vehicle is None:
            raise HTTPException(
                status_code=404,
                detail=f"Vehicle {request.vehicle_id} not found.",
            )

        features = build_vehicle_features(
            vehicle=vehicle,
            services=services,
            costs=costs,
        )

        feature_df = pd.DataFrame(
            [features],
            columns=FEATURE_COLUMNS,
        )

        probability = float(
            model.predict_proba(feature_df)[0][1]
        )

        if probability >= 0.70:
            risk = "HIGH"
        elif probability >= 0.40:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        return {
            "vehicle_id": request.vehicle_id,
            "maintenance_risk": risk,
            "risk_score": round(probability, 4),
            "risk_percentage": round(probability * 100, 2),
            "model_version": metadata["model_version"],
            "features": features,
            "prediction_type": "development_prototype",
        }

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {str(exc)}",
        ) from exc