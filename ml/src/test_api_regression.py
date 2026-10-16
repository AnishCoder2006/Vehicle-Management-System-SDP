
import json
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = "http://127.0.0.1:8001"
ROOT = Path(__file__).resolve().parents[2]
METADATA_PATH = ROOT / "ml" / "artifacts" / "model_metadata.json"


def post_json(path, payload):
    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def main():
    with open(METADATA_PATH, encoding="utf-8") as file:
        metadata = json.load(file)

    feature_names = metadata["features"]

    # All expected features supplied; null values are supported.
    valid_payload = {
        "vehicle_id": 0,
        "features": {name: 0.0 for name in feature_names},
    }
    valid_payload["features"][feature_names[0]] = None

    status, result = post_json("/predict", valid_payload)
    assert status == 200, (status, result)
    assert result["vehicle_id"] == 0
    assert result["maintenance_risk"] in {"LOW", "MEDIUM", "HIGH"}
    assert 0 <= result["risk_score"] <= 1
    print("PASS: valid feature payload")

    # Remove a required feature.
    missing_payload = {
        "vehicle_id": 0,
        "features": dict(valid_payload["features"]),
    }
    missing_payload["features"].pop(feature_names[0])

    status, _ = post_json("/predict", missing_payload)
    assert status == 422, f"Expected 422, got {status}"
    print("PASS: missing feature rejected")

    # Supply an unexpected feature.
    extra_payload = {
        "vehicle_id": 0,
        "features": {
            **valid_payload["features"],
            "unexpected_feature": 1.0,
        },
    }

    status, _ = post_json("/predict", extra_payload)
    assert status == 422, f"Expected 422, got {status}"
    print("PASS: extra feature rejected")

    # Supply a non-numeric value.
    invalid_payload = {
        "vehicle_id": 0,
        "features": dict(valid_payload["features"]),
    }
    invalid_payload["features"][feature_names[0]] = "not-a-number"

    status, _ = post_json("/predict", invalid_payload)
    assert status == 422, f"Expected 422, got {status}"
    print("PASS: non-numeric feature rejected")

    print("\nAll API regression checks passed.")


if __name__ == "__main__":
    main()
