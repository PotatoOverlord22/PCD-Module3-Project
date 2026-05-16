"""Centralized configuration loaded from environment variables.

Locally, values are read from ``backend/.env`` via python-dotenv.
On cloud platforms (GCP Cloud Run, AWS ECS, etc.), the same variable
names are injected as real environment variables — no .env file needed.
"""

import os
from dotenv import load_dotenv

# load_dotenv() is a no-op when no .env file exists, so this is safe
# to call unconditionally in any environment.
load_dotenv()

# MongoDB Atlas connection string.
# When None the application falls back to reading local JSON/CSV files,
# so the app still works without a database configured.
MONGO_URI: str | None = os.getenv("MONGO_URI")

# MongoDB database name — override via env var if needed.
MONGO_DB_NAME: str = os.getenv("MONGO_DB_NAME", "pcd-module3-project")

# Privacy: rooms whose data is redacted from API responses sent to users
# with the "caregiver" role. Admins always see the full data. Default
# hides BATHROOM activity (intimate space) — change via env var, e.g.
#   PRIVATE_ROOMS_FOR_CAREGIVER=BATHROOM,BEDROOM
# Empty string disables redaction entirely.
PRIVATE_ROOMS_FOR_CAREGIVER: list[str] = [
    r.strip().upper()
    for r in os.getenv("PRIVATE_ROOMS_FOR_CAREGIVER", "BATHROOM").split(",")
    if r.strip()
]
