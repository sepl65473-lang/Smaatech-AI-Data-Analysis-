import pytest
import shutil
import time
from pathlib import Path
import secrets
from fastapi.testclient import TestClient

from app.main import app
from app.session.store import SessionStore
from app.services import auth_store
from app.routers import auth

ADMIN_EMAIL = "superadmin@example.test"
ADMIN_PASSWORD = "Str0ng-SuperAdmin!2026"


@pytest.fixture
def client(monkeypatch):
    test_data = Path(__file__).parent / ".auth-test-admin-data" / secrets.token_hex(8)
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


def test_admin_invitation_lifecycle_and_user_activation(client, monkeypatch):
    # 1. Sign in as Super Admin
    login_res = client.post("/api/auth/login", json={"identity": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert login_res.status_code == 200

    # 2. Mock SMTP to capture sent invitation emails
    sent_invitations = []
    def mock_send_invitation(email, full_name, activation_url, expires_in_hours=48):
        sent_invitations.append({"email": email, "full_name": full_name, "url": activation_url})
        return True
    monkeypatch.setattr(auth, "_send_invitation", mock_send_invitation)

    # 3. Create a new user with full name and unique email (invitation mode - no password upfront)
    create_res = client.post("/api/auth/admin/users", json={
        "full_name": "Rohan Sharma",
        "email": "rohan.sharma@example.test",
        "role": "standard_user",
        "permissions": ["platform:access", "statements:upload", "reports:export"]
    })
    assert create_res.status_code == 201
    user_data = create_res.json()
    assert user_data["email"] == "rohan.sharma@example.test"
    assert user_data["full_name"] == "Rohan Sharma"
    assert user_data["status"] == "pending_activation"
    assert user_data["role"] == "standard_user"
    assert user_data["email_sent"] is True
    assert "token=" in user_data["invitation_url"]
    invitation_url = user_data["invitation_url"]
    raw_token = invitation_url.split("token=")[1]

    # Verify password was never stored or emailed in plaintext
    assert "password" not in create_res.text.lower() or "password_hash" not in user_data
    db = auth_store.read()
    assert db["users"]["rohan.sharma@example.test"]["password_hash"] is None
    assert db["users"]["rohan.sharma@example.test"]["invitation_token_hash"] is not None

    # 4. Duplicate email creation should fail with 409
    dup_res = client.post("/api/auth/admin/users", json={
        "full_name": "Another Person",
        "email": "rohan.sharma@example.test",
        "role": "standard_user"
    })
    assert dup_res.status_code == 409

    # 5. Pending user cannot log in before activating
    client.post("/api/auth/logout")
    pre_login = client.post("/api/auth/login", json={"identity": "rohan.sharma@example.test", "password": "AnyPassword!2026"})
    assert pre_login.status_code == 403
    assert "pending activation" in pre_login.json()["detail"].lower()

    # 6. Verify invitation token endpoint
    verify_res = client.get(f"/api/auth/activate/verify?token={raw_token}")
    assert verify_res.status_code == 200
    assert verify_res.json()["email"] == "rohan.sharma@example.test"
    assert verify_res.json()["full_name"] == "Rohan Sharma"

    # Invalid token check
    assert client.get("/api/auth/activate/verify?token=invalid_token_12345").status_code == 400

    # 7. User activates account and chooses password
    # Password complexity enforcement
    weak_res = client.post("/api/auth/activate", json={"token": raw_token, "password": "weak"})
    assert weak_res.status_code == 422

    act_res = client.post("/api/auth/activate", json={"token": raw_token, "password": "Rohan-Strong-Password!2026"})
    assert act_res.status_code == 200
    assert act_res.json()["ok"] is True

    # 8. Single-use token: token cannot be reused
    act_reuse = client.post("/api/auth/activate", json={"token": raw_token, "password": "Another-Password!2026"})
    assert act_reuse.status_code == 400

    # 9. Activated user can now log in
    login_user = client.post("/api/auth/login", json={"identity": "rohan.sharma@example.test", "password": "Rohan-Strong-Password!2026"})
    assert login_user.status_code == 200
    me = client.get("/api/auth/me").json()
    assert me["user"]["email"] == "rohan.sharma@example.test"
    assert me["user"]["role"] == "standard_user"
    assert "statements:upload" in me["user"]["permissions"]


def test_standard_user_blocked_from_admin_apis_and_privilege_escalation(client):
    # Create standard user directly
    client.post("/api/auth/login", json={"identity": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    res = client.post("/api/auth/admin/users", json={
        "full_name": "Standard Tester",
        "email": "standard@example.test",
        "password": "Standard-User-Pass!2026",
        "role": "standard_user"
    })
    assert res.status_code == 201
    user_id = res.json()["id"]

    # Sign in as standard user
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"identity": "standard@example.test", "password": "Standard-User-Pass!2026"})

    # Standard user CANNOT access admin endpoints
    assert client.get("/api/auth/admin/users").status_code == 403
    assert client.get("/api/auth/admin/audit").status_code == 403
    assert client.post("/api/auth/admin/users", json={"email": "hacked@example.test", "password": "Hacked-Pass!2026"}).status_code == 403
    assert client.patch(f"/api/auth/admin/users/{user_id}", json={"role": "administrator"}).status_code == 403
    assert client.delete(f"/api/auth/admin/users/{user_id}").status_code == 403


def test_admin_user_table_operations_edit_suspend_unlock_and_safe_delete(client):
    # Log in as admin
    client.post("/api/auth/login", json={"identity": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    admin_me = client.get("/api/auth/me").json()["user"]

    # 1. Create standard user
    res = client.post("/api/auth/admin/users", json={
        "full_name": "Jane Doe",
        "email": "jane.doe@example.test",
        "password": "Jane-Doe-Secret!2026",
        "role": "standard_user"
    })
    jane_id = res.json()["id"]

    # 2. List users table
    users_table = client.get("/api/auth/admin/users").json()["users"]
    assert any(u["id"] == jane_id and u["full_name"] == "Jane Doe" for u in users_table)

    # 3. Edit user: update name and permissions
    patch_res = client.patch(f"/api/auth/admin/users/{jane_id}", json={
        "full_name": "Jane Smith",
        "permissions": ["platform:access", "analytics:view"]
    })
    assert patch_res.status_code == 200
    assert patch_res.json()["full_name"] == "Jane Smith"

    # 4. Suspend user
    suspend_res = client.patch(f"/api/auth/admin/users/{jane_id}", json={"status": "suspended"})
    assert suspend_res.status_code == 200
    assert suspend_res.json()["status"] == "suspended"

    # Suspended user cannot log in
    client.post("/api/auth/logout")
    login_attempt = client.post("/api/auth/login", json={"identity": "jane.doe@example.test", "password": "Jane-Doe-Secret!2026"})
    assert login_attempt.status_code == 403
    assert "suspended" in login_attempt.json()["detail"].lower()

    # Re-activate user
    client.post("/api/auth/login", json={"identity": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    reactivate_res = client.patch(f"/api/auth/admin/users/{jane_id}", json={"status": "active"})
    assert reactivate_res.status_code == 200
    assert reactivate_res.json()["status"] == "active"

    # 5. Safe Deletion:
    # Admin cannot delete own account
    self_del = client.delete(f"/api/auth/admin/users/{admin_me['id']}")
    assert self_del.status_code == 400
    assert "cannot delete your own account" in self_del.json()["detail"].lower()

    # Admin cannot suspend or delete the permanent Super Admin / last active administrator
    admin_del = client.patch(f"/api/auth/admin/users/{admin_me['id']}", json={"status": "suspended"})
    assert admin_del.status_code in (403, 409)

    # Delete standard user successfully
    del_res = client.delete(f"/api/auth/admin/users/{jane_id}")
    assert del_res.status_code == 200
    # Jane should no longer be in users list
    updated_users = client.get("/api/auth/admin/users").json()["users"]
    assert not any(u["id"] == jane_id for u in updated_users)


def test_resend_invitation_and_audit_logging(client, monkeypatch):
    client.post("/api/auth/login", json={"identity": ADMIN_EMAIL, "password": ADMIN_PASSWORD})

    # Create pending invitation
    res = client.post("/api/auth/admin/users", json={
        "full_name": "Dev User",
        "email": "dev.user@example.test",
        "role": "standard_user"
    })
    dev_id = res.json()["id"]

    # Resend invitation
    resend_res = client.post(f"/api/auth/admin/users/{dev_id}/resend-invitation")
    assert resend_res.status_code == 200
    assert "token=" in resend_res.json()["invitation_url"]

    # Audit log check
    audit_res = client.get("/api/auth/admin/audit")
    assert audit_res.status_code == 200
    events = [e["event"] for e in audit_res.json()["events"]]
    assert "user_invited" in events
    assert "invitation_resent" in events

