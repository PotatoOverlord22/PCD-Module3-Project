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
├── .env.example                     # Template for environment variables (committed)
├── backend/
│   ├── .env                         # Real secrets — gitignored, never committed
│   ├── app/
│   │   ├── main.py                  # FastAPI app
│   │   ├── auth.py                  # JWT authentication + role-based access
│   │   ├── config.py                # Environment variable loading (MONGO_URI, etc.)
│   │   ├── routers/                 # API endpoints (days, anomalies, predict, audit)
│   │   ├── services/
│   │   │   ├── data_service.py      # Reads from MongoDB (or local files as fallback)
│   │   │   ├── ml_service.py        # Loads models, live prediction + SHAP explanations
│   │   │   └── mongo_service.py     # MongoDB connection singleton
│   │   └── middleware/              # Audit logging
│   └── requirements.txt
├── frontend/                            # React + TypeScript (Vite, MUI, Zod)
│   ├── src/
│   │   ├── main.tsx                 # Entry point
│   │   ├── components/              # App, Login, DayCard, DayDetail, views...
│   │   ├── layouts/                 # DashboardLayout (AppBar + Tabs + Outlet)
│   │   ├── routes/                  # ProtectedRoute (auth guard)
│   │   ├── api/                     # Typed fetch client + API request functions
│   │   ├── model/                   # Zod schemas per endpoint (auth, day, audit, etc.)
│   │   └── utils/                   # CSV parser with validation
│   └── package.json
├── documents/
│   └── frontend-project-structure.md    # Detailed frontend architecture documentation
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
- Node.js 20+ (for React + TypeScript frontend)

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

### 3. Configure MongoDB (Optional)

The app works fully without MongoDB — it falls back to reading local JSON/CSV files from `ml-pipeline/outputs/`. To enable MongoDB Atlas for persistent cloud-ready storage:

```bash
# Copy the template to both backend and ml-pipeline
cp .env.example backend/.env
cp .env.example ml-pipeline/.env

# Edit both .env files with your MongoDB Atlas connection string:
# MONGO_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority
# MONGO_DB_NAME=pcd-module3-project
```

