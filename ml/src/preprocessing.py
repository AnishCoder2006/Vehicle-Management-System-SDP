import pandas as pd


def prepare_training_data(operational_df, target_df):

    # Get the latest observation for each vehicle
    operational_df = operational_df.sort_values(
        ["vehicle_id", "time_step"]
    )

    latest = (
        operational_df
        .groupby("vehicle_id")
        .tail(1)
        .copy()
    )

    # Merge the repair target
    data = latest.merge(
        target_df[["vehicle_id", "in_study_repair"]],
        on="vehicle_id",
        how="inner"
    )

    # Remove identifiers from ML features
    X = data.drop(
        columns=[
            "vehicle_id",
            "in_study_repair"
        ],
        errors="ignore"
    )

    y = data["in_study_repair"]

    # Keep numeric features only for V1
    X = X.select_dtypes(include=["number"])

    # Replace infinite values
    X = X.replace([float("inf"), float("-inf")], float("nan"))

    # Simple missing-value handling
    X = X.fillna(X.median(numeric_only=True))

    return X, y