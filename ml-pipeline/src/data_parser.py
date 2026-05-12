import pandas as pd
import numpy as np
from pathlib import Path

ROOMS = ["BATHROOM", "BEDROOM", "KITCHEN", "LIVING_ROOM"]

SENSOR_TO_ROOM = {
    "Bathroom": "BATHROOM",
    "Bedroom": "BEDROOM",
    "Kitchen": "KITCHEN",
    "LivingRoom": "LIVING_ROOM",
    "DiningRoom": "KITCHEN",
    "GuestRoom": "BEDROOM",
    "LoungeChair": "LIVING_ROOM",
    "WorkArea": "LIVING_ROOM",
    "OtherRoom": "LIVING_ROOM",
    "OutsideDoor": None,
}

NUM_SLOTS = 96


def parse_casas_raw(filepath: Path) -> pd.DataFrame:
    df = pd.read_csv(
        filepath,
        header=None,
        names=["date", "time", "sensor", "state"],
        dtype={"date": str, "time": str, "sensor": str, "state": str},
        on_bad_lines="skip",
    )
    df = df.dropna(subset=["date", "time", "sensor", "state"])
    df = df[df["date"].str.match(r"^\d{4}-\d{2}-\d{2}$", na=False)]
    df["timestamp"] = pd.to_datetime(df["date"] + " " + df["time"], errors="coerce")
    df = df.dropna(subset=["timestamp"])
    df["room"] = df["sensor"].map(SENSOR_TO_ROOM)
    df = df.dropna(subset=["room"])
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df


def compute_presence_features(df: pd.DataFrame) -> dict:
    df = df[df["state"].isin(["ON", "OPEN"])].copy()
    df["slot"] = (
        df["timestamp"].dt.hour * 4 + df["timestamp"].dt.minute // 15
    ).clip(0, NUM_SLOTS - 1)

    result = {}
    for room in ROOMS:
        room_df = df[df["room"] == room]
        grouped = room_df.groupby(["date", "slot"]).size().reset_index(name="count")
        all_dates = sorted(df["date"].unique())
        matrix = []
        date_index = []
        for d in all_dates:
            day_data = grouped[grouped["date"] == d]
            row = np.zeros(NUM_SLOTS)
            for _, r in day_data.iterrows():
                row[int(r["slot"])] = r["count"]
            matrix.append(row)
            date_index.append(d)
        feature_cols = [str(i) for i in range(NUM_SLOTS)]
        features_df = pd.DataFrame(matrix, columns=feature_cols)
        features_df.insert(0, "date", [str(d) for d in date_index])
        result[room] = features_df
    return result


def load_zenodo_test(zenodo_dir: Path) -> dict:
    test_data = {}
    for room in ROOMS:
        test_file = (
            zenodo_dir
            / "Test dataset with synthetic anomalies"
            / f"test_anomalia_{room}_ARUBA.csv"
        )
        ytrue_file = zenodo_dir / "y_true" / f"y_true_{room}_ARUBA.csv"

        test_df = pd.read_csv(test_file)
        ytrue_df = pd.read_csv(ytrue_file)
        ytrue_df = ytrue_df.rename(columns={"fecha": "date"})

        test_data[room] = {
            "features": test_df,
            "labels": ytrue_df,
        }
    return test_data


def get_training_data(all_features: dict, test_data: dict) -> dict:
    training = {}
    for room in ROOMS:
        test_dates = set(test_data[room]["labels"]["date"].values)
        room_features = all_features[room].copy()
        train_mask = ~room_features["date"].isin(test_dates)
        training[room] = room_features[train_mask].reset_index(drop=True)
    return training
