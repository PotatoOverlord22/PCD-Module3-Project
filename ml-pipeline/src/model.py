import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib
from pathlib import Path

RANDOM_STATE = 42


def train_isolation_forest(
    train_features: pd.DataFrame,
    n_estimators: int = 100,
    contamination: float = 0.05,
) -> tuple:
    feature_cols = [c for c in train_features.columns if c != "date"]
    X_train = train_features[feature_cols].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_train)

    model = IsolationForest(
        n_estimators=n_estimators,
        contamination=contamination,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    model.fit(X_scaled)

    return model, scaler, feature_cols


def predict(
    model: IsolationForest,
    scaler: StandardScaler,
    test_features: pd.DataFrame,
    feature_cols: list,
) -> dict:
    X_test = test_features[feature_cols].values
    X_scaled = scaler.transform(X_test)

    raw_predictions = model.predict(X_scaled)
    anomaly_scores = model.decision_function(X_scaled)

    predictions = (raw_predictions == -1).astype(int)

    return {
        "predictions": predictions,
        "anomaly_scores": anomaly_scores,
        "dates": test_features["date"].values,
    }


def save_model(model, scaler, feature_cols, output_dir: Path, room: str):
    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump({
        "model": model,
        "scaler": scaler,
        "feature_cols": feature_cols,
    }, output_dir / f"model_{room}.joblib")


def load_model(output_dir: Path, room: str) -> tuple:
    data = joblib.load(output_dir / f"model_{room}.joblib")
    return data["model"], data["scaler"], data["feature_cols"]
