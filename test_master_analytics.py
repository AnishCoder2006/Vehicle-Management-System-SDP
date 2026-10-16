
import json
import pandas as pd
from pathlib import Path

from agents.master_agent import run_master_agent
from agents.schemas import AgentRequest

ROOT = Path(__file__).resolve().parent

DATA_PATH = ROOT / "ml" / "data" / "raw" / "train_operational_readouts.csv"
METADATA_PATH = ROOT / "ml" / "artifacts" / "model_metadata.json"


def main():
    # Load the exact feature names expected by the model
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    feature_names = metadata["features"]

    # Select the latest operational reading for a vehicle
    df = pd.read_csv(DATA_PATH)
    df = df.sort_values(["vehicle_id", "time_step"])
    row = df.drop_duplicates("vehicle_id", keep="last").iloc[0]

    vehicle_id = int(row["vehicle_id"])

    features = {
        name: None if pd.isna(row[name]) else float(row[name])
        for name in feature_names
    }

    request = AgentRequest(
        session_id="master-analytics-test",
        message=f"Predict maintenance risk for vehicle {vehicle_id}",
        context={
            "vehicle_id": vehicle_id,
            "features": features,
        },
    )

    print(f"Testing vehicle ID: {vehicle_id}")
    print(f"Features supplied: {len(features)}")

    response = run_master_agent(request)

    print("\nMaster Agent response:")
    print(response.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
