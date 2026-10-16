# Predictive Maintenance — Analytics Agent

## 1. Overview

This module integrates a machine learning model with the Analytics Agent to estimate vehicle maintenance risk from operational sensor data.

The Master Agent routes maintenance-related requests to the Analytics Agent, which calls a separate ML prediction API and returns the prediction.

The Analytics Agent is read-only and does not modify fleet records.

## 2. Architecture

1. The user requests a maintenance risk prediction.
2. The Master Agent identifies the request as an analytics task.
3. The Analytics Agent extracts the vehicle ID and sensor features from the request context.
4. The Analytics Agent calls the ML prediction API.
5. The ML API validates the input and generates a risk estimate.
6. The result is returned to the user through the agent workflow.

## 3. Machine Learning Model

- Algorithm: Logistic Regression
- Model version: 1.0.0
- Input: 106 operational features
- Target: `in_study_repair`
- Output: Estimated repair-related risk score and risk category
- Model artifact: `ml/models/maintenance_model.joblib`
- Feature metadata: `ml/artifacts/model_metadata.json`

The model uses the SCANIA Component X dataset. The target dataset's `length_of_study_time_step` field is excluded from model inputs to avoid target leakage.

## 4. ML API

The local prediction API runs on port 8001.

- `GET /health` — checks API health
- `GET /model-info` — returns model information
- `POST /predict` — generates a maintenance risk prediction
- `/docs` — interactive API documentation

Start the API from the `ml` directory:

```powershell
uvicorn api.main:app --reload --port 8001
```

## 5. Input Requirements

The prediction API expects exactly 106 named operational features, matching `ml/artifacts/model_metadata.json`.

Features must be numeric or null where supported by the API. Missing features, unexpected features, and non-numeric values are rejected.

Ordinary fleet metadata such as vehicle make, model, or status cannot replace sensor features.

## 6. Testing

The following checks have passed:

- ML prediction API smoke test
- Valid and invalid API payload regression tests
- Analytics Agent integration test
- Master Agent end-to-end integration test
- Existing agent and routing tests: 14 passed

Run the API regression test with the ML API already running:

```powershell
.\ml\.venv\Scripts\python.exe ml\src\test_api_regression.py
```

Run the existing routing and agent tests using the Python environment in which the project dependencies are installed:

```powershell
python -m pytest tests/test_analytics_routing.py tests/test_router.py tests/test_agents.py -v
```

## 7. Limitations

- Predictions are estimates, not guarantees of vehicle condition.
- The model expects compatible operational sensor data.
- The current integration tests use SCANIA dataset features; real fleet integration requires a legitimate source of compatible sensor readings.
- Risk thresholds may require