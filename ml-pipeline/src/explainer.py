import numpy as np
import pandas as pd
import shap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

# ---------------------------------------------------------------------------
# Constants – every "magic number" is named and explained here
# ---------------------------------------------------------------------------

# SHAP magnitude thresholds for human-readable intensity words.
# Calibrated from the actual SHAP distribution across 2220 top-feature values
# in the CASAS Aruba test set (min=0.087, median=0.352, max=0.990):
#   - P25 ≈ 0.27  →  bottom ~20% are "slightly" contributing
#   - P75 ≈ 0.47  →  middle ~55% are "moderately" contributing
#   - Above P75   →  top ~25% are "significantly" contributing
SHAP_THRESHOLD_SLIGHT = 0.25
SHAP_THRESHOLD_MODERATE = 0.45

# Time-of-day boundaries (hour, inclusive start).
# Based on common daily-routine segmentation for elderly home monitoring:
#   00:00–05:59  ->  "night"     (sleep period)
#   06:00–11:59  ->  "morning"   (wake-up, breakfast, chores)
#   12:00–17:59  ->  "afternoon" (lunch, activities)
#   18:00–23:59  ->  "evening"   (dinner, winding down)
NIGHT_END_HOUR = 6
MORNING_END_HOUR = 12
AFTERNOON_END_HOUR = 18

# How many top SHAP features to store per detected anomaly.
# 10 captures enough signal for downstream analysis without bloating the JSON.
TOP_N_FEATURES_PER_ANOMALY = 10

# How many top features to show in the human-readable plain-text summary.
# 5 keeps the explanation concise while covering the main drivers.
TOP_FEATURES_IN_READABLE = 5

# SHAP summary plot: max features displayed on the global beeswarm chart.
# 20 is the SHAP library default and gives a good overview without clutter.
SHAP_SUMMARY_MAX_DISPLAY = 20

# Per-anomaly example bar chart: number of top features to plot.
# 15 provides detailed drill-down for the single-day example.
SHAP_EXAMPLE_TOP_FEATURES = 15

# Resolution (dots per inch) for saved matplotlib figures.
# 150 DPI balances file size with readability in reports.
PLOT_DPI = 150

# Number of 15-minute time slots in a day (24 h * 4 slots/h = 96).
NUM_TIME_SLOTS = 96

# Figure sizes (width, height in inches) for the two plot types.
SUMMARY_FIGURE_SIZE = (12, 8)
EXAMPLE_FIGURE_SIZE = (14, 6)


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _time_of_day(hour: int) -> str:
    """Return a human-friendly period label for the given hour (0-23)."""
    if hour < NIGHT_END_HOUR:
        return "night"
    if hour < MORNING_END_HOUR:
        return "morning"
    if hour < AFTERNOON_END_HOUR:
        return "afternoon"
    return "evening"


def _magnitude_word(shap_value: float) -> str:
    """Translate an absolute SHAP value into an intensity qualifier."""
    abs_val = abs(shap_value)
    if abs_val < SHAP_THRESHOLD_SLIGHT:
        return "slightly"
    if abs_val < SHAP_THRESHOLD_MODERATE:
        return "moderately"
    return "significantly"


def _build_slot_labels() -> list:
    """Create human-readable 'HH:MM' labels for each 15-min slot."""
    labels = []
    for i in range(NUM_TIME_SLOTS):
        hour = i // 4
        minute = (i % 4) * 15
        labels.append(f"{hour:02d}:{minute:02d}")
    return labels


# ---------------------------------------------------------------------------
# Core explanation functions
# ---------------------------------------------------------------------------

