import sys
import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

from .data_parser import ROOMS, parse_casas_raw, compute_presence_features, load_zenodo_test, get_training_data
from .model import train_isolation_forest, predict, save_model
from .evaluate import evaluate_room, build_comparison_table, save_results
from .explainer import explain_anomalies, generate_human_readable
from .config import MONGO_URI, MONGO_DB_NAME

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "raw"
ZENODO_DIR = DATA_DIR / "zenodo_test" / "CASAS" / "ARUBA"
OUTPUT_DIR = PROJECT_ROOT / "ml-pipeline" / "outputs"

CASAS_RAW_PATHS = [
    DATA_DIR / "aruba.csv",
    DATA_DIR / "data",
    DATA_DIR / "Aruba",
]

# How many human-readable explanations to preview on the console per room.
# Keeps terminal output manageable while still giving a quick sanity check.
CONSOLE_PREVIEW_COUNT = 3


def find_casas_raw():
    for p in CASAS_RAW_PATHS:
        if p.exists():
            return p
    return None


def run_with_raw_data():
    print("=== Loading raw CASAS Aruba data ===")
    raw_path = find_casas_raw()
    if raw_path is None:
        return None

    print(f"Parsing {raw_path}...")
    df = parse_casas_raw(raw_path)
    print(f"Parsed {len(df)} events, {df['date'].nunique()} days")

    print("Computing per-room presence features...")
    all_features = compute_presence_features(df)
    for room in ROOMS:
        print(f"  {room}: {len(all_features[room])} days")

    return all_features


def run_zenodo_only_mode():
    print("=== Running in Zenodo-only mode (no raw CASAS data) ===")
    print("Training on non-anomalous days from the Zenodo test set itself")
    print("(This is a fallback — download raw CASAS data for full pipeline)")

    test_data = load_zenodo_test(ZENODO_DIR)
    training_data = {}
    for room in ROOMS:
        features = test_data[room]["features"]
        labels = test_data[room]["labels"]
        normal_mask = labels["y_true"] == 0
        normal_dates = labels[normal_mask]["date"].values
        train_df = features[features["date"].isin(normal_dates)]
        training_data[room] = train_df

    return training_data, test_data


# ---------------------------------------------------------------------------
# MongoDB helpers
# ---------------------------------------------------------------------------

def _get_mongo_db():
    """Return a pymongo Database handle, or None if MongoDB is not configured."""
    if not MONGO_URI:
        return None
    try:
        from pymongo import MongoClient
        client = MongoClient(MONGO_URI)
        # Quick connectivity check
        client.admin.command("ping")
        db = client[MONGO_DB_NAME]
        print(f"[pipeline] Connected to MongoDB Atlas — database: {MONGO_DB_NAME}")
        return db
    except Exception as e:
        print(f"[pipeline] WARNING: Could not connect to MongoDB: {e}")
        print("[pipeline] Results will only be saved to local files.")
        return None


