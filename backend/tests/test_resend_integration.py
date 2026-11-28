import asyncio
import time
import httpx
import os
import json
import secrets
import shutil
import io
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.session.store import SessionStore
from app.services import auth_store
from app.routers import auth

ADMIN_EMAIL = "admin@example.test"
ADMIN_PASSWORD = "Str0ng-Admin-Pass!2026"
NEW_PASSWORD = "BrandNew-Strong-Pass!2026"

class MockHTTPResponse:
    def __init__(self, status=200, data=None):
        self.status = status
        self.data = json.dumps(data or {"id": "re_mock_12345678"}).encode("utf-8")

    def read(self, *args, **kwargs):
        return self.data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


@pytest.fixture
def auth_env(monkeypatch):
    test_data = Path(__file__).parent / ".resend-test-data" / secrets.token_hex(8)
    test_data.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(auth_store, "_auth_store", SessionStore(ttl_minutes=525600, data_dir=str(test_data)))
    monkeypatch.setenv("AUTH_ADMIN_EMAIL", ADMIN_EMAIL)
    monkeypatch.setenv("AUTH_ADMIN_PASSWORD", ADMIN_PASSWORD)
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")
    monkeypatch.setenv("AUTH_REQUIRED", "true")
    monkeypatch.setenv("RESEND_API_KEY", "re_test_dummy_key_123456")
    monkeypatch.setenv("RESEND_FROM_EMAIL", "onboarding@resend.dev")
    monkeypatch.setenv("RESEND_FROM_NAME", "SEPL Security")
    monkeypatch.setattr(auth, "COOKIE_SECURE", False)

    with TestClient(app) as test_client:
        csrf = test_client.get("/api/auth/csrf")
        assert csrf.status_code == 200
        test_client.headers.update({"X-CSRF-Token": test_client.cookies.get("sepl_csrf")})
        assert test_client.post("/api/auth/bootstrap").status_code == 200
        yield test_client

    shutil.rmtree(test_data, ignore_errors=True)


# TEST 1: Successful email delivery through Resend HTTPS API
def test_resend_delivery_success(auth_env):
    with patch("urllib.request.urlopen", return_value=MockHTTPResponse(200, {"id": "re_success_abc"})) as mock_open:
        res = auth_env.post("/api/auth/recovery/request", json={"email": ADMIN_EMAIL})
        assert res.status_code == 200
        assert mock_open.called
        req = mock_open.call_args[0][0]
        assert req.full_url == "https://api.resend.com/emails"
        assert req.headers["Authorization"] == "Bearer re_test_dummy_key_123456"
        assert "Idempotency-key" in req.headers
        body = json.loads(req.data.decode("utf-8"))
        assert body["to"] == [ADMIN_EMAIL]
        assert "SEPL account recovery" in body["subject"]


# TEST 2: Invalid or missing API key
def test_resend_missing_or_invalid_api_key(auth_env, monkeypatch):
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.delenv("SMTP_HOST", raising=False)
    res = auth_env.post("/api/auth/recovery/request", json={"email": ADMIN_EMAIL})
    assert res.status_code == 503
    assert "temporarily unavailable" in res.json()["detail"].lower()


# TEST 3: Unverified sender / domain rejection (HTTP 422 from provider)
def test_resend_unverified_domain_error(auth_env):
    error = urllib.error.HTTPError(
        url="https://api.resend.com/emails",
        code=422,
        msg="Unprocessable Entity",
        hdrs={},
        fp=io.BytesIO(b'{"statusCode":422,"message":"Domain not verified"}')
    )
    with patch("urllib.request.urlopen", side_effect=error):
        res = auth_env.post("/api/auth/recovery/request", json={"email": ADMIN_EMAIL})
        assert res.status_code == 200
        db = auth_store.read()
        assert ADMIN_EMAIL not in db.get("recovery", {})
        recent_audit = [a["event"] for a in db.get("audit", [])]
        assert "recovery_delivery_failed" in recent_audit


# TEST 4: Provider timeout (TimeoutError)
def test_resend_provider_timeout(auth_env):
    with patch("urllib.request.urlopen", side_effect=TimeoutError("Request timed out")):
        res = auth_env.post("/api/auth/recovery/request", json={"email": ADMIN_EMAIL})
        assert res.status_code == 200
        db = auth_store.read()
        assert ADMIN_EMAIL not in db.get("recovery", {})


