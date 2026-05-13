import numpy as np
import joblib
import shap
from pathlib import Path

OUTPUTS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ml-pipeline" / "outputs"
ROOMS = ["BATHROOM", "BEDROOM", "KITCHEN", "LIVING_ROOM"]
NUM_SLOTS = 96

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
}

# ---------------------------------------------------------------------------
# Explanation constants (mirrored from ml-pipeline/src/explainer.py)
# Kept as a lightweight copy so the backend has zero dependency on the
# ml-pipeline package — each deploys independently.
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

# How many top features to include in the explanation response.
# 5 keeps the explanation concise while covering the main drivers.
TOP_FEATURES_IN_EXPLANATION = 5


# ---------------------------------------------------------------------------
# Explanation helpers
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


def _generate_explanation(room: str, score: float, top_features: list) -> str:
    """Build a human-readable explanation string for a single anomalous room.

    This is a lightweight copy of the ml-pipeline's generate_human_readable(),
    adapted for the live /predict endpoint where we have a single room result
    rather than a list of batch explanations.
    """
    lines = [f"Room: {room} | Anomaly Score: {round(score, 4)}"]

    # --- Summary sentence ---
    higher_periods = []
    lower_periods = []
    for feat in top_features[:TOP_FEATURES_IN_EXPLANATION]:
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

    # --- Per-slot breakdown ---
    lines.append("Top contributing time slots:")
    for feat in top_features[:TOP_FEATURES_IN_EXPLANATION]:
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

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# ML Service
# ---------------------------------------------------------------------------

class MLService:
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.feature_cols = {}
        self._load_models()

    def _load_models(self):
        for room in ROOMS:
            path = OUTPUTS_DIR / f"model_{room}.joblib"
            if path.exists():
                data = joblib.load(path)
                self.models[room] = data["model"]
                self.scalers[room] = data["scaler"]
                self.feature_cols[room] = data["feature_cols"]

    def compute_features_from_events(self, events: list) -> dict:
        room_features = {}
        for room in ROOMS:
            counts = np.zeros(NUM_SLOTS)
            for ev in events:
                mapped_room = SENSOR_TO_ROOM.get(ev.get("sensor"))
                if mapped_room != room:
                    continue
                state = ev.get("state", "")
                if state not in ("ON", "OPEN"):
                    continue
                time_str = ev.get("time", "")
                try:
                    parts = time_str.split(":")
                    hour = int(parts[0])
                    minute = int(parts[1].split(".")[0])
                    slot = hour * 4 + minute // 15
                    slot = min(max(slot, 0), NUM_SLOTS - 1)
                    counts[slot] += 1
                except (ValueError, IndexError):
                    continue
            room_features[room] = counts
        return room_features

    def predict_day(self, events: list) -> dict:
        features = self.compute_features_from_events(events)
        results = {}

        for room in ROOMS:
            if room not in self.models:
                continue

            X = features[room].reshape(1, -1)
            X_scaled = self.scalers[room].transform(X)

            prediction = self.models[room].predict(X_scaled)[0]
            score = self.models[room].decision_function(X_scaled)[0]
            is_anomaly = prediction == -1

            top_features = []
            explanation = None

            if is_anomaly:
                explainer = shap.TreeExplainer(self.models[room])
                sv = explainer.shap_values(X_scaled)[0]
                training_means = self.scalers[room].mean_
                top_idx = np.argsort(np.abs(sv))[::-1][:TOP_FEATURES_IN_EXPLANATION]
                for i in top_idx:
                    hour = i // 4
                    minute = (i % 4) * 15
                    top_features.append({
                        "time_slot": f"{hour:02d}:{minute:02d}",
                        "shap_value": round(float(sv[i]), 4),
                        "raw_value": round(float(features[room][i]), 1),
                        "training_mean": round(float(training_means[i]), 1),
                    })

                explanation = _generate_explanation(room, float(score), top_features)

            results[room] = {
                "status": "anomaly" if is_anomaly else "normal",
                "score": round(float(score), 4),
                "top_features": top_features,
                "explanation": explanation,
            }

        return results


ml_service = MLService()
