from concurrent.futures import ThreadPoolExecutor
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

from app.session.store import SessionStore


@pytest.fixture
def workspace_data_dir():
    directory = Path(__file__).parent / f".session-test-{uuid.uuid4().hex}"
    directory.mkdir()
    yield str(directory)
    for child in directory.iterdir():
        child.unlink()
    directory.rmdir()


def test_restart_recovery_preserves_mapping_and_audit(workspace_data_dir):
    sid = str(uuid.uuid4())
    first = SessionStore(data_dir=workspace_data_dir)
    first.set(sid, {"transactions": [{"category": "Rent", "classification_source": "user"}], "audit_trail": [{"action": "category_remap"}]})
    second = SessionStore(data_dir=workspace_data_dir)
    data = second.get(sid)
    assert data["transactions"][0]["category"] == "Rent"
    assert data["transactions"][0]["classification_source"] == "user"
    assert data["audit_trail"] == [{"action": "category_remap"}]
    first.delete(sid)


def test_concurrent_updates_are_serialized_across_store_instances(workspace_data_dir):
    sid = str(uuid.uuid4())
    stores = [SessionStore(data_dir=workspace_data_dir) for _ in range(4)]
    stores[0].set(sid, {"count": 0})

    def increment(i):
        def update(data):
            data["count"] += 1
            return data["count"]
        stores[i % len(stores)].update(sid, update)

    with ThreadPoolExecutor(max_workers=12) as pool:
        list(pool.map(increment, range(240)))
    assert SessionStore(data_dir=workspace_data_dir).get(sid)["count"] == 240
    stores[0].delete(sid)


def test_concurrent_updates_are_serialized_across_processes(workspace_data_dir):
    sid = str(uuid.uuid4())
    SessionStore(data_dir=workspace_data_dir).set(sid, {"count": 0})
    worker = (
        "import sys; from app.session.store import SessionStore; "
        "store=SessionStore(data_dir=sys.argv[1]); sid=sys.argv[2]; "
        "n=int(sys.argv[3]); "
        "[store.update(sid, lambda d: d.update(count=d['count']+1)) for _ in range(n)]"
    )
    processes = [subprocess.Popen([sys.executable, "-c", worker, workspace_data_dir, sid, "40"],
                                  cwd=os.path.dirname(os.path.dirname(__file__))) for _ in range(3)]
    for process in processes:
        assert process.wait(timeout=60) == 0
    assert SessionStore(data_dir=workspace_data_dir).get(sid)["count"] == 120
    SessionStore(data_dir=workspace_data_dir).delete(sid)


def test_interrupted_complete_temp_file_is_recovered(workspace_data_dir):
    sid = str(uuid.uuid4())
    store = SessionStore(data_dir=workspace_data_dir)
    temp_path = os.path.join(workspace_data_dir, f"{sid}.json.interrupted.tmp")
    with open(temp_path, "w", encoding="utf-8") as stream:
        json.dump({"session_id": sid, "expires_at": 4_000_000_000, "data": {"audit_trail": ["recovered"]}}, stream)
    recovered = SessionStore(data_dir=workspace_data_dir).get(sid)
    assert recovered == {"audit_trail": ["recovered"]}
    assert os.path.isfile(os.path.join(workspace_data_dir, f"{sid}.json"))
    store.delete(sid)


def test_write_errors_are_not_suppressed(workspace_data_dir, monkeypatch):
    sid = str(uuid.uuid4())
    store = SessionStore(data_dir=workspace_data_dir)

    def fail(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(store, "_atomic_write", fail)
    with pytest.raises(OSError, match="disk full"):
        store.set(sid, {"value": 1})
