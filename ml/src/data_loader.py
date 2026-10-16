from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"


def load_operational_data():
    path = RAW_DIR / "train_operational_readouts.csv"

    if not path.exists():
        raise FileNotFoundError(
            f"Operational dataset not found: {path}"
        )

    return pd.read_csv(path)


def load_target_data():
    path = RAW_DIR / "train_tte.csv"

    if not path.exists():
        raise FileNotFoundError(
            f"Target dataset not found: {path}"
        )

    return pd.read_csv(path)


if __name__ == "__main__":
    operational = load_operational_data()
    target = load_target_data()

    print("\nOperational data:")
    print(operational.shape)
    print(operational.head())

    print("\nTarget data:")
    print(target.shape)
    print(target.head())

    print("\nOperational columns:")
    print(operational.columns.tolist())

    print("\nTarget columns:")
    print(target.columns.tolist())