"""Service that provides anomaly day data and evaluation results.

When a MongoDB connection is available (MONGO_URI is set), all reads come
from the database.  Otherwise the service falls back to loading the local
JSON / CSV files produced by the ml-pipeline — so the app still works
without a database configured.
"""

import json
import csv
from pathlib import Path

from app.services.mongo_service import get_db

OUTPUTS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ml-pipeline" / "outputs"
ROOMS = ["BATHROOM", "BEDROOM", "KITCHEN", "LIVING_ROOM"]


class DataService:
    def __init__(self):
        self._db = get_db()

        # Local-file fallback caches (only populated when MongoDB is unavailable)
        self.evaluation: dict = {}
        self.explanations: dict = {}
        self.days: dict = {}

        if self._db is None:
            print("[data_service] No MongoDB — loading from local files")
            self._load_from_files()
        else:
            print("[data_service] Using MongoDB for data reads")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_all_days(self) -> list:
        if self._db is not None:
            docs = list(self._db.anomaly_days.find().sort("date", 1))
            return [self._strip_mongo_id(d) for d in docs]
        return sorted(self.days.values(), key=lambda d: d["date"])

    def get_day(self, date: str) -> dict | None:
        if self._db is not None:
            doc = self._db.anomaly_days.find_one({"_id": date})
            return self._strip_mongo_id(doc) if doc else None
        return self.days.get(date)

    def get_anomalies(self) -> list:
        if self._db is not None:
            # Find days where at least one room has status "anomaly"
            all_days = list(self._db.anomaly_days.find().sort("date", 1))
            result = []
            for doc in all_days:
                rooms = doc.get("rooms", {})
                has_anomaly = any(
                    r.get("status") == "anomaly" for r in rooms.values()
                )
                if has_anomaly:
                    result.append(self._strip_mongo_id(doc))
            return result
        # File fallback
        result = []
        for day in self.days.values():
            has_anomaly = any(
                r["status"] == "anomaly" for r in day["rooms"].values()
            )
            if has_anomaly:
                result.append(day)
        return sorted(result, key=lambda d: d["date"])

    def get_evaluation(self) -> dict:
        if self._db is not None:
            doc = self._db.evaluation_results.find_one(
                sort=[("run_date", -1)]
            )
            if doc:
                doc.pop("_id", None)
                return doc.get("results", doc)
        return self.evaluation

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _strip_mongo_id(doc: dict | None) -> dict | None:
        """Remove the MongoDB ``_id`` field so responses are JSON-serializable."""
        if doc is None:
            return None
        doc.pop("_id", None)
        return doc

    # ------------------------------------------------------------------
    # Local-file fallback (original behaviour)
    # ------------------------------------------------------------------

    def _load_from_files(self):
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


data_service = DataService()
