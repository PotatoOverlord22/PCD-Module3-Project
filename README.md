# Caregiver Dashboard for Explainable Daily Activity Monitoring

## Research Question

Can an Isolation Forest model with SHAP-based explanations identify deviations in elderly daily activity routines with comparable accuracy to deep learning methods, while also providing human-interpretable explanations of which activities deviated and why?

## Team

- Teodora Vlad
- Raul Tiron
- Cosmin Stan
- Miruna Varzar

## Project Structure

```
project/
├── data/
│   ├── download.sh                  # Downloads CASAS Aruba + Zenodo test set
│   ├── sample_day.csv               # Sample file for testing the Simulate feature
│   └── raw/
│       ├── aruba.csv                # Raw CASAS Aruba sensor data (1.6M events, 220 days)
│       └── zenodo_test/CASAS/ARUBA/ # Llumiguano et al. test set + ground truth
├── ml-pipeline/
│   ├── src/
│   │   ├── data_parser.py           # Parse aruba.csv → structured events, compute features
│   │   ├── model.py                 # Train Isolation Forest, predict, save/load models
│   │   ├── evaluate.py              # P/R/F1 metrics + comparison table
│   │   ├── explainer.py             # SHAP explanations + plots
│   │   └── pipeline.py              # End-to-end orchestrator
│   ├── outputs/                     # Trained models, results, SHAP plots
│   ├── requirements.txt
│   └── README.md                    # Detailed ML pipeline documentation
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app
│   │   ├── auth.py                  # JWT authentication + role-based access
│   │   ├── routers/                 # API endpoints (days, anomalies, predict, audit)
│   │   ├── services/                # ML service (loads models) + data service
│   │   └── middleware/              # Audit logging
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx                  # React dashboard (all tabs)
│   │   ├── api.js                   # API client (auth, fetch, post)
│   │   └── App.css                  # Styling
│   └── package.json
├── venv/                            # Python virtual environment
└── README.md                        # This file
```

## Dataset

### Training Data — CASAS Aruba

- **Source**: https://zenodo.org/records/15708568 (extracted `aruba.csv` from `data.zip`)
- **Format**: CSV — `date,time,room_name,state`
- **Size**: 1.6M events, 220 days (2010-11-04 to 2011-06-11)
- **Rooms**: Bathroom, Bedroom, Kitchen, LivingRoom (+ others mapped to these 4)
- **Used for training**: 169 days (non-test days)

### Test Data — Llumiguano et al.

- **Source**: https://zenodo.org/records/15800764
- **Paper**: "Unsupervised convolutional neural networks using home presence sensors for behavioural anomaly detection in older adults"
- **Format**: Pre-computed 96-slot features + ground truth labels per room
- **Size**: 128 test days per room with injected synthetic anomalies

### Why Valid Comparison

Same dataset, same test set, same ground truth labels as Llumiguano et al. — direct comparison with no evaluation protocol differences.

## How to Run Locally

### Prerequisites

- Python 3.12
- Node.js (for React frontend)

### 1. Setup

```bash

# Create and setup virtual environment
python3 -m venv venv
./venv/bin/pip install -r ml-pipeline/requirements.txt
./venv/bin/pip install -r backend/requirements.txt
./venv/bin/pip install python-multipart
```

### 2. Download Data

```bash
chmod +x data/download.sh
./data/download.sh
```

### 3. Run ML Pipeline (once)

```bash
cd ml-pipeline
../venv/bin/python -m src.pipeline
```

Produces trained models + evaluation results + SHAP plots in `ml-pipeline/outputs/`.

### 4. Start Backend (Terminal 1)

```bash
cd [backend dir path]
../venv/bin/uvicorn app.main:app --port 8000 --reload
```

API docs: http://localhost:8000/docs

### 5. Start Frontend (Terminal 2)

```bash
cd [frontend dir path]]
npm run dev
```

Dashboard: http://localhost:5173

## How the Application Works

### Architecture

```
React Frontend (localhost:5173)
    ↕ HTTP/JSON
FastAPI Backend (localhost:8000)
    ↕ loads on startup
.joblib Models (ml-pipeline/outputs/)
    ↕ trained by
ML Pipeline (runs once, produces models + results)
    ↕ reads
CASAS Aruba Dataset (data/raw/aruba.csv)
```

### User Roles

| Role | Username | Password | Access |
|------|----------|----------|--------|
| Caregiver | caregiver | care123 | Anomalies, All Days, Simulate, Evaluation |
| Admin | admin | admin123 | Everything above + Audit Log |

Caregivers cannot see the audit log. The backend enforces this — even if someone calls the `/audit` endpoint directly, it returns 403 Forbidden for non-admin users.

### Dashboard Tabs

**Anomalies** — Shows all days where at least one room was flagged as anomalous. Each card shows the date and per-room status badges (green=normal, red=anomaly). Click a day to see SHAP explanations.

