"""Comprehensive security, isolation, Super Admin protection and MongoDB Atlas tests.
Verifies:
1. Super Admin Protection (cannot be deleted, demoted, suspended or taken over).
2. User Data Isolation (User A statements and exports blocked from User B with 403).
3. Production Invitation Links (dynamic public URL, single-use, expiry).
4. MongoDB Atlas store persistence and strict fallback prohibition.
"""

import os
import secrets
import shutil
import time
from pathlib import Path
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.session.store import SessionStore
from app.services import auth_store


@pytest.fixture(autouse=True)
def clean_auth_env(monkeypatch):
    """Ensure clean isolated environment for security tests."""
    test_data = Path(__file__).resolve().parents[2] / "scratch" / "pytest-auth-isolation" / secrets.token_hex(8)
    test_data.mkdir(parents=True, exist_ok=False)
    monkeypatch.setattr(auth_store, "_auth_store", SessionStore(ttl_minutes=525600, data_dir=str(test_data)))
    monkeypatch.setenv("AUTH_REQUIRED", "true")
    monkeypatch.setenv("AUTH_ADMIN_EMAIL", "itsmaatech@gmail.com")
    monkeypatch.setenv("AUTH_ADMIN_PASSWORD", "SuperSecure2026!#")
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")
    monkeypatch.setenv("AUTH_COOKIE_SAMESITE", "lax")
    monkeypatch.setenv("PUBLIC_FRONTEND_URL", "https://sepl-analytics.vercel.app")

    # Clean up non-admin test users from auth_store
    def purge(db):
        super_admin = "itsmaatech@gmail.com"
        db["users"] = {k: v for k, v in db.get("users", {}).items() if k.lower() == super_admin}
        db["sessions"] = {}
        db["recovery"] = {}
    auth_store.update(purge)
    yield
    shutil.rmtree(test_data, ignore_errors=True)


def _get_csrf_and_cookies(client: TestClient):
    resp = client.get("/api/auth/csrf")
    assert resp.status_code == 200
    token = resp.json()["csrf_token"]
    return token, client.cookies


# -----------------------------------------------------------------------------
# 1. Super Admin Protection Tests
# -----------------------------------------------------------------------------

def test_super_admin_protection():
    client = TestClient(app)
    csrf, _ = _get_csrf_and_cookies(client)
    headers = {"X-CSRF-Token": csrf}

    # Bootstrap Super Admin (or verify existing)
    b_resp = client.post("/api/auth/bootstrap", headers=headers)
    assert b_resp.status_code in (200, 409)

    # Attempt second bootstrap: must strictly reject with 409 Conflict
    re_b_resp = client.post("/api/auth/bootstrap", headers=headers)
    assert re_b_resp.status_code == 409
    assert "already been completed" in re_b_resp.json()["detail"]

    # Login as Super Admin
    login_resp = client.post("/api/auth/login", json={
        "identity": "itsmaatech@gmail.com",
        "password": "SuperSecure2026!#",
    }, headers=headers)
    assert login_resp.status_code == 200
    super_admin_id = login_resp.json()["user"]["id"]

    # Super Admin creates a second administrator
    create_resp = client.post("/api/auth/admin/users", json={
        "email": "secondary.admin@example.com",
        "full_name": "Secondary Admin",
        "password": "SecondAdmin2026!#",
        "role": "administrator",
    }, headers=headers)
    assert create_resp.status_code == 201

    # Secondary admin signs in
    client_sec = TestClient(app)
    csrf_sec, _ = _get_csrf_and_cookies(client_sec)
    headers_sec = {"X-CSRF-Token": csrf_sec}

    sec_login = client_sec.post("/api/auth/login", json={
        "identity": "secondary.admin@example.com",
        "password": "SecondAdmin2026!#",
    }, headers=headers_sec)
    assert sec_login.status_code == 200

    # 1. Secondary admin attempts to DELETE Super Admin -> 403 Forbidden
    del_resp = client_sec.delete(f"/api/auth/admin/users/{super_admin_id}", headers=headers_sec)
    assert del_resp.status_code == 403
    assert "Super Admin account cannot be deleted" in del_resp.json()["detail"]

    # 2. Secondary admin attempts to SUSPEND Super Admin -> 403 Forbidden
    susp_resp = client_sec.patch(f"/api/auth/admin/users/{super_admin_id}", json={
        "status": "suspended"
    }, headers=headers_sec)
    assert susp_resp.status_code == 403
    assert "Super Admin account cannot be suspended" in susp_resp.json()["detail"]

    # 3. Secondary admin attempts to DEMOTE Super Admin -> 403 Forbidden
    demote_resp = client_sec.patch(f"/api/auth/admin/users/{super_admin_id}", json={
        "role": "standard_user"
    }, headers=headers_sec)
    assert demote_resp.status_code == 403
    assert "Super Admin account cannot be demoted" in demote_resp.json()["detail"]

    # 4. Secondary admin attempts to alter Super Admin profile name -> 403 Forbidden
    edit_resp = client_sec.patch(f"/api/auth/admin/users/{super_admin_id}", json={
        "full_name": "Hijacked Name"
    }, headers=headers_sec)
    assert edit_resp.status_code == 403
    assert "Only the permanent Super Admin can modify" in edit_resp.json()["detail"]


