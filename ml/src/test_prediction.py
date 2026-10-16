from pathlib import Path
import sys
import requests
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent))

from data_loader import load_operational_data


def main():
    # Load operational data
    df = load_operational_data()

    # Pick one vehicle
    vehicle_id = int(df["vehicle_id"].iloc[0])

    # Get its latest observation
    vehicle_data = (
        df[df["vehicle_id"] == vehicle_id]
        .sort_values("time_step")
        .tail(1)
    )

    # Remove vehicle_id because it is not a model feature
    features = vehicle_data.drop(
        columns=["vehicle_id"]
    ).iloc[0].to_dict()

    # Convert NaN / infinity to None so JSON can handle them
    cleaned_features = {}

    for key, value in features.items():
        if pd.isna(value) or value in [float("inf"), float("-inf")]:
            cleaned_features[key] = None
        else:
            cleaned_features[key] = float(value)

    payload = {
        "vehicle_id": vehicle_id,
        "features": cleaned_features
    }

    print(f"Testing vehicle: {vehicle_id}")
    print(f"Number of features: {len(cleaned_features)}")

    response = requests.post(
        "http://localhost:8001/predict",
        json=payload,
        timeout=10
    )

    print("\nStatus:", response.status_code)

    try:
        print("Response:")
        print(response.json())
    except Exception:
        print(response.text)

        
    import json


    print(json.dumps(payload, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()


