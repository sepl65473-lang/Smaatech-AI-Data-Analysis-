import copy
import os
import time
from datetime import datetime, timezone, timedelta
import mongomock
import pytest
from starlette.testclient import TestClient

from app.session.mongo_store import MongoSessionStore, check_mongo_connection
from app.session.store import SessionStore, check_database_health, FileSessionStore
from app.main import app

client = TestClient(app)


def test_mongo_session_store_crud_lifecycle():
    mock_client = mongomock.MongoClient()
    store = MongoSessionStore(
        ttl_minutes=60,
        collection_name="test_sessions",
        db_name="test_db",
        client=mock_client,
    )

    # 1. Create
    session_id = store.create()
    assert session_id is not None
    assert len(session_id) == 36

    # 2. Get before set
    data = store.get(session_id)
    assert data is None

    # 3. Set
    payload = {"account": "12345", "balance": 1500.50, "transactions": [{"id": "t1", "amount": 100.0}]}
    store.set(session_id, payload)
    retrieved = store.get(session_id)
    assert retrieved == payload
    assert store.exists(session_id) is True
    assert store.active_count == 1

    # 4. Ensure
    store.ensure(session_id, {"account": "ignored"})
    assert store.get(session_id) == payload  # did not overwrite

    new_sid = "brand-new-sid"
    store.ensure(new_sid, {"initialized": True})
    assert store.get(new_sid) == {"initialized": True}

    # 5. Update
    def add_tx(doc):
        doc["transactions"].append({"id": "t2", "amount": 50.0})
        return "tx_added"

    updated_doc, result = store.update(session_id, add_tx)
    assert result == "tx_added"
    assert len(updated_doc["transactions"]) == 2
    assert store.get(session_id)["transactions"][1]["id"] == "t2"

    # 6. Delete
    store.delete(session_id)
    assert store.get(session_id) is None
    assert store.exists(session_id) is False


def test_mongo_session_store_expiry_and_prune():
    mock_client = mongomock.MongoClient()
    store = MongoSessionStore(
        ttl_minutes=1,
        collection_name="test_expiry",
        db_name="test_db",
        client=mock_client,
    )

    s1 = store.create()
    store.set(s1, {"status": "expired_soon"})

    # Artificially age the session to past
    col = store._get_collection()
    past_dt = datetime.now(timezone.utc) - timedelta(minutes=5)
    col.update_one({"_id": s1}, {"$set": {"expires_at": past_dt}})

    # Should be detected as expired and return None on get/exists
    assert store.get(s1) is None
    assert store.exists(s1) is False

    # Insert another expired session directly
    s2 = "legacy_expired"
    col.insert_one({
        "_id": s2,
        "data": {"type": "legacy"},
        "expires_at": time.time() - 100,
    })

    deleted_count = store.prune_expired()
    assert deleted_count >= 1
    assert col.find_one({"_id": s2}) is None


def test_require_mongodb_prevents_silent_fallback(monkeypatch):
    monkeypatch.setenv("REQUIRE_MONGODB", "true")
    monkeypatch.delenv("MONGODB_URI", raising=False)
    monkeypatch.delenv("ENV", raising=False)

    with pytest.raises(RuntimeError) as exc_info:
        SessionStore(ttl_minutes=10)
    assert "silent fallback to ephemeral local filesystem storage is disabled" in str(exc_info.value).lower()

    # check_database_health() should report unconfigured and unconnected
    health = check_database_health()
    assert health["configured"] is False
    assert health["connected"] is False
    assert health["type"] == "mongodb"


def test_local_dev_fallback_without_require_mongo(monkeypatch, tmp_path):
    monkeypatch.delenv("REQUIRE_MONGODB", raising=False)
    monkeypatch.delenv("MONGODB_URI", raising=False)
    monkeypatch.setenv("ENV", "development")

    store = SessionStore(ttl_minutes=10, data_dir=str(tmp_path))
    assert isinstance(store, FileSessionStore)


def test_health_endpoint_reports_degraded_when_mongodb_required_but_missing(monkeypatch):
    monkeypatch.setenv("REQUIRE_MONGODB", "true")
    monkeypatch.delenv("MONGODB_URI", raising=False)

    res = client.get("/health")
    assert res.status_code == 503
    payload = res.json()
    assert payload["status"] == "degraded"
    assert payload["database"]["connected"] is False