def _write_results_to_mongo(db, all_explanations, all_results):
    """Write anomaly days, normal days, and evaluation results to MongoDB."""
    # --- Collect all test dates with their ground-truth labels ---
    test_data = load_zenodo_test(ZENODO_DIR)

    # Build a dict: date -> {room -> {status, score, top_features, explanation}}
    days = {}

    # First, populate from ground-truth labels (so we get normal days too)
    for room in ROOMS:
        labels = test_data[room]["labels"]
        for _, row in labels.iterrows():
            date = row["date"]
            label = int(row["y_true"])
            if date not in days:
                days[date] = {"date": date, "rooms": {}}
            if room not in days[date]["rooms"]:
                days[date]["rooms"][room] = {
                    "status": "anomaly" if label == 1 else "normal",
                    "score": 0.0,
                    "top_features": [],
                    "explanation": None,
                }

    # Then overlay with SHAP explanations for detected anomalies
    for room, explanations in all_explanations.items():
        readable_list = generate_human_readable(explanations)
        for exp, readable_text in zip(explanations, readable_list):
            date = exp["date"]
            if date not in days:
                days[date] = {"date": date, "rooms": {}}
            days[date]["rooms"][room] = {
                "status": "anomaly",
                "score": exp["anomaly_score"],
                "top_features": exp["top_features"][:5],
                "explanation": readable_text,
            }

    # --- Write anomaly_days collection ---
    collection = db.anomaly_days
    bulk_ops = []
    from pymongo import ReplaceOne
    for date, day_doc in days.items():
        day_doc["_id"] = date
        bulk_ops.append(ReplaceOne({"_id": date}, day_doc, upsert=True))

    if bulk_ops:
        result = collection.bulk_write(bulk_ops)
        print(f"[pipeline] MongoDB anomaly_days: "
              f"{result.upserted_count} inserted, {result.modified_count} updated")

    # --- Write evaluation_results collection (idempotent: single document, replaced each run) ---
    eval_doc = {
        "_id": "latest",
        "run_date": datetime.now(timezone.utc).isoformat(),
        "results": all_results,
    }
    db.evaluation_results.replace_one({"_id": "latest"}, eval_doc, upsert=True)
    print(f"[pipeline] MongoDB evaluation_results: upserted 'latest' document")


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main():
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Data dir: {DATA_DIR}")
    print(f"Zenodo dir: {ZENODO_DIR}")
    print(f"Output dir: {OUTPUT_DIR}")

    if not ZENODO_DIR.exists():
        print(f"\nERROR: Zenodo test set not found at {ZENODO_DIR}")
        print("Run: ./data/download.sh")
        sys.exit(1)

    test_data = load_zenodo_test(ZENODO_DIR)
    print(f"\nLoaded Zenodo test set:")
    for room in ROOMS:
        n = len(test_data[room]["labels"])
        n_anom = test_data[room]["labels"]["y_true"].sum()
        print(f"  {room}: {n} days, {n_anom} anomalies")

    raw_features = run_with_raw_data()

    if raw_features is not None:
        training_data = get_training_data(raw_features, test_data)
    else:
        print("\nRaw CASAS data not found, using Zenodo-only fallback")
        training_data, test_data = run_zenodo_only_mode()

    all_results = {}
    all_explanations = {}

    for room in ROOMS:
        print(f"\n{'='*50}")
        print(f"Processing {room}")
        print(f"{'='*50}")

        train_df = training_data[room]
        test_df = test_data[room]["features"]
        labels = test_data[room]["labels"]

        feature_cols = [c for c in test_df.columns if c != "date"]

        train_aligned = train_df[["date"] + feature_cols].copy()

        print(f"Training samples: {len(train_aligned)}")
        print(f"Test samples: {len(test_df)}")

        model, scaler, fcols = train_isolation_forest(train_aligned)
        save_model(model, scaler, fcols, OUTPUT_DIR, room)

        results = predict(model, scaler, test_df, fcols)
        predictions = results["predictions"]

        metrics = evaluate_room(predictions, labels)
        all_results[room] = metrics

        print(f"  F1={metrics['f1_score']} P={metrics['precision']} R={metrics['recall']}")

        print(f"  Generating SHAP explanations...")
        explanations = explain_anomalies(
            model, scaler, test_df, predictions, fcols, room, OUTPUT_DIR
        )
        all_explanations[room] = explanations

        readable = generate_human_readable(explanations[:CONSOLE_PREVIEW_COUNT])
        for r in readable:
            print(f"\n{r}")

    comparison = build_comparison_table(all_results)
    save_results(all_results, comparison, OUTPUT_DIR)

    # --- Save structured explanations as JSON (local file) ---
    with open(OUTPUT_DIR / "explanations.json", "w") as f:
        json.dump(all_explanations, f, indent=2, default=str)

    # --- Save human-readable explanations as text (local file) ---
    with open(OUTPUT_DIR / "explanations_readable.txt", "w") as f:
        for room, explanations in all_explanations.items():
            f.write(f"\n{'='*60}\n")
            f.write(f"  {room}\n")
            f.write(f"{'='*60}\n\n")
            for text in generate_human_readable(explanations):
                f.write(text + "\n\n")
    print(f"Human-readable explanations saved to {OUTPUT_DIR / 'explanations_readable.txt'}")

    # --- Write results to MongoDB (if configured) ---
    db = _get_mongo_db()
    if db is not None:
        _write_results_to_mongo(db, all_explanations, all_results)

    print(f"\n{'='*50}")
    print("Pipeline complete!")
    print(f"Results saved to {OUTPUT_DIR}")
    if db is not None:
        print(f"Results also written to MongoDB Atlas ({MONGO_DB_NAME})")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