def explain_anomalies(
    model: IsolationForest,
    scaler: StandardScaler,
    test_features: pd.DataFrame,
    predictions: np.ndarray,
    feature_cols: list,
    room: str,
    output_dir: Path,
    top_n: int = TOP_N_FEATURES_PER_ANOMALY,
) -> list:
    """Compute SHAP-based explanations for every detected anomaly.

    Returns a list of dicts, one per anomalous day, each containing the date,
    room, anomaly score, and the top_n most influential time-slot features
    with their SHAP values and raw sensor counts.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    X_test = test_features[feature_cols].values
    X_scaled = scaler.transform(X_test)
    dates = test_features["date"].values

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_scaled)

    anomaly_mask = predictions == 1
    anomaly_indices = np.where(anomaly_mask)[0]

    slot_labels = _build_slot_labels()

    explanations = []
    for idx in anomaly_indices:
        sv = shap_values[idx]
        top_indices = np.argsort(np.abs(sv))[::-1][:top_n]

        # Training means (before scaling) — used for "higher/lower than normal"
        training_means = scaler.mean_

        top_features = []
        for fi in top_indices:
            top_features.append({
                "feature": feature_cols[fi],
                "time_slot": slot_labels[fi] if fi < len(slot_labels) else feature_cols[fi],
                "shap_value": round(float(sv[fi]), 4),
                "actual_value": round(float(X_scaled[idx, fi]), 4),
                "raw_value": round(float(X_test[idx, fi]), 4),
                "training_mean": round(float(training_means[fi]), 1),
            })

        explanations.append({
            "date": str(dates[idx]),
            "room": room,
            "anomaly_score": round(float(model.decision_function(X_scaled[idx:idx + 1])[0]), 4),
            "top_features": top_features,
        })

    # --- Global SHAP summary plot ---
    plt.figure(figsize=SUMMARY_FIGURE_SIZE)
    shap.summary_plot(
        shap_values,
        X_scaled,
        feature_names=[
            slot_labels[i] if i < len(slot_labels) else f"f{i}"
            for i in range(len(feature_cols))
        ],
        show=False,
        max_display=SHAP_SUMMARY_MAX_DISPLAY,
    )
    plt.title(f"SHAP Summary - {room}")
    plt.tight_layout()
    plt.savefig(output_dir / f"shap_summary_{room}.png", dpi=PLOT_DPI)
    plt.close()

    # --- Single-anomaly example bar chart ---
    if len(anomaly_indices) > 0:
        idx = anomaly_indices[0]
        plt.figure(figsize=EXAMPLE_FIGURE_SIZE)
        sv = shap_values[idx]
        top_idx = np.argsort(np.abs(sv))[::-1][:SHAP_EXAMPLE_TOP_FEATURES]
        labels = [slot_labels[i] if i < len(slot_labels) else f"f{i}" for i in top_idx]
        values = sv[top_idx]
        colors = ["red" if v > 0 else "blue" for v in values]
        plt.barh(range(len(labels)), values, color=colors)
        plt.yticks(range(len(labels)), labels)
        plt.xlabel("SHAP value (impact on anomaly score)")
        plt.title(f"Top features for anomaly on {dates[idx]} - {room}")
        plt.tight_layout()
        plt.savefig(output_dir / f"shap_example_{room}.png", dpi=PLOT_DPI)
        plt.close()

    return explanations


def generate_human_readable(explanations: list) -> list:
    """Convert structured SHAP explanations into rich plain-text paragraphs.

    Each anomaly gets:
      1. A header line with date, room, and anomaly score.
      2. A one-sentence summary synthesising the dominant pattern.
      3. A bullet list of the top contributing time slots with magnitude
         qualifiers ("slightly / moderately / significantly") and
         time-of-day context ("morning / afternoon / evening / night").
    """
    readable = []
    for exp in explanations:
        lines = [
            f"Date: {exp['date']} | Room: {exp['room']} | Anomaly Score: {exp['anomaly_score']}"
        ]

        # --- Build a one-sentence summary from the top features ---
        top = exp["top_features"][:TOP_FEATURES_IN_READABLE]
        higher_periods = []
        lower_periods = []
        for feat in top:
            hour = int(feat["time_slot"].split(":")[0])
            period = _time_of_day(hour)
            # Direction determined by comparing raw value against training mean
            mean = feat.get("training_mean", 0)
            if feat["raw_value"] >= mean:
                if period not in higher_periods:
                    higher_periods.append(period)
            else:
                if period not in lower_periods:
                    lower_periods.append(period)

        summary_parts = []
        if higher_periods:
            summary_parts.append(
                f"unusually high activity during the {'/'.join(higher_periods)}"
            )
        if lower_periods:
            summary_parts.append(
                f"lower-than-expected activity during the {'/'.join(lower_periods)}"
            )
        if summary_parts:
            lines.append(
                f"Summary: This day was flagged mainly due to {' and '.join(summary_parts)}."
            )

        # --- Detailed per-slot breakdown ---
        lines.append("Top contributing time slots:")
        for feat in top:
            hour = int(feat["time_slot"].split(":")[0])
            period = _time_of_day(hour)
            magnitude = _magnitude_word(feat["shap_value"])
            mean = feat.get("training_mean", 0)
            raw = feat["raw_value"]
            direction = "higher" if raw >= mean else "lower"

            # Concrete comparison: "12 events vs typical 2"
            raw_int = int(raw) if raw == int(raw) else raw
            mean_display = int(mean) if mean == int(mean) else mean
            lines.append(
                f"  - {feat['time_slot']} ({period}): {raw_int} sensor events vs "
                f"typical {mean_display} — {magnitude} {direction} than normal"
            )

        readable.append("\n".join(lines))
    return readable
