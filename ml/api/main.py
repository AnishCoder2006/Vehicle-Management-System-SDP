
from pathlib import Path
import json
import math

import joblib
import pandas as pd

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent

MODEL_PATH = BASE_DIR / "models" / "maintenance_model.joblib"
METADATA_PATH = BASE_DIR / "artifacts" / "model_metadata.json"

app = FastAPI(
    title="Fleet Predictive Intelligence API",
    version="1.0.0",
)

model = None
metadata = None


def load_model():
    global model, metadata

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            "Trained model not found. Run train.py first."
        )

    if not METADATA_PATH.exists():
        raise FileNotFoundError(
            "Model metadata not found."
        )

    model = joblib.load(MODEL_PATH)

    with open(METADATA_PATH, "r", encoding="utf-8") as file:
        metadata = json.load(file)

    expected_features = metadata.get("features")

    if not isinstance(expected_features, list) or not expected_features:
        raise ValueError(
            "Model metadata must contain a non-empty features list."
        )

    if len(expected_features) != len(set(expected_features)):
        raise ValueError(
            "Model metadata contains duplicate feature names."
        )


class PredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vehicle_id: int
    features: dict[str, object]


@app.get("/health")
def health():
    return {
        "status": "healthy" if model is not None else "unavailable",
        "model_loaded": model is not None,
        "metadata_loaded": metadata is not None,
    }


@app.get("/model-info")
def model_info():
    if metadata is None:
        raise HTTPException(
            status_code=503,
            detail="Model metadata is not available.",
        )

    return metadata


@app.post("/predict")
def predict(request: PredictionRequest):
    if model is None or metadata is None:
        raise HTTPException(
            status_code=503,
            detail="Model or metadata is not loaded.",
        )

    expected_features = metadata["features"]
    received_features = set(request.features.keys())
    expected_set = set(expected_features)

    missing_features = sorted(expected_set - received_features)
    extra_features = sorted(received_features - expected_set)

    if missing_features or extra_features:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Feature schema mismatch.",
                "missing_features": missing_features,
                "extra_features": extra_features,
            },
        )

    values = []

    for name in expected_features:
        value = request.features[name]

        # Null values are allowed only if the model pipeline
        # has a compatible missing-value imputer.
        if value is None:
            values.append(float("nan"))
            continue

        # Reject strings, booleans, lists and other non-numeric values.
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise HTTPException(
                status_code=422,
                detail=f"Feature '{name}' must be a number or null.",
            )

        numeric_value = float(value)

        if not math.isfinite(numeric_value):
            raise HTTPException(
                status_code=422,
                detail=f"Feature '{name}' must be finite.",
            )

        values.append(numeric_value)

    input_df = pd.DataFrame(
        [values],
        columns=expected_features,
    )

    try:
        probabilities = model.predict_proba(input_df)[0]

        # The training target is binary. Find the probability
        # corresponding to the positive class (label 1).
        classes = list(model.classes_)

        if 1 not in classes:
            raise RuntimeError(
                "The trained model does not contain positive class 1."
            )

        probability = float(probabilities[classes.index(1)])

    except Exception:
        # Keep internal implementation details in server logs,
        # rather than returning a raw exception to API clients.
        import logging
        logging.exception("Maintenance prediction failed.")

        raise HTTPException(
            status_code=500,
            detail="Prediction failed. Check the ML service logs.",
        )

    if probability >= 0.7:
        risk = "HIGH"
    elif probability >= 0.4:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    return {
        "vehicle_id": request.vehicle_id,
        "maintenance_risk": risk,
        "risk_score": round(probability, 4),
        "model_version": metadata.get("model_version", "unknown"),
    }


@app.on_event("startup")
def startup_event():
    load_model()
