import numpy as np
import pandas as pd
import shap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


def explain_anomalies(
    model: IsolationForest,
    scaler: StandardScaler,
    test_features: pd.DataFrame,
    predictions: np.ndarray,
    feature_cols: list,
    room: str,
    output_dir: Path,
    top_n: int = 10,
) -> list:
    output_dir.mkdir(parents=True, exist_ok=True)

    X_test = test_features[feature_cols].values
    X_scaled = scaler.transform(X_test)
    dates = test_features["date"].values

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_scaled)

    anomaly_mask = predictions == 1
    anomaly_indices = np.where(anomaly_mask)[0]

    slot_labels = []
    for i in range(96):
        hour = i // 4
        minute = (i % 4) * 15
        slot_labels.append(f"{hour:02d}:{minute:02d}")

    explanations = []
    for idx in anomaly_indices:
        sv = shap_values[idx]
        top_indices = np.argsort(np.abs(sv))[::-1][:top_n]

        top_features = []
        for fi in top_indices:
            top_features.append({
                "feature": feature_cols[fi],
                "time_slot": slot_labels[fi] if fi < len(slot_labels) else feature_cols[fi],
                "shap_value": round(float(sv[fi]), 4),
                "actual_value": round(float(X_scaled[idx, fi]), 4),
                "raw_value": round(float(X_test[idx, fi]), 4),
            })

        explanations.append({
            "date": str(dates[idx]),
            "room": room,
            "anomaly_score": round(float(model.decision_function(X_scaled[idx:idx+1])[0]), 4),
            "top_features": top_features,
        })

    plt.figure(figsize=(12, 8))
    shap.summary_plot(
        shap_values,
        X_scaled,
        feature_names=[slot_labels[i] if i < len(slot_labels) else f"f{i}" for i in range(len(feature_cols))],
        show=False,
        max_display=20,
    )
    plt.title(f"SHAP Summary - {room}")
    plt.tight_layout()
    plt.savefig(output_dir / f"shap_summary_{room}.png", dpi=150)
    plt.close()

    if len(anomaly_indices) > 0:
        idx = anomaly_indices[0]
        plt.figure(figsize=(14, 6))
        sv = shap_values[idx]
        top_idx = np.argsort(np.abs(sv))[::-1][:15]
        labels = [slot_labels[i] if i < len(slot_labels) else f"f{i}" for i in top_idx]
        values = sv[top_idx]
        colors = ["red" if v > 0 else "blue" for v in values]
        plt.barh(range(len(labels)), values, color=colors)
        plt.yticks(range(len(labels)), labels)
        plt.xlabel("SHAP value (impact on anomaly score)")
        plt.title(f"Top features for anomaly on {dates[idx]} - {room}")
        plt.tight_layout()
        plt.savefig(output_dir / f"shap_example_{room}.png", dpi=150)
        plt.close()

    return explanations


def generate_human_readable(explanations: list) -> list:
    readable = []
    for exp in explanations:
        lines = [f"Date: {exp['date']} | Room: {exp['room']} | Score: {exp['anomaly_score']}"]
        lines.append("Top contributing time slots:")
        for feat in exp["top_features"][:5]:
            direction = "higher" if feat["shap_value"] > 0 else "lower"
            lines.append(
                f"  - {feat['time_slot']}: activity was {direction} than normal "
                f"(raw={feat['raw_value']}, SHAP={feat['shap_value']})"
            )
        readable.append("\n".join(lines))
    return readable
