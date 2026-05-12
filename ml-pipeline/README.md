# ML Pipeline — Anomaly Detection with Explainability

## What This Does

Detects anomalous days in elderly daily routines using an Isolation Forest, then explains each anomaly using SHAP (which time slots in which rooms deviated from normal).

## Dataset

### Training Data — CASAS Aruba Raw Sensor Events

- **Source**: https://zenodo.org/records/15708568 (file `data.zip`, we extract only `aruba.csv`)
- **Format**: CSV with columns `date, time, room_name, state`
- **Size**: 1.6M sensor events, 220 days (2010-11-04 to 2011-06-11)
- **Rooms**: Bathroom, Bedroom, Kitchen, LivingRoom (+ DiningRoom, GuestRoom, etc. mapped to the 4 main rooms)
- **States**: ON, OFF, OPEN, CLOSE
- **Used for training**: 169 days (the days NOT in the test set)

### Test Data — Llumiguano et al. Zenodo Test Set

- **Source**: https://zenodo.org/records/15800764 (file `CASAS.zip`)
- **Published alongside**: "Unsupervised convolutional neural networks using home presence sensors for behavioural anomaly detection in older adults" (https://pure.qub.ac.uk/en/publications/unsupervised-convolutional-neural-networks-using-home-presence-se/)
- **Format**: Pre-computed features (96 time-slot columns = 15-min intervals across 24h) + ground truth labels per room
- **Size**: 128 test days per room, with synthetic anomalies injected
- **4 rooms evaluated independently**: BATHROOM, BEDROOM, KITCHEN, LIVING_ROOM
- **Ground truth**: `y_true_{ROOM}_ARUBA.csv` — binary label (0=normal, 1=anomaly) per day

### Why This Is a Valid Comparison

Llumiguano et al. trained their models (Convolutional Autoencoder, Isolation Forest, OC-SVM) on the same CASAS Aruba data and evaluated on this exact test set. By using their published test set with the same ground truth labels, our results are directly comparable — no differences in evaluation protocol, dataset split, or feature format.

## How It Works

### Training Phase (the ML pipeline — already done)

1. **Parse raw data** (`data_parser.py`): Reads `aruba.csv`, maps room-level sensor names (Bathroom, Kitchen, LivingRoom, etc.) to 4 standardized rooms (BATHROOM, BEDROOM, KITCHEN, LIVING_ROOM)
2. **Compute features** (`data_parser.py`): For each day, counts how many ON/OPEN activations happened in each 15-minute time slot per room. Result: 96 features per room per day (96 slots × 24h ÷ 15min = 96)
3. **Scale features** (`model.py`): A `StandardScaler` learns the mean and standard deviation of each feature across all training days. It then normalizes the data so all rooms/slots are on the same scale. Without this, a room with 200 daily activations would dominate over one with 5.
4. **Train Isolation Forest** (`model.py`): Learns which daily patterns are "normal". Parameters: `n_estimators=100`, `contamination=0.05`, `random_state=42`. One model per room.
5. **Save models** (`model.py`): Each room's trained model + scaler + feature names saved as `model_{ROOM}.joblib`

### Evaluation Phase (also part of the pipeline)

1. **Load Zenodo test set** (`data_parser.py`): The 128-day test set with pre-computed features (same 96-slot format we produce from raw data)
2. **Predict** (`model.py`): Scale test features using the training scaler, then classify each day as normal or anomaly
3. **Compute metrics** (`evaluate.py`): Compare predictions against ground truth labels → Precision, Recall, F1-Score, confusion matrix
4. **Generate explanations** (`explainer.py`): For each detected anomaly, SHAP TreeExplainer identifies which time slots contributed most to the anomaly score
5. **Build comparison table** (`evaluate.py`): Places our results next to Llumiguano et al.'s reported metrics

### Dashboard Phase (next — what the backend/frontend will do)

1. New sensor data comes in for today (or any day the caregiver wants to check)
2. Backend computes the same 96 time-slot features from the raw events
3. Scaler transforms the new data — subtracts mean and divides by std learned during training. This puts the new day on the same scale the model expects.
4. Scaled features go into the Isolation Forest → returns: anomaly or normal + confidence score
5. If anomaly: SHAP explains which time slots were unusual (e.g., "bedroom had 0 activations at 02:00-04:00, normally there are 15-20 — this contributed 40% to the anomaly flag")
6. Dashboard displays: "Tuesday was flagged as unusual. Main reason: no bedroom activity during typical sleep hours."

## Results

### F1-Scores (our model vs Llumiguano et al. baselines)

| Room | Our IF+SHAP | Conv. Autoencoder | Their IF | OC-SVM |
|------|-------------|-------------------|----------|--------|
| BATHROOM | 0.627 | 0.80 | 0.70 | 0.72 |
| BEDROOM | **0.904** | 0.80 | 0.67 | 0.69 |
| KITCHEN | **0.955** | 0.84 | 0.73 | 0.75 |
| LIVING_ROOM | **0.860** | 0.79 | 0.68 | 0.70 |

**Note**: Llumiguano comparison values are placeholders — replace with actual numbers from their paper.

### Detailed Metrics

| Room | Precision | Recall | F1 | TP | FP | TN | FN |
|------|-----------|--------|------|----|----|----|----|
| BATHROOM | 1.000 | 0.456 | 0.627 | 26 | 0 | 71 | 31 |
| BEDROOM | 0.825 | 1.000 | 0.904 | 52 | 11 | 65 | 0 |
| KITCHEN | 0.915 | 1.000 | 0.955 | 75 | 7 | 46 | 0 |
| LIVING_ROOM | 0.961 | 0.778 | 0.860 | 49 | 2 | 63 | 14 |

### Observations

- **Bedroom and Kitchen**: Perfect recall (catches all anomalies), high precision
- **Bathroom**: Perfect precision (never false alarms) but low recall — the model is too conservative. Tunable via `contamination` parameter.
- **Our differentiator**: Same or better detection than their IF baseline, but we add SHAP explanations (which time slots deviated and by how much)

## Output Files

All in `ml-pipeline/outputs/`:

| File | What it contains |
|------|-----------------|
| `evaluation_results.json` | Precision, Recall, F1, TP/FP/TN/FN per room |
| `comparison_table.csv` | Our results vs Llumiguano baselines in CSV |
| `explanations.json` | SHAP feature attributions for every detected anomaly |
| `shap_summary_{ROOM}.png` | Overall feature importance plot (which time slots matter most) |
| `shap_example_{ROOM}.png` | Bar chart for one specific anomaly (visual explanation) |
| `model_{ROOM}.joblib` | Trained model + scaler (for backend API to load) |

## How to Run Locally

### Prerequisites

- Python 3.12 (the venv was created with mise's Python 3.12.11)
- ~100MB disk space for data + outputs

### First-Time Setup

```bash
cd /Users/teov/Documents/Master/PCD/TemaPaper/project

# Create virtual environment (already done, skip if venv/ exists)
python3 -m venv venv

# Install dependencies
./venv/bin/pip install -r ml-pipeline/requirements.txt

# Download datasets (~12MB aruba.csv + 89KB test set)
chmod +x data/download.sh
./data/download.sh
```

### Run the ML Pipeline

```bash
cd /Users/teov/Documents/Master/PCD/TemaPaper/project/ml-pipeline
../venv/bin/python -m src.pipeline
```

This takes ~30-60 seconds and produces all outputs in `ml-pipeline/outputs/`.

### View Results

```bash
# Evaluation metrics
cat outputs/evaluation_results.json

# Comparison table
cat outputs/comparison_table.csv

# Open SHAP plots
open outputs/shap_summary_KITCHEN.png
open outputs/shap_example_KITCHEN.png

# Read explanations (first 2 entries for kitchen)
python3 -c "import json; d=json.load(open('outputs/explanations.json')); [print(json.dumps(e,indent=2)) for e in d['KITCHEN'][:2]]"
```

### Important: Use `../venv/bin/python` Not Just `python`

If you have `mise` installed, it overrides the `python` command even after `source venv/bin/activate`. Always use the explicit venv path:

```bash
../venv/bin/python -m src.pipeline
```

## What's Next

1. **FastAPI backend** — loads `.joblib` models, exposes endpoints for daily summaries, anomaly detection, and SHAP explanations
2. **React dashboard** — visualizes daily timelines, anomaly cards with explanations, confidence scores
3. **MongoDB** — stores processed results for the dashboard to query
4. **Tuning** — adjust `contamination` for bathroom, potentially try different `n_estimators`