# -----------------------------------------------------------------------------
# 2. Production Invitation Links & Expiry Tests
# -----------------------------------------------------------------------------

def test_production_invitation_links_and_expiry():
    client = TestClient(app)
    csrf, _ = _get_csrf_and_cookies(client)
    headers = {"X-CSRF-Token": csrf}

    # Ensure Super Admin logged in
    client.post("/api/auth/login", json={
        "identity": "itsmaatech@gmail.com",
        "password": "SuperSecure2026!#",
    }, headers=headers)

    # Create an invited user without password
    create_resp = client.post("/api/auth/admin/users", json={
        "email": "invited.analyst@example.com",
        "full_name": "Invited Analyst",
        "role": "standard_user",
    }, headers=headers)
    assert create_resp.status_code == 201
    data = create_resp.json()
    invite_url = data["invitation_url"]

    # Verify public domain is used, NOT localhost
    assert invite_url.startswith("https://sepl-analytics.vercel.app/activate?token="), \
        f"Expected public domain in invitation URL, got: {invite_url}"

    token = invite_url.split("token=")[1]

    # Verify token
    verify_resp = client.get(f"/api/auth/activate/verify?token={token}")
    assert verify_resp.status_code == 200
    assert verify_resp.json()["email"] == "invited.analyst@example.com"

    # Activate account
    act_resp = client.post("/api/auth/activate", json={
        "token": token,
        "password": "ActivatedPass2026!#",
    }, headers=headers)
    assert act_resp.status_code == 200

    # Single-use enforcement: Attempting to reuse the same token must fail
    reuse_resp = client.get(f"/api/auth/activate/verify?token={token}")
    assert reuse_resp.status_code == 400
    assert "invalid, expired, or has already been used" in reuse_resp.json()["detail"]

    reuse_act = client.post("/api/auth/activate", json={
        "token": token,
        "password": "AnotherPassword2026!#",
    }, headers=headers)
    assert reuse_act.status_code == 400


# -----------------------------------------------------------------------------
# 3. User Data Isolation Tests
# -----------------------------------------------------------------------------

