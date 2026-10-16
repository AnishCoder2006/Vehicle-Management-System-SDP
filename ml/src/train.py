from pathlib import Path
import json
from datetime import datetime

import joblib

from data_loader import load_operational_data, load_target_data
from preprocessing import prepare_training_data

from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score
)


BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "models"
ARTIFACT_DIR = BASE_DIR / "artifacts"

MODEL_DIR.mkdir(exist_ok=True)
ARTIFACT_DIR.mkdir(exist_ok=True)


def main():

    print("Loading data...")

    operational = load_operational_data()
    target = load_target_data()

    print("Preparing data...")

    X, y = prepare_training_data(
        operational,
        target
    )

    print(f"Training samples: {len(X)}")
    print(f"Features: {X.shape[1]}")

    print("\nTarget distribution:")
    print(y.value_counts())

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y
    )

    pipeline = Pipeline([
        (
            "imputer",
            SimpleImputer(strategy="median")
        ),
        (
            "scaler",
            StandardScaler()
        ),
        (
            "model",
            LogisticRegression(
                max_iter=1000,
                class_weight="balanced"
            )
        )
    ])

    print("\nTraining model...")

    pipeline.fit(X_train, y_train)

    predictions = pipeline.predict(X_test)
    probabilities = pipeline.predict_proba(X_test)[:, 1]

    print("\nClassification Report:")
    print(
        classification_report(
            y_test,
            predictions,
            zero_division=0
        )
    )

    print("\nConfusion Matrix:")
    print(confusion_matrix(y_test, predictions))

    auc = roc_auc_score(
        y_test,
        probabilities
    )

    print(f"\nROC-AUC: {auc:.4f}")

    model_path = MODEL_DIR / "maintenance_model.joblib"

    joblib.dump(
        pipeline,
        model_path
    )

    metadata = {
        "model_name": "maintenance_risk_model",
        "model_version": "1.0.0",
        "algorithm": "LogisticRegression",
        "training_date": datetime.utcnow().isoformat(),
        "features": list(X.columns),
        "feature_count": len(X.columns),
        "roc_auc": float(auc)
    }

    with open(
        ARTIFACT_DIR / "model_metadata.json",
        "w"
    ) as file:
        json.dump(
            metadata,
            file,
            indent=4
        )

    print("\nModel saved:")
    print(model_path)


if __name__ == "__main__":
    main()