**How to get the connection string:**
1. Go to [cloud.mongodb.com](https://cloud.mongodb.com) → Create a free M0 cluster
2. Database Access → Create a user with read/write permissions
3. Network Access → Add your IP (or `0.0.0.0/0` for development)
4. Database → Connect → Drivers → Python → Copy the connection string

The `.env` files are gitignored — secrets are never committed. On cloud platforms (GCP Cloud Run, AWS ECS), inject `MONGO_URI` and `MONGO_DB_NAME` as environment variables directly.

### 4. Run ML Pipeline (once)

```bash
cd ml-pipeline
../venv/bin/python -m src.pipeline
```

Produces trained models + evaluation results + SHAP plots + human-readable explanations in `ml-pipeline/outputs/`. If MongoDB is configured, also writes all results to MongoDB Atlas (idempotent — safe to re-run).

### 5. Start Backend (Terminal 1)

```bash
cd backend
../venv/bin/uvicorn app.main:app --port 8000 --reload
```

Reads from MongoDB if `MONGO_URI` is set in `backend/.env`, otherwise falls back to local files.

API docs: http://localhost:8000/docs

### 6. Start Frontend (Terminal 2)

```bash
cd frontend
npm install
npm run dev
```

Dashboard: http://localhost:5173

## How the Application Works

### Architecture

```
React Frontend (localhost:5173)
    ↕ HTTP/JSON
FastAPI Backend (localhost:8000)
    ↕ reads from                  ↕ loads on startup
MongoDB Atlas (optional)     .joblib Models (ml-pipeline/outputs/)
    ↑ writes to                   ↑ trained by
    └──── ML Pipeline (runs once, produces models + results) ────┘
              ↕ reads
    CASAS Aruba Dataset (data/raw/aruba.csv)
```

When MongoDB is configured, the pipeline writes results (anomaly days + human-readable explanations + evaluation metrics) to MongoDB, and the backend reads from it. Without MongoDB, the backend falls back to local JSON/CSV files — no functionality is lost.

### User Roles

| Role | Username | Password | Access |
|------|----------|----------|--------|
| Caregiver | caregiver | care123 | Anomalies, All Days, Simulate |
| Admin | admin | admin123 | Everything above + Evaluation, Audit Log |

Caregivers cannot see the Evaluation tab or the Audit Log. The backend enforces role checks on the `/audit` endpoint — even if someone calls it directly, it returns 403 Forbidden for non-admin users.

### Dashboard Tabs

**Anomalies** — Shows all days where at least one room was flagged as anomalous. Each card shows the date and per-room status badges (green=normal, red=anomaly). Click a day to see SHAP explanations.

**All Days** — Shows all 128 test days (both normal and anomalous). Same click-to-detail functionality.

**Simulate** — Upload a CSV file with raw sensor events (same format as `aruba.csv`). The model runs live inference and returns per-room anomaly status with SHAP explanations. Use `data/sample_day.csv` as a test file.

**Evaluation** (admin only) — Model performance metrics per room:
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

## What's Done

### MongoDB Atlas Integration

The pipeline and backend now support MongoDB Atlas (free M0 tier) as an optional persistent data store:
- **Pipeline** writes anomaly days (with human-readable SHAP explanations) + evaluation metrics to MongoDB after each run
- **Backend** reads from MongoDB when `MONGO_URI` is configured, falls back to local JSON/CSV files otherwise
- **Idempotent writes** — running the pipeline multiple times replaces existing data, never duplicates
- **Environment-based config** — connection string loaded from `.env` files locally, injected as env vars on cloud platforms
- **Live predictions** (`/predict`) generate human-readable explanations on-the-fly using SHAP + training means from the saved scaler

### Human-Readable Explanations

Anomalies now include plain-text explanations with:
- Time-of-day context (morning/afternoon/evening/night)
- Magnitude qualifiers (slightly/moderately/significantly) calibrated from actual SHAP distributions
- Concrete sensor counts vs training baselines (e.g. "12 sensor events vs typical 2")
- Summary sentences synthesizing the overall pattern

### Privacy-by-Design (Role-Based Data Redaction)

Sensor activity in sensitive rooms (default: `BATHROOM`) is filtered **server-side** from API responses sent to users with the `caregiver` role. Administrators with explicit clinical authorization still see the full data.

- **Defense beyond UI hiding** — the response payload itself does not contain the redacted room data, so caregivers cannot bypass the restriction via DevTools or direct API calls (`curl /days`, `/anomalies`, `/predict` all redacted)
- **Transparent to the user** — the response includes a `redacted_rooms: ["BATHROOM"]` field, so the dashboard renders a `🔒 private` placeholder where data would have been
- **Configurable** — change the redacted set via env var `PRIVATE_ROOMS_FOR_CAREGIVER=BATHROOM,BEDROOM` (comma-separated, empty string disables)
- **Audit trail** — the existing audit log records every request including who attempted to access what, so administrative overrides are accountable

Endpoints affected: `GET /days`, `GET /days/{date}`, `GET /anomalies`, `POST /predict`. `GET /anomalies/evaluation` returns aggregate metrics only (no per-day per-room activity) and is admin-only on the dashboard anyway.

## Cloud Deployment (Live)

The application is deployed to Microsoft Azure and is reachable in a browser without any local setup:

| Component | URL / Service |
|---|---|
| **Frontend (live demo)** | https://gentle-hill-0493bc203.7.azurestaticapps.net |
| **Backend API** | https://caregiver-backend.ambitioussky-65844e0a.westeurope.azurecontainerapps.io |
| **Interactive API docs** | https://caregiver-backend.ambitioussky-65844e0a.westeurope.azurecontainerapps.io/docs |
| **Frontend hosting** | Azure Static Web Apps (Free tier, GitHub Actions CI/CD) |
| **Backend hosting** | Azure Container Apps (Consumption plan, Docker from Azure Container Registry Basic) |
| **Database** | MongoDB Atlas M0 (Frankfurt) |
| **Region** | West Europe |

### How to test the deployed app (no install required)

1. Open the **Frontend URL** above
2. Login with one of:
   - **Caregiver** — `caregiver / care123` → sees Anomalies, All Days, Simulate (bathroom data redacted)
   - **Admin** — `admin / admin123` → sees all 5 tabs + full bathroom data
3. Try the tabs:
   - **Anomalies / All Days** — click any card → SHAP explanation
   - **Simulate** — upload `data/sample_day.csv` from the repo → live ML inference
   - **Evaluation** (admin) — model metrics
   - **Audit Log** (admin) — request history
4. Privacy demo: login as caregiver, open any day → `🔒 bathroom · private` chip + info banner. Login as admin → bathroom appears with green/red status.

Full deployment guide and `az` CLI commands are in [`DEPLOY.md`](./DEPLOY.md).

## Next Steps

### GCP Deployment

| Component | Local | GCP |
|-----------|-------|-----|
| ML Pipeline | `python -m src.pipeline` | Cloud Run Job (scheduled) |
| Backend | `uvicorn app.main:app` | Cloud Run Service |
| Frontend | `npm run dev` | Firebase Hosting |
| Models | `ml-pipeline/outputs/*.joblib` | Cloud Storage |
| Database | MongoDB Atlas (already integrated) | MongoDB Atlas (same cluster) |

Environment variables (`MONGO_URI`, `MONGO_DB_NAME`) can be injected via GCP Cloud Run's `--set-env-vars` or Secret Manager.

### Other Improvements

- Tuning: adjust `contamination` parameter for Bathroom (currently too conservative — perfect precision but only 0.456 recall)
- Persist audit log to MongoDB (currently in-memory, lost on restart)
- Save simulated predictions to MongoDB for later review
- Replace placeholder comparison values in `evaluate.py` with actual Llumiguano et al. numbers
- Add caregiver feedback loop (mark false positives/negatives)
- Extend privacy controls to time-range masking (currently only per-room redaction is implemented)

## Reproducibility

- Fixed random seed: 42
- Python 3.12, Node.js 20+
- All dependencies in `ml-pipeline/requirements.txt` and `backend/requirements.txt`
- Data download script included (`data/download.sh`)
