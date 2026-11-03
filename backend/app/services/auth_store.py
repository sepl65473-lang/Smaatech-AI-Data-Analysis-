"""Persistent authentication records using the project's locked atomic JSON store."""
from __future__ import annotations

import os
import secrets
from typing import Any

from app.session.store import SessionStore

_auth_dir = os.getenv("AUTH_DATA_DIR", os.getenv("SESSION_DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "session", "data")))
_auth_store = SessionStore(ttl_minutes=10 * 365 * 24 * 60, data_dir=os.path.abspath(_auth_dir))
_database_id = "00000000-0000-0000-0000-000000000001"


def _empty() -> dict[str, Any]:
    return {"users": {}, "sessions": {}, "audit": [], "recovery": {}, "ip_failures": {}}


def read() -> dict[str, Any]:
    value = _auth_store.get(_database_id)
    return value if isinstance(value, dict) else _empty()


def update(fn):
    # Avoid a separate exists()/set() race that could overwrite a concurrent bootstrap.
    _auth_store.ensure(_database_id, _empty())
    return _auth_store.update(_database_id, fn)


def audit(db: dict[str, Any], event: str, actor: str | None, subject: str | None, **details):
    db.setdefault("audit", []).append({"id": secrets.token_hex(12), "event": event, "actor": actor, "subject": subject, **details})
    db["audit"] = db["audit"][-5000:]
