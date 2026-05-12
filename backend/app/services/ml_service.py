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
            if is_anomaly:
                explainer = shap.TreeExplainer(self.models[room])
                sv = explainer.shap_values(X_scaled)[0]
                top_idx = np.argsort(np.abs(sv))[::-1][:5]
                for i in top_idx:
                    hour = i // 4
                    minute = (i % 4) * 15
                    top_features.append({
                        "time_slot": f"{hour:02d}:{minute:02d}",
                        "shap_value": round(float(sv[i]), 4),
                        "raw_value": round(float(features[room][i]), 1),
                    })

            results[room] = {
                "status": "anomaly" if is_anomaly else "normal",
                "score": round(float(score), 4),
                "top_features": top_features,
            }

        return results


ml_service = MLService()
