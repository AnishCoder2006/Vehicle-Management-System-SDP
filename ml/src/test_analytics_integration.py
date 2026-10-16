
import json
import sys
from pathlib import Path

import pandas as pd

# Find the project root so the agents package can be imported.
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agents.analytics_agent import run_analytics_agent
from agents.schemas import AgentRequest


DATA_PATH = ROOT / "ml" / "data" / "raw" / "train_operational_readouts.csv"
METADATA_PATH = ROOT / "ml" / "artifacts" / "model_metadata.json"


def main():
    # Load the feature names expected by the trained model.
    with open(METADATA_PATH, "r", encoding="utf-8") as file:
        metadata = json.load(file)

    feature_names = metadata["features"]

    # Load the dataset and select the latest reading for one vehicle.
    df = pd.read_csv(DATA_PATH)
    df = df.sort_values(["vehicle_id", "time_step"])
    row = df.drop_duplicates("vehicle_id", keep="last").iloc[0]

    vehicle_id = int(row["vehicle_id"])

    # Convert NumPy/Pandas values to JSON-compatible Python values.
    features = {}
    for name in feature_names:
        value = row[name]
        features[name] = None if pd.isna(value) else float(value)

    request = AgentRequest(
        session_id="analytics-ml-integration-test",
        message=f"Predict maintenance risk for vehicle {vehicle_id}",
        context={
            "vehicle_id": vehicle_id,
            "features": features,
        },
    )

    print(f"Testing vehicle ID: {vehicle_id}")
    print(f"Features supplied: {len(features)}")

    response = run_analytics_agent(request)
    print("\nAnalytics Agent response:")
    print(json.dumps(response.model_dump(), indent=2, default=str))


if __name__ == "__main__":
    main()