# TEST 5: Provider HTTP 500 error
def test_resend_provider_http_500(auth_env):
    error = urllib.error.HTTPError(
        url="https://api.resend.com/emails",
        code=500,
        msg="Internal Server Error",
        hdrs={},
        fp=io.BytesIO(b'{"message":"Internal Server Error"}')
    )
    with patch("urllib.request.urlopen", side_effect=error):
        res = auth_env.post("/api/auth/recovery/request", json={"email": ADMIN_EMAIL})
        assert res.status_code == 200
        db = auth_store.read()
        assert ADMIN_EMAIL not in db.get("recovery", {})


# TEST 6: Duplicate request and idempotency behaviour
def test_resend_idempotency_and_throttling(auth_env):
    with patch("urllib.request.urlopen", return_value=MockHTTPResponse(200, {"id": "re_idem_1"})) as mock_open:
        res1 = auth_env.post("/api/auth/recovery/request", json={"email": ADMIN_EMAIL})
        assert res1.status_code == 200
        req1 = mock_open.call_args[0][0]
        idem_key1 = req1.headers.get("Idempotency-key")
        assert idem_key1 is not None

        # Immediate second request within 60s cooldown must NOT dispatch duplicate email
        mock_open.reset_mock()
        res2 = auth_env.post("/api/auth/recovery/request", json={"email": ADMIN_EMAIL})
        assert res2.status_code == 200
        assert not mock_open.called


# TESTS 7–10: End-to-end recovery lifecycle (Verify OTP, reset password, login new, reject old, revoke sessions)
def test_full_recovery_and_session_invalidation(auth_env):
    captured_otps = []
    dispatched_subjects = []
    def fake_send(to_email, subject, text, html, idempotency_key=None):
        import re
        dispatched_subjects.append((to_email, subject))
        match = re.search(r"\b\d{6}\b", text)
        if match:
            captured_otps.append(match.group(0))
        return True

    with patch("app.routers.auth._send_email", side_effect=fake_send):
        # 0. Initial authenticated session
        login_orig = auth_env.post("/api/auth/login", json={"identity": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "remember": True})
        assert login_orig.status_code == 200
        orig_session = auth_env.cookies.get("sepl_session")
        assert orig_session is not None

        # 1. Request recovery
        res = auth_env.post("/api/auth/recovery/request", json={"email": ADMIN_EMAIL})
        assert res.status_code == 200
        assert len(captured_otps) == 1
        otp = captured_otps[0]

        # 2. Replay protection (Test 7)
        verify_res = auth_env.post("/api/auth/recovery/verify", json={"email": ADMIN_EMAIL, "otp": otp})
        assert verify_res.status_code == 200
        reset_token = verify_res.json()["reset_token"]

        replay_res = auth_env.post("/api/auth/recovery/verify", json={"email": ADMIN_EMAIL, "otp": otp})
        assert replay_res.status_code == 400

        # 3. Reset password (Test 8)
        reset_res = auth_env.post("/api/auth/recovery/reset", json={"email": ADMIN_EMAIL, "reset_token": reset_token, "new_password": NEW_PASSWORD})
        assert reset_res.status_code == 200
        assert (ADMIN_EMAIL, "Your SEPL password was changed") in dispatched_subjects

        # 4. Login with new password (Test 8)
        auth_env.headers["X-CSRF-Token"] = auth_env.cookies.get("sepl_csrf")
        login_new = auth_env.post("/api/auth/login", json={"identity": ADMIN_EMAIL, "password": NEW_PASSWORD, "remember": False})
        assert login_new.status_code == 200

        # 5. Old password rejected (Test 9)
        login_old = auth_env.post("/api/auth/login", json={"identity": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "remember": False})
        assert login_old.status_code == 401

        # 6. Session invalidation (Test 10)
        stale_client = TestClient(app)
        stale_client.cookies.set("sepl_session", orig_session)
        assert stale_client.get("/api/auth/me").status_code == 401


# TEST 11: Malformed JSON, missing ID, and unexpected HTTP status from Resend
@pytest.mark.parametrize(
    "status_code,raw_payload",
    [
        (200, b"{}"),
        (200, b'{"id": ""}'),
        (200, b'{"id": "   "}'),
        (200, b'{"id": null}'),
        (200, b"[]"),
        (200, b"not-valid-json"),
        (202, b'{"id": "re_202"}'),
        (204, b""),
    ],
)
def test_resend_rejects_incomplete_or_malformed_responses(auth_env, status_code, raw_payload):
    class CustomHTTPResponse:
        def __init__(self, status, data):
            self.status = status
            self._data = data
        def read(self, *args, **kwargs):
            return self._data
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    with patch("urllib.request.urlopen", return_value=CustomHTTPResponse(status_code, raw_payload)):
        res = auth_env.post("/api/auth/recovery/request", json={"email": ADMIN_EMAIL})
        assert res.status_code == 200
        db = auth_store.read()
        assert ADMIN_EMAIL not in db.get("recovery", {})
        recent_audit = [a["event"] for a in db.get("audit", [])]
        assert "recovery_delivery_failed" in recent_audit


