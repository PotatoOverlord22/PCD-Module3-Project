import json
import csv
from pathlib import Path

OUTPUTS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ml-pipeline" / "outputs"
ROOMS = ["BATHROOM", "BEDROOM", "KITCHEN", "LIVING_ROOM"]


class DataService:
    def __init__(self):
        self.evaluation = {}
        self.explanations = {}
        self.days = {}
        self._load()

    def _load(self):
        eval_path = OUTPUTS_DIR / "evaluation_results.json"
        if eval_path.exists():
            with open(eval_path) as f:
                self.evaluation = json.load(f)

        expl_path = OUTPUTS_DIR / "explanations.json"
        if expl_path.exists():
            with open(expl_path) as f:
                self.explanations = json.load(f)

        self._build_days_index()

    def _build_days_index(self):
        for room, anomalies in self.explanations.items():
            for entry in anomalies:
                date = entry["date"]
                if date not in self.days:
                    self.days[date] = {"date": date, "rooms": {}}
                self.days[date]["rooms"][room] = {
                    "status": "anomaly",
                    "score": entry["anomaly_score"],
                    "top_features": entry["top_features"][:5],
                }

        data_dir = OUTPUTS_DIR.parent.parent / "data" / "raw" / "zenodo_test" / "CASAS" / "ARUBA"
        for room in ROOMS:
            ytrue_path = data_dir / "y_true" / f"y_true_{room}_ARUBA.csv"
            if not ytrue_path.exists():
                continue
            with open(ytrue_path) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    date = row["fecha"] if "fecha" in row else row.get("date", "")
                    label = int(row["y_true"])
                    if date not in self.days:
                        self.days[date] = {"date": date, "rooms": {}}
                    if room not in self.days[date]["rooms"]:
                        self.days[date]["rooms"][room] = {
                            "status": "normal" if label == 0 else "anomaly",
                            "score": 0.0,
                            "top_features": [],
                        }

    def get_all_days(self) -> list:
        return sorted(self.days.values(), key=lambda d: d["date"])

    def get_day(self, date: str) -> dict | None:
        return self.days.get(date)

    def get_anomalies(self) -> list:
        result = []
        for day in self.days.values():
            has_anomaly = any(
                r["status"] == "anomaly" for r in day["rooms"].values()
            )
            if has_anomaly:
                result.append(day)
        return sorted(result, key=lambda d: d["date"])

    def get_evaluation(self) -> dict:
        return self.evaluation


data_service = DataService()
