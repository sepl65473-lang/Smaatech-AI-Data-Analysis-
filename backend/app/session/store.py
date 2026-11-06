"""Session storage adapter supporting both MongoDB Atlas and atomic local files.

When MONGODB_URI is configured, sessions and application metadata are persisted
in MongoDB Atlas. Otherwise, atomic file storage with thread and process locks
is used for zero-dependency local development.
"""
from __future__ import annotations

import glob
import copy
import json
import os
import tempfile
import threading
import time
import uuid
from contextlib import contextmanager
from typing import Any, Callable, Optional

from app.config import settings

DATA_DIR = os.environ.get("SESSION_DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))
os.makedirs(DATA_DIR, exist_ok=True)

_guard = threading.Lock()
_thread_locks: dict[str, threading.RLock] = {}


def _thread_lock(session_id: str) -> threading.RLock:
    with _guard:
        return _thread_locks.setdefault(session_id, threading.RLock())


def check_database_health() -> dict[str, Any]:
    """Report storage health (MongoDB Atlas or persistent filesystem)."""
    mongo_uri = os.getenv("MONGODB_URI", "").strip()
    require_mongo = os.getenv("REQUIRE_MONGODB", "").strip().lower() in ("true", "1", "yes") or (
        os.getenv("ENV", "").strip().lower() == "production"
        and os.getenv("REQUIRE_MONGODB", "true").strip().lower() not in ("false", "0", "no")
    )
    if mongo_uri:
        from app.session.mongo_store import check_mongo_connection
        res = check_mongo_connection()
        res["type"] = "mongodb"
        return res
    if require_mongo:
        return {
            "configured": False,
            "connected": False,
            "type": "mongodb",
            "detail": "MONGODB_URI is required in production environment but not configured.",
        }
    return {
        "configured": True,
        "type": "filesystem",
        "data_dir": os.path.abspath(DATA_DIR),
        "connected": os.path.exists(DATA_DIR) and os.access(DATA_DIR, os.W_OK),
        "detail": "Using local persistent filesystem storage",
    }


class FileSessionStore:
    """Persist sessions with atomic replace and cross-process per-session locks."""

    def __init__(self, ttl_minutes: int = settings.SESSION_TTL_MINUTES, data_dir: str | None = None):
        self._store: dict[str, dict] = {}
        self._ttl_seconds = ttl_minutes * 60
        self._data_dir = data_dir or DATA_DIR
        os.makedirs(self._data_dir, exist_ok=True)

    def _file_path(self, session_id: str) -> str:
        return os.path.join(self._data_dir, f"{session_id}.json")

    @contextmanager
    def _locked(self, session_id: str):
        lock = _thread_lock(self._file_path(session_id))
        with lock:
            lock_path = self._file_path(session_id) + ".lock"
            os.makedirs(os.path.dirname(lock_path), exist_ok=True)
            with open(lock_path, "a+b") as lock_file:
                if os.name == "nt":
                    import msvcrt
                    lock_file.seek(0, os.SEEK_END)
                    if lock_file.tell() == 0:
                        lock_file.write(b"\0")
                        lock_file.flush()
                    while True:
                        try:
                            lock_file.seek(0)
                            msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                            break
                        except OSError:
                            time.sleep(0.01)
                    try:
                        yield
                    finally:
                        lock_file.seek(0)
                        msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                    try:
                        yield
                    finally:
                        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def _serialize(self, session_id: str, data: Any, expires_at: float) -> dict:
        serialized = data.model_dump(mode="json") if hasattr(data, "model_dump") else data
        return {"session_id": session_id, "data": serialized, "expires_at": expires_at}

    def _atomic_write(self, session_id: str, payload: dict) -> None:
        path = self._file_path(session_id)
        fd, tmp_path = tempfile.mkstemp(prefix=f"{session_id}.json.", suffix=".tmp", dir=self._data_dir)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(payload, stream, default=str, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp_path, path)
            if os.name != "nt":
                dir_fd = os.open(self._data_dir, os.O_RDONLY)
                try:
                    os.fsync(dir_fd)
                finally:
                    os.close(dir_fd)
        except Exception:
            try:
                os.close(fd)
            except OSError:
                pass
            raise

    def _read_disk(self, session_id: str) -> Optional[dict]:
        path = self._file_path(session_id)
        try:
            with open(path, "r", encoding="utf-8") as stream:
                return json.load(stream)
        except FileNotFoundError:
            pass
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

        candidates = sorted(glob.glob(path + ".*.tmp"), key=os.path.getmtime, reverse=True)
        candidates += [path + ".tmp"]
        for candidate in candidates:
            try:
                with open(candidate, "r", encoding="utf-8") as stream:
                    payload = json.load(stream)
                if payload.get("session_id") != session_id or "data" not in payload or "expires_at" not in payload:
                    continue
                os.replace(candidate, path)
                return payload
            except (OSError, json.JSONDecodeError, UnicodeDecodeError, TypeError):
                continue
        if os.path.exists(path):
            raise ValueError(f"Session file is corrupt and no valid interrupted-write recovery exists: {path}")
        return None

    def create(self) -> str:
        session_id = str(uuid.uuid4())
        self._store[session_id] = {"data": None, "expires_at": time.time() + self._ttl_seconds}
        return session_id

    def set(self, session_id: str, data: Any) -> None:
        expires_at = time.time() + self._ttl_seconds
        payload = self._serialize(session_id, data, expires_at)
        with self._locked(session_id):
            self._atomic_write(session_id, payload)
            self._store[session_id] = {"data": payload["data"], "expires_at": expires_at}

    def ensure(self, session_id: str, data: Any) -> None:
        """Create a record once under its process lock without overwriting a concurrent initializer."""
        with self._locked(session_id):
            payload = self._read_disk(session_id)
            if payload is not None and time.time() <= float(payload.get("expires_at", 0)):
                self._store[session_id] = {"data": payload.get("data"), "expires_at": payload["expires_at"]}
                return
            expires_at = time.time() + self._ttl_seconds
            new_payload = self._serialize(session_id, data, expires_at)
            self._atomic_write(session_id, new_payload)
            self._store[session_id] = {"data": new_payload["data"], "expires_at": expires_at}

    def update(self, session_id: str, updater: Callable[[dict], Any]) -> tuple[dict, Any]:
        """Atomically read the newest document, mutate it, and persist it."""
        with self._locked(session_id):
            payload = self._read_disk(session_id)
            entry = self._store.get(session_id)
            if payload is not None:
                if time.time() > float(payload.get("expires_at", 0)):
                    raise KeyError(session_id)
                data = payload.get("data")
            elif entry is not None and time.time() <= entry["expires_at"]:
                data = entry["data"]
            else:
                raise KeyError(session_id)
            result = updater(data)
            expires_at = time.time() + self._ttl_seconds
            new_payload = self._serialize(session_id, data, expires_at)
            self._atomic_write(session_id, new_payload)
            self._store[session_id] = {"data": new_payload["data"], "expires_at": expires_at}
            return copy.deepcopy(new_payload["data"]), result

    def get(self, session_id: str) -> Optional[Any]:
        with self._locked(session_id):
            payload = self._read_disk(session_id)
            if payload is not None:
                if time.time() > float(payload.get("expires_at", 0)):
                    os.remove(self._file_path(session_id))
                    self._store.pop(session_id, None)
                    return None
                data = payload.get("data")
                self._store[session_id] = {"data": data, "expires_at": payload["expires_at"]}
                return copy.deepcopy(data)
            entry = self._store.get(session_id)
            if entry is not None and time.time() <= entry["expires_at"]:
                return copy.deepcopy(entry["data"])
            self._store.pop(session_id, None)
            return None

    def exists(self, session_id: str) -> bool:
        return self.get(session_id) is not None

    def delete(self, session_id: str) -> None:
        with self._locked(session_id):
            self._store.pop(session_id, None)
            path = self._file_path(session_id)
            if os.path.exists(path):
                os.remove(path)
            for candidate in glob.glob(path + ".*.tmp") + [path + ".tmp"]:
                try:
                    os.remove(candidate)
                except FileNotFoundError:
                    pass

    def _evict_expired(self) -> None:
        now = time.time()
        for sid in [key for key, value in self._store.items() if now > value["expires_at"]]:
            self._store.pop(sid, None)

    def prune_expired(self) -> int:
        """Evict both in-memory and on-disk expired session files and stale locks."""
        self._evict_expired()
        count = 0
        now = time.time()
        for path in glob.glob(os.path.join(self._data_dir, "*.json")):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                if now > float(payload.get("expires_at", 0)):
                    os.remove(path)
                    lock_path = path + ".lock"
                    if os.path.exists(lock_path):
                        try:
                            os.remove(lock_path)
                        except OSError:
                            pass
                    count += 1
            except Exception:
                continue
        return count

    @property
    def active_count(self) -> int:
        self._evict_expired()
        return len(self._store)


class SessionStore:
    """Factory that instantiates MongoSessionStore when MONGODB_URI is provided, or FileSessionStore otherwise."""

    def __new__(
        cls,
        ttl_minutes: int = settings.SESSION_TTL_MINUTES,
        data_dir: str | None = None,
        collection_name: str = "sessions",
    ):
        mongo_uri = os.getenv("MONGODB_URI", "").strip()
        require_mongo = os.getenv("REQUIRE_MONGODB", "").strip().lower() in ("true", "1", "yes") or (
            os.getenv("ENV", "").strip().lower() == "production"
            and os.getenv("REQUIRE_MONGODB", "true").strip().lower() not in ("false", "0", "no")
        )
        if mongo_uri:
            from app.session.mongo_store import MongoSessionStore
            return MongoSessionStore(
                ttl_minutes=ttl_minutes,
                collection_name=collection_name,
                uri=mongo_uri,
            )
        if require_mongo:
            raise RuntimeError(
                "Production requires MongoDB Atlas persistent storage, but MONGODB_URI is not set. "
                "Silent fallback to ephemeral local filesystem storage is disabled."
            )
        return FileSessionStore(ttl_minutes=ttl_minutes, data_dir=data_dir)


session_store = SessionStore()
