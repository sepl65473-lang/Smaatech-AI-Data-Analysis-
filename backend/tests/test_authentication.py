import pytest
import shutil
from pathlib import Path
import secrets
from fastapi.testclient import TestClient

from app.main import app
from app.session.store import SessionStore
from app.services import auth_store
from app.routers import auth

ADMIN_EMAIL = "admin@example.test"
ADMIN_PASSWORD = "Str0ng-Admin-Pass!2026"


@pytest.fixture
def client(monkeypatch):
    test_data = Path(__file__).parent / ".auth-test-data" / secrets.token_hex(8)
    test_data.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(auth_store, "_auth_store", SessionStore(ttl_minutes=525600, data_dir=str(test_data)))
    monkeypatch.setenv("AUTH_ADMIN_EMAIL", ADMIN_EMAIL)
    monkeypatch.setenv("AUTH_ADMIN_PASSWORD", ADMIN_PASSWORD)
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")
    monkeypatch.setenv("AUTH_REQUIRED", "true")
    monkeypatch.setattr(auth, "COOKIE_SECURE", False)
    with TestClient(app) as test_client:
        csrf = test_client.get("/api/auth/csrf")
        assert csrf.status_code == 200
        test_client.headers.update({"X-CSRF-Token": test_client.cookies.get("sepl_csrf")})
        assert test_client.post("/api/auth/bootstrap").status_code == 200
        yield test_client
    shutil.rmtree(test_data, ignore_errors=True)


def test_password_hash_login_logout_and_protected_api(client):
    assert client.get("/api/results/not-a-session").status_code == 401
    response = client.post("/api/auth/login", json={"identity": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "remember": True})
    assert response.status_code == 200
    assert client.get("/api/auth/me").status_code == 200
    assert client.get("/api/results/not-a-session").status_code == 404
    assert client.get("/api/results/not-a-session").status_code == 404
    assert "password" not in response.text.lower()
    assert client.get("/api/auth/me").json()["user"]["role"] == "administrator"
    sessions = client.get("/api/auth/sessions").json()["sessions"]
    assert len(sessions) == 1 and sessions[0]["current"]
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/auth/me").status_code == 401


