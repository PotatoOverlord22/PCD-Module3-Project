"""MongoDB connection singleton.

Provides a thin wrapper around pymongo so the rest of the backend can
call ``get_db()`` without worrying about connection management.

If ``MONGO_URI`` is not configured (None), every accessor returns None
so callers can fall back to local-file behaviour.
"""

from pymongo import MongoClient
from pymongo.database import Database
from app.config import MONGO_URI, MONGO_DB_NAME

# Module-level singletons — created once on first import.
_client: MongoClient | None = None
_db: Database | None = None

if MONGO_URI:
    _client = MongoClient(MONGO_URI)
    _db = _client[MONGO_DB_NAME]
    print(f"[mongo] Connected to MongoDB Atlas — database: {MONGO_DB_NAME}")
else:
    print("[mongo] MONGO_URI not set — running in local-file fallback mode")


def get_db() -> Database | None:
    """Return the pymongo Database handle, or None when MongoDB is not configured."""
    return _db


def get_client() -> MongoClient | None:
    """Return the raw MongoClient, or None when MongoDB is not configured."""
    return _client