# TEST 12: Explicit sender validation (never silently fall back to unverified Gmail SMTP sender)
def test_resend_never_falls_back_to_smtp_from_email(auth_env, monkeypatch):
    monkeypatch.delenv("RESEND_FROM_EMAIL", raising=False)
    monkeypatch.setenv("SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "sepl65473@gmail.com")
    with patch("urllib.request.urlopen") as mock_open:
        res = auth_env.post("/api/auth/recovery/request", json={"email": ADMIN_EMAIL})
        assert res.status_code == 503
        assert not mock_open.called
        assert auth._send_email_resend("u@example.com", "Sub", "Txt", "<p>H</p>") is False


# TEST 13: Email workflows (invitations, resend invitation, password change & reset notifications)
def test_email_workflows_use_resend_https(auth_env):
    login = auth_env.post("/api/auth/login", json={"identity": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert login.status_code == 200
    auth_env.headers["X-CSRF-Token"] = auth_env.cookies.get("sepl_csrf")

    dispatched_subjects = []

    def fake_urlopen(req, timeout=10, context=None):
        body = json.loads(req.data.decode("utf-8"))
        dispatched_subjects.append((body["to"][0], body["subject"]))
        return MockHTTPResponse(200, {"id": f"re_wf_{len(dispatched_subjects)}"})

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        # 1. Admin creates invited user -> invitation email
        create_res = auth_env.post(
            "/api/auth/admin/users",
            json={
                "email": "invitee@example.test",
                "full_name": "Invitee User",
                "role": "standard_user",
                "permissions": ["platform:access"],
            },
        )
        assert create_res.status_code == 201
        assert create_res.json()["email_sent"] is True
        invitee_id = create_res.json()["id"]

        # 2. Admin resends invitation -> invitation email
        resend_res = auth_env.post(f"/api/auth/admin/users/{invitee_id}/resend-invitation")
        assert resend_res.status_code == 200
        assert resend_res.json()["email_sent"] is True

        # 3. Admin changes own password -> password change notification
        chg_res = auth_env.post(
            "/api/auth/change-password",
            json={"current_password": ADMIN_PASSWORD, "new_password": NEW_PASSWORD},
        )
        assert chg_res.status_code == 200

        # 4. Admin resets another user's password -> password notice
        act_res = auth_env.post(
            "/api/auth/admin/users",
            json={
                "email": "direct@example.test",
                "full_name": "Direct User",
                "role": "standard_user",
                "permissions": ["platform:access"],
                "password": ADMIN_PASSWORD,
            },
        )
        assert act_res.status_code == 201
        direct_id = act_res.json()["id"]
        rst_res = auth_env.post(
            f"/api/auth/admin/users/{direct_id}/reset-password",
            json={"new_password": NEW_PASSWORD},
        )
        assert rst_res.status_code == 200

    assert ("invitee@example.test", "Welcome to SEPL — Activate Your Account") in dispatched_subjects
    assert dispatched_subjects.count(("invitee@example.test", "Welcome to SEPL — Activate Your Account")) == 2
    assert (ADMIN_EMAIL, "Your SEPL password was changed") in dispatched_subjects
    assert ("direct@example.test", "Your SEPL password was changed") in dispatched_subjects


# TEST 14: Event loop remains responsive during delayed email-provider response
def test_async_event_loop_non_blocking_during_slow_provider(auth_env):
    def slow_send(to_email, subject, text, html, idempotency_key=None):
        time.sleep(0.6)
        return True

    async def run_concurrent():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as ac:
            csrf_res = await ac.get("/api/auth/csrf")
            assert csrf_res.status_code == 200
            csrf_token = csrf_res.cookies.get("sepl_csrf")

            with patch("app.routers.auth._send_email", side_effect=slow_send):
                recovery_task = asyncio.create_task(
                    ac.post(
                        "/api/auth/recovery/request",
                        json={"email": ADMIN_EMAIL},
                        headers={"X-CSRF-Token": csrf_token},
                    )
                )
                await asyncio.sleep(0.05)
                t0 = time.perf_counter()
                ping_res = await ac.get("/api/auth/csrf")
                ping_elapsed = time.perf_counter() - t0
                assert ping_res.status_code == 200
                assert ping_elapsed < 0.25, f"Event loop blocked for {ping_elapsed:.3f}s"

                rec_res = await recovery_task
                assert rec_res.status_code == 200

    asyncio.run(run_concurrent())
