"""Centralized configuration loaded from environment variables.

Locally, values are read from ``ml-pipeline/.env`` via python-dotenv.
On cloud platforms (GCP Cloud Run, Vertex AI, etc.), the same variable
names are injected as real environment variables — no .env file needed.
"""

import os
from dotenv import load_dotenv

# load_dotenv() is a no-op when no .env file exists, so this is safe
# to call unconditionally in any environment.
load_dotenv()

# MongoDB Atlas connection string.
# When None the pipeline skips writing to MongoDB and only saves local files.
MONGO_URI: str | None = os.getenv("MONGO_URI")

# MongoDB database name — override via env var if needed.
MONGO_DB_NAME: str = os.getenv("MONGO_DB_NAME", "pcd-module3-project")