**All Days** — Shows all 128 test days (both normal and anomalous). Same click-to-detail functionality.

**Simulate** — Upload a CSV file with raw sensor events (same format as `aruba.csv`). The model runs live inference and returns per-room anomaly status with SHAP explanations. Use `data/sample_day.csv` as a test file.

**Evaluation** — Model performance metrics per room:
- **Precision**: Of all days the model flagged as anomalies, what fraction actually were anomalies? (High precision = few false alarms)
- **Recall**: Of all actual anomaly days, what fraction did the model catch? (High recall = few missed anomalies)
- **F1-Score**: Harmonic mean of Precision and Recall (balanced metric)
- **TP (True Positives)**: Correctly detected anomalies
- **FP (False Positives)**: Normal days incorrectly flagged as anomalies (false alarms)
- **FN (False Negatives)**: Anomaly days the model missed

**Audit Log** (admin only) — Shows every API request: timestamp, user, HTTP method, endpoint path, and status code. Used for accountability and compliance.

### How Simulate Works (Live Inference)

1. You upload a `.csv` file in the React frontend
2. Frontend parses the CSV — extracts `time`, `sensor`, `state` from each line
3. Frontend sends the events as JSON to `POST /predict` on the FastAPI backend
4. Backend (`ml_service.py`) uses the `.joblib` models (loaded once at startup from `ml-pipeline/outputs/model_{ROOM}.joblib`)
5. Backend computes features — counts ON activations per 15-min time slot per room (same 96-slot format used in training)
6. Backend runs the saved StandardScaler — normalizes the features using the mean/std learned during training
7. Backend runs the saved Isolation Forest — `model.predict()` returns normal or anomaly
8. If anomaly: backend runs SHAP — `TreeExplainer` explains which time slots drove the decision
9. Backend returns JSON with per-room status + SHAP explanations
10. Frontend displays the results with red/green badges and SHAP bar charts

The entire process takes ~100-200ms because the models are pre-loaded in memory.

### How SHAP Explanations Work

When a day is flagged as anomalous, SHAP (SHapley Additive exPlanations) tells you *why*:
- Each of the 96 time slots gets a SHAP value indicating how much it contributed to the anomaly decision
- Negative SHAP values push toward "anomaly"
- The top contributing time slots are shown as red bars in the dashboard
- Example: "Kitchen at 02:30 — SHAP: -0.67, raw: 52 activations" means the 02:30-02:45 slot had 52 activations, which was unusual and contributed strongly to flagging this day

## Current Results

| Room | Precision | Recall | F1 | TP | FP | FN |
|------|-----------|--------|------|----|----|-----|
| BATHROOM | 1.000 | 0.456 | 0.627 | 26 | 0 | 31 |
| BEDROOM | 0.825 | 1.000 | 0.904 | 52 | 11 | 0 |
| KITCHEN | 0.915 | 1.000 | 0.955 | 75 | 7 | 0 |
| LIVING_ROOM | 0.961 | 0.778 | 0.860 | 49 | 2 | 14 |

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/login` | None | Get JWT token |
| GET | `/days` | Any | All days with per-room status |
| GET | `/days/{date}` | Any | Single day detail + SHAP |
| GET | `/anomalies` | Any | Only anomalous days |
| GET | `/anomalies/evaluation` | Any | Model metrics |
| POST | `/predict` | Any | Live inference from raw events |
| GET | `/audit` | Admin | Audit log |

## Next Steps

### Database Integration (MongoDB)

Currently the backend reads results from JSON files in `ml-pipeline/outputs/`. The next step is to store them in MongoDB Atlas (free tier):
- Pipeline writes results to MongoDB after training
- Backend reads from MongoDB instead of JSON files
- Audit log persists to MongoDB (currently in-memory, lost on restart)
- Simulated predictions can be saved and reviewed later

### GCP Deployment

| Component | Local | GCP |
|-----------|-------|-----|
| ML Pipeline | `python -m src.pipeline` | Cloud Run Job (scheduled) |
| Backend | `uvicorn app.main:app` | Cloud Run Service |
| Frontend | `npm run dev` | Firebase Hosting |
| Models | `ml-pipeline/outputs/*.joblib` | Cloud Storage |
| Database | JSON files | MongoDB Atlas |

### Other Improvements

- Tuning: adjust `contamination` parameter for Bathroom (currently too conservative)
- Replace placeholder comparison values in `evaluate.py` with actual Llumiguano et al. numbers
- Add privacy controls (mask specific rooms/time ranges)
- Add caregiver feedback loop (mark false positives/negatives)

## Reproducibility

- Fixed random seed: 42
- Python 3.12, Node.js 18+
- All dependencies in `ml-pipeline/requirements.txt` and `backend/requirements.txt`
- Data download script included (`data/download.sh`)