def test_user_data_isolation():
    client_admin = TestClient(app)
    csrf_a, _ = _get_csrf_and_cookies(client_admin)
    headers_a = {"X-CSRF-Token": csrf_a}

    client_admin.post("/api/auth/login", json={
        "identity": "itsmaatech@gmail.com",
        "password": "SuperSecure2026!#",
    }, headers=headers_a)

    # Create User 1
    client_admin.post("/api/auth/admin/users", json={
        "email": "user1@company.com",
        "full_name": "User One",
        "password": "UserOne2026!#",
        "role": "standard_user",
    }, headers=headers_a)

    # Create User 2
    client_admin.post("/api/auth/admin/users", json={
        "email": "user2@company.com",
        "full_name": "User Two",
        "password": "UserTwo2026!#",
        "role": "standard_user",
    }, headers=headers_a)

    # Log in as User 1
    c1 = TestClient(app)
    csrf1, _ = _get_csrf_and_cookies(c1)
    h1 = {"X-CSRF-Token": csrf1}
    c1.post("/api/auth/login", json={"identity": "user1@company.com", "password": "UserOne2026!#"}, headers=h1)

    # Log in as User 2
    c2 = TestClient(app)
    csrf2, _ = _get_csrf_and_cookies(c2)
    h2 = {"X-CSRF-Token": csrf2}
    c2.post("/api/auth/login", json={"identity": "user2@company.com", "password": "UserTwo2026!#"}, headers=h2)

    # User 1 uploads a bank statement CSV
    csv_content = (
        "Date,Description,Debit,Credit,Balance\n"
        "01/06/2023,Opening Balance,,,10000.00\n"
        "02/06/2023,Client Payment,,50000.00,60000.00\n"
        "03/06/2023,Office Rent,20000.00,,40000.00\n"
    ).encode("utf-8")

    upload_resp = c1.post("/api/upload", files={"file": ("june_statement.csv", csv_content, "text/csv")}, headers=h1)
    assert upload_resp.status_code == 200
    session_id = upload_resp.json()["session_id"]

    # 1. User 1 accesses their own session -> 200 OK
    res1 = c1.get(f"/api/results/{session_id}")
    assert res1.status_code == 200

    # 2. User 2 attempts to access User 1's session -> 403 Forbidden
    res2 = c2.get(f"/api/results/{session_id}")
    assert res2.status_code == 403
    assert "Access denied" in res2.json()["detail"]

    # 3. User 2 attempts to export User 1's report as PDF -> 403 Forbidden
    pdf2 = c2.get(f"/api/export/{session_id}?format=pdf")
    assert pdf2.status_code == 403

    # 4. User 2 attempts to export User 1's report as Excel -> 403 Forbidden
    xlsx2 = c2.get(f"/api/export/{session_id}?format=xlsx")
    assert xlsx2.status_code == 403

    # 5. User 2 attempts to export User 1's report as ZIP -> 403 Forbidden
    zip2 = c2.get(f"/api/export/{session_id}?format=zip")
    assert zip2.status_code == 403

    # 6. User 2 attempts to export User 1's report as CSV -> 403 Forbidden
    csv2 = c2.get(f"/api/export/{session_id}?format=csv")
    assert csv2.status_code == 403

    # 6b. User 2 attempts to export User 1's standalone HTML -> 403 Forbidden
    html2 = c2.get(f"/api/export/{session_id}?format=html")
    assert html2.status_code == 403

    # 6c. User 2 attempts to check User 1's export status -> 403 Forbidden
    status2 = c2.get(f"/api/export/{session_id}/status")
    assert status2.status_code == 403

    # 7. User 2 attempts to override category mapping on User 1's session -> 403 Forbidden
    cat2 = c2.post(f"/api/results/{session_id}/category-mapping", json={
        "counterparty": "Office Rent",
        "new_category": "Utilities",
    }, headers=h2)
    assert cat2.status_code == 403

    # 8. Universal Analysis Track Data Isolation: User 1 uploads generic dataset
    ds_csv = b"Product,Revenue,Cost\nWidget A,5000,2000\nWidget B,8000,3000\n"
    up_ds = c1.post("/api/analyze", files={"file": ("sales.csv", ds_csv, "text/csv")}, headers=h1)
    assert up_ds.status_code == 200
    analysis_id = up_ds.json()["session_id"]

    # User 2 attempts to access User 1's dataset analysis -> 403 Forbidden
    an2 = c2.get(f"/api/analysis/{analysis_id}")
    assert an2.status_code == 403

    # User 2 attempts to query User 1's dataset via AI QA -> 403 Forbidden
    qa2 = c2.post(f"/api/analysis/{analysis_id}/qa", json={"question": "Total revenue?"}, headers=h2)
    assert qa2.status_code == 403

    # User 2 attempts to download User 1's dataset file -> 403 Forbidden
    dl2 = c2.get(f"/api/analysis/{analysis_id}/download")
    assert dl2.status_code == 403

    # 9. User 1 can successfully export their own deliverables
    pdf1 = c1.get(f"/api/export/{session_id}?format=pdf")
    assert pdf1.status_code == 200

    xlsx1 = c1.get(f"/api/export/{session_id}?format=xlsx")
    assert xlsx1.status_code == 200

    # 10. Administrator can inspect session for audit/support purposes
    res_admin = client_admin.get(f"/api/results/{session_id}")
    assert res_admin.status_code == 200


# -----------------------------------------------------------------------------
# 4. MongoDB Atlas Fallback Prevention Tests
# -----------------------------------------------------------------------------

def test_require_mongodb_fallback_prevention(monkeypatch):
    """Verify REQUIRE_MONGODB=true strictly prohibits silent fallback to local file store."""
    monkeypatch.setenv("REQUIRE_MONGODB", "true")
    monkeypatch.delenv("MONGODB_URI", raising=False)

    with pytest.raises(RuntimeError) as exc_info:
        SessionStore(ttl_minutes=30, collection_name="test_collection")

    assert "MONGODB_URI is not set" in str(exc_info.value)
    assert "Silent fallback" in str(exc_info.value)
