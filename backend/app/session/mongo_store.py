"""MongoDB Atlas session and application store adapter.

Persists analysis sessions and authentication records to MongoDB Atlas
with TTL expiration, atomic updates, and connection pooling.
"""
from __future__ import annotations

import copy
import logging
import os
import time
import uuid
from typing import Any, Callable, Optional

log = logging.getLogger(__name__)


def check_mongo_connection(uri: str | None = None, db_name: str | None = None) -> dict[str, Any]:
    """Test connection to MongoDB Atlas and return status."""
    uri = uri or os.getenv("MONGODB_URI", "").strip()
    db_name = db_name or os.getenv("MONGODB_DB_NAME", "ai_data_analysis").strip()
    if not uri:
        return {"configured": False, "connected": False, "detail": "MONGODB_URI not configured"}
    try:
        import pymongo
        client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=4000)
        client.admin.command("ping")
        return {"configured": True, "connected": True, "database": db_name, "detail": "Connected to MongoDB Atlas"}
    except Exception as exc:
        return {"configured": True, "connected": False, "database": db_name, "detail": str(exc)}


class MongoSessionStore:
    """SessionStore adapter for MongoDB Atlas."""

    def __init__(
        self,
        ttl_minutes: int = 60,
        collection_name: str = "sessions",
        uri: str | None = None,
        db_name: str | None = None,
        client: Any | None = None,
    ):
        self._ttl_seconds = ttl_minutes * 60
        self._collection_name = collection_name
        self._uri = uri or os.getenv("MONGODB_URI", "").strip()
        self._db_name = db_name or os.getenv("MONGODB_DB_NAME", "ai_data_analysis").strip()
        self._client = client
        self._db = None
        self._collection = None
        self._indexes_created = False

    def _get_collection(self):
        if self._collection is not None:
            return self._collection
        if self._client is None:
            import pymongo
            self._client = pymongo.MongoClient(
                self._uri,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=10000,
                retryWrites=True,
            )
        self._db = self._client[self._db_name]
        self._collection = self._db[self._collection_name]
        if not self._indexes_created:
            try:
                # TTL index for automatic expiry
                self._collection.create_index("expires_at", expireAfterSeconds=0, background=True)
                self._collection.create_index("updated_at", background=True)
                self._indexes_created = True
            except Exception as exc:
                log.warning("Index creation on %s failed: %s", self._collection_name, exc)
        return self._collection

    def _serialize(self, data: Any) -> Any:
        if hasattr(data, "model_dump"):
            return data.model_dump(mode="json")
        return copy.deepcopy(data)

    def create(self) -> str:
        session_id = str(uuid.uuid4())
        col = self._get_collection()
        now = time.time()
        expires_at = now + self._ttl_seconds
        col.insert_one({
            "_id": session_id,
            "data": None,
            "expires_at": expires_at,
            "created_at": now,
            "updated_at": now,
        })
        return session_id

    def set(self, session_id: str, data: Any) -> None:
        col = self._get_collection()
        now = time.time()
        expires_at = now + self._ttl_seconds
        serialized = self._serialize(data)
        col.update_one(
            {"_id": session_id},
            {"$set": {
                "data": serialized,
                "expires_at": expires_at,
                "updated_at": now,
            }},
            upsert=True,
        )

    def ensure(self, session_id: str, data: Any) -> None:
        """Create a record once without overwriting an existing document."""
        col = self._get_collection()
        now = time.time()
        expires_at = now + self._ttl_seconds
        serialized = self._serialize(data)
        col.update_one(
            {"_id": session_id},
            {"$setOnInsert": {
                "data": serialized,
                "expires_at": expires_at,
                "created_at": now,
                "updated_at": now,
            }},
            upsert=True,
        )

    def update(self, session_id: str, updater: Callable[[dict], Any]) -> tuple[dict, Any]:
        """Atomically read the document, mutate it, and persist it."""
        col = self._get_collection()
        doc = col.find_one({"_id": session_id})
        now = time.time()
        if doc is None:
            raise KeyError(session_id)
        if doc.get("expires_at") and now > float(doc.get("expires_at")):
            col.delete_one({"_id": session_id})
            raise KeyError(session_id)

        data = doc.get("data")
        if data is None:
            data = {}
        result = updater(data)
        serialized = self._serialize(data)
        expires_at = now + self._ttl_seconds
        col.update_one(
            {"_id": session_id},
            {"$set": {
                "data": serialized,
                "expires_at": expires_at,
                "updated_at": now,
            }},
        )
        return copy.deepcopy(data), result

    def get(self, session_id: str) -> Optional[Any]:
        col = self._get_collection()
        doc = col.find_one({"_id": session_id})
        if doc is None:
            return None
        now = time.time()
        if doc.get("expires_at") and now > float(doc.get("expires_at")):
            col.delete_one({"_id": session_id})
            return None
        return copy.deepcopy(doc.get("data"))

    def exists(self, session_id: str) -> bool:
        col = self._get_collection()
        doc = col.find_one({"_id": session_id})
        if doc is None:
            return False
        now = time.time()
        if doc.get("expires_at") and now > float(doc.get("expires_at")):
            col.delete_one({"_id": session_id})
            return False
        return True

    def delete(self, session_id: str) -> None:
        col = self._get_collection()
        col.delete_one({"_id": session_id})
