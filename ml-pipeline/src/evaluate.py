import numpy as np
import pandas as pd
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix
from pathlib import Path
import json


def evaluate_room(predictions: np.ndarray, labels: pd.DataFrame) -> dict:
    y_true = labels["y_true"].values
    y_pred = predictions

    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "true_positives": int(tp),
        "false_positives": int(fp),
        "true_negatives": int(tn),
        "false_negatives": int(fn),
        "total_samples": len(y_true),
        "total_anomalies": int(y_true.sum()),
        "predicted_anomalies": int(y_pred.sum()),
    }


LLUMIGUANO_RESULTS = {
    "Convolutional_Autoencoder": {
        "BATHROOM": {"precision": 0.82, "recall": 0.79, "f1_score": 0.80},
        "BEDROOM": {"precision": 0.79, "recall": 0.81, "f1_score": 0.80},
        "KITCHEN": {"precision": 0.85, "recall": 0.83, "f1_score": 0.84},
        "LIVING_ROOM": {"precision": 0.80, "recall": 0.78, "f1_score": 0.79},
    },
    "Isolation_Forest_baseline": {
        "BATHROOM": {"precision": 0.72, "recall": 0.68, "f1_score": 0.70},
        "BEDROOM": {"precision": 0.70, "recall": 0.65, "f1_score": 0.67},
        "KITCHEN": {"precision": 0.75, "recall": 0.71, "f1_score": 0.73},
        "LIVING_ROOM": {"precision": 0.71, "recall": 0.66, "f1_score": 0.68},
    },
    "OC_SVM": {
        "BATHROOM": {"precision": 0.74, "recall": 0.70, "f1_score": 0.72},
        "BEDROOM": {"precision": 0.72, "recall": 0.67, "f1_score": 0.69},
        "KITCHEN": {"precision": 0.77, "recall": 0.73, "f1_score": 0.75},
        "LIVING_ROOM": {"precision": 0.73, "recall": 0.68, "f1_score": 0.70},
    },
}


def build_comparison_table(our_results: dict) -> pd.DataFrame:
    rows = []
    for room in our_results:
        row = {"room": room}
        ours = our_results[room]
        row["our_IF_SHAP_precision"] = ours["precision"]
        row["our_IF_SHAP_recall"] = ours["recall"]
        row["our_IF_SHAP_f1"] = ours["f1_score"]

        for method, method_results in LLUMIGUANO_RESULTS.items():
            if room in method_results:
                row[f"{method}_precision"] = method_results[room]["precision"]
                row[f"{method}_recall"] = method_results[room]["recall"]
                row[f"{method}_f1"] = method_results[room]["f1_score"]

        rows.append(row)

    return pd.DataFrame(rows)


def save_results(our_results: dict, comparison_table: pd.DataFrame, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "evaluation_results.json", "w") as f:
        json.dump(our_results, f, indent=2)

    comparison_table.to_csv(output_dir / "comparison_table.csv", index=False)

    print("\n=== Evaluation Results ===")
    for room, metrics in our_results.items():
        print(f"\n{room}:")
        print(f"  Precision: {metrics['precision']}")
        print(f"  Recall:    {metrics['recall']}")
        print(f"  F1-Score:  {metrics['f1_score']}")
        print(f"  TP={metrics['true_positives']} FP={metrics['false_positives']} "
              f"TN={metrics['true_negatives']} FN={metrics['false_negatives']}")

    print("\n=== Comparison Table ===")
    print(comparison_table.to_string(index=False))
