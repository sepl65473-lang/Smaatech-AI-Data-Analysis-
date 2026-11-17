import io
import json
import time
import pytest

from app.main import app, health_check
from app.session.store import session_store, FileSessionStore
from app.routers.upload import _validate_file_signature
from fastapi import HTTPException

def test_file_signature_validation():
    # PDF check
    with pytest.raises(HTTPException) as exc:
        _validate_file_signature(b"NOT_A_REAL_PDF", "pdf")
    assert exc.value.status_code == 415

    # Valid PDF
    _validate_file_signature(b"%PDF-1.4 sample content", "pdf")

    # CSV check for null bytes
    with pytest.raises(HTTPException) as exc:
        _validate_file_signature(b"col1,col2\x00malicious", "csv")
    assert exc.value.status_code == 415

    # Valid CSV
    _validate_file_signature(b"Date,Amount,Description\n2025-01-01,100,Sample", "csv")


def test_file_session_store_retention_prune(tmp_path):
    store = FileSessionStore(ttl_minutes=1, data_dir=str(tmp_path))
    s1 = store.create()
    store.set(s1, {"test": "data"})
    
    # Artificially expire s1
    path = store._file_path(s1)
    with open(path, "w", encoding="utf-8") as f:
        f.write('{"session_id": "' + s1 + '", "data": {}, "expires_at": ' + str(time.time() - 10) + '}')
    
    deleted = store.prune_expired()
    assert deleted == 1
    assert not (tmp_path / f"{s1}.json").exists()


def test_health_check_endpoint():
    res = health_check()
    assert res.status_code == 200
    data = json.loads(res.body.decode("utf-8"))
    assert data["status"] == "ok"
    assert "database" in data