def test_three_failed_attempts_trigger_persistent_lockout(client):
    for _ in range(2):
        response = client.post("/api/auth/login", json={"identity": ADMIN_EMAIL, "password": "incorrect"})
        assert response.status_code == 401
    response = client.post("/api/auth/login", json={"identity": ADMIN_EMAIL, "password": "incorrect"})
    assert response.status_code == 423
    response = client.post("/api/auth/login", json={"identity": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert response.status_code == 423
    data = auth_store.read()
    user = data["users"][ADMIN_EMAIL]
    assert user["locked_until"] > 0


def test_csrf_and_password_policy_are_enforced(client):
    assert client.post("/api/auth/login", json={"identity": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, headers={"X-CSRF-Token": "bad"}).status_code == 403
    response = client.post("/api/auth/login", json={"identity": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert response.status_code == 200
    response = client.post("/api/auth/change-password", json={"current_password": ADMIN_PASSWORD, "new_password": "short"})
    assert response.status_code == 422


def test_session_revoke_and_password_change(client):
    client.post("/api/auth/login", json={"identity": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    first = client.get("/api/auth/sessions").json()["sessions"][0]
    client.post("/api/auth/login", json={"identity": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert len(client.get("/api/auth/sessions").json()["sessions"]) == 2
    assert client.delete(f"/api/auth/sessions/{first['id']}").status_code == 204
    assert len(client.get("/api/auth/sessions").json()["sessions"]) == 1
    response = client.post("/api/auth/change-password", json={"current_password": ADMIN_PASSWORD, "new_password": "Another-Admin-Password!2026"})
    assert response.status_code == 200
    assert client.get("/api/auth/me").status_code == 200
    assert len(client.get("/api/auth/sessions").json()["sessions"]) == 1
    assert client.post("/api/auth/login", json={"identity": ADMIN_EMAIL, "password": ADMIN_PASSWORD}).status_code == 401
    assert client.post("/api/auth/login", json={"identity": ADMIN_EMAIL, "password": "Another-Admin-Password!2026"}).status_code == 200


def test_auth_accounts_sessions_and_audit_survive_store_restart(client, monkeypatch):
    assert client.post("/api/auth/login", json={"identity": ADMIN_EMAIL, "password": ADMIN_PASSWORD}).status_code == 200
    before = auth_store._auth_store
    data_dir = before._data_dir
    monkeypatch.setattr(auth_store, "_auth_store", SessionStore(ttl_minutes=525600, data_dir=data_dir))
    assert client.get("/api/auth/me").status_code == 200
    assert len(client.get("/api/auth/sessions").json()["sessions"]) == 1
    events = client.get("/api/auth/admin/audit").json()["events"]
    assert any(event["event"] == "login_success" for event in events)


def test_admin_user_rbac_and_audit(client):
    client.post("/api/auth/login", json={"identity": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    response = client.post("/api/auth/admin/users", json={"email": "analyst@example.test", "password": "Str0ng-Analyst-Pass!2026", "role": "standard_user"})
    assert response.status_code == 201
    account = response.json()
    assert "password" not in response.text and "password_hash" not in response.text
    assert client.get("/api/auth/admin/users").status_code == 200
    assert client.get("/api/auth/admin/audit").status_code == 200
    assert client.patch(f"/api/auth/admin/users/{account['id']}", json={"status": "suspended"}).json()["status"] == "suspended"
    assert client.get("/api/auth/admin/users").status_code == 200
    assert client.patch(f"/api/auth/admin/users/{account['id']}", json={"status": "active"}).json()["status"] == "active"
    client.post("/api/auth/logout")
    assert client.post("/api/auth/login", json={"identity": "analyst@example.test", "password": "Str0ng-Analyst-Pass!2026"}).status_code == 200
    assert client.get("/api/auth/admin/users").status_code == 403
    assert client.patch(f"/api/auth/admin/users/{account['id']}", json={"role": "administrator"}).status_code == 403
    client.post("/api/auth/logout")
    assert client.post("/api/auth/login", json={"identity": ADMIN_EMAIL, "password": ADMIN_PASSWORD}).status_code == 200
    reset = client.post(f"/api/auth/admin/users/{account['id']}/reset-password", json={"new_password": "Reset-Analyst-Pass!2026"})
    assert reset.status_code == 200 and reset.json()["sessions_revoked"]
    assert client.post("/api/auth/logout").status_code == 200
    assert client.post("/api/auth/login", json={"identity": "analyst@example.test", "password": "Str0ng-Analyst-Pass!2026"}).status_code == 401
    assert client.post("/api/auth/login", json={"identity": "analyst@example.test", "password": "Reset-Analyst-Pass!2026"}).status_code == 200


def test_otp_recovery_uses_single_use_reset_authorization(client, monkeypatch):
    client.post("/api/auth/logout")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.test")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "noreply@example.test")
    monkeypatch.setattr(auth, "_send_otp", lambda email, otp: setattr(auth, "_test_otp", otp) or True)
    response = client.post("/api/auth/recovery/request", json={"email": ADMIN_EMAIL})
    assert response.status_code == 200
    assert "otp" not in response.text.lower()
    otp = auth._test_otp
    verified = client.post("/api/auth/recovery/verify", json={"email": ADMIN_EMAIL, "otp": otp})
    assert verified.status_code == 200
    token = verified.json()["reset_token"]
    body = {"reset_token": token, "new_password": "New-Admin-Pass!2026"}
    assert client.post("/api/auth/recovery/reset", json=body).status_code == 200
    assert client.post("/api/auth/recovery/reset", json=body).status_code == 400
    assert client.post("/api/auth/login", json={"identity": ADMIN_EMAIL, "password": "New-Admin-Pass!2026"}).status_code == 200


def test_recovery_delivery_failure_does_not_confirm_account_existence(client, monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.test")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "noreply@example.test")
    def fail_delivery(email, otp): raise OSError("SMTP offline")
    monkeypatch.setattr(auth, "_send_otp", fail_delivery)
    known = client.post("/api/auth/recovery/request", json={"email": ADMIN_EMAIL})
    unknown = client.post("/api/auth/recovery/request", json={"email": "missing@example.test"})
    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()
