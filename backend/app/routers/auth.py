"""Cookie-based login, account bootstrap, lockout, sessions and OTP recovery."""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
import secrets
import smtplib
import ssl
import time
import urllib.error
import urllib.request
from email.message import EmailMessage
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.services import auth_store

router = APIRouter(prefix="/auth", tags=["authentication"])
log = logging.getLogger(__name__)
LOCK_SECONDS = int(os.getenv("AUTH_LOCK_MINUTES", "15")) * 60
IDLE_SECONDS = int(os.getenv("AUTH_IDLE_MINUTES", "30")) * 60
ABSOLUTE_SECONDS = int(os.getenv("AUTH_SESSION_HOURS", "12")) * 3600
REMEMBER_SECONDS = int(os.getenv("AUTH_REMEMBER_DAYS", "14")) * 86400
INVITATION_TTL_HOURS = int(os.getenv("AUTH_INVITATION_HOURS", "48"))
INVITATION_TTL_SECONDS = INVITATION_TTL_HOURS * 3600
_is_prod = os.getenv("ENV", "production").lower() in {"production", "prod"}
COOKIE_SECURE = os.getenv("AUTH_COOKIE_SECURE", "true" if _is_prod else "false").lower() in {"1", "true", "yes"}
COOKIE_SAMESITE = os.getenv("AUTH_COOKIE_SAMESITE", "lax").lower()
if COOKIE_SAMESITE not in {"lax", "strict", "none"}: COOKIE_SAMESITE = "lax"
SESSION_COOKIE = "sepl_session"
CSRF_COOKIE = "sepl_csrf"


def _get_client_ip(request: Request) -> str:
    """Extract client IP through reverse proxies (Render, Cloudflare, Vercel)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
        if client_ip:
            return client_ip
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "unknown"


class LoginBody(BaseModel):
    identity: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)
    remember: bool = False


class ChangePasswordBody(BaseModel):
    current_password: str
    new_password: str


class RecoveryRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)


class OTPVerify(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    otp: str = Field(min_length=6, max_length=6)


class PasswordReset(BaseModel):
    reset_token: str
    new_password: str


class AccountCreate(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    full_name: Optional[str] = Field(default=None, max_length=120)
    password: Optional[str] = Field(default=None, min_length=12, max_length=128)
    role: str = Field(default="standard_user", pattern="^(administrator|standard_user)$")
    permissions: Optional[list[str]] = None


class AccountUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, max_length=120)
    status: Optional[str] = Field(default=None, pattern="^(active|inactive|suspended|disabled|pending|pending_activation)$")
    role: Optional[str] = Field(default=None, pattern="^(administrator|standard_user)$")
    permissions: Optional[list[str]] = None


class AccountActivate(BaseModel):
    token: str = Field(min_length=16, max_length=128)
    password: str = Field(min_length=12, max_length=128)


class AdministratorPasswordReset(BaseModel):
    new_password: str = Field(min_length=12, max_length=128)


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    derived = hashlib.scrypt(password.encode(), salt=salt, n=2**15, r=8, p=1, dklen=32, maxmem=64 * 1024 * 1024)
    return f"scrypt$32768$8$1${salt.hex()}${derived.hex()}"


def _verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, n, r, p, salt, expected = encoded.split("$")
        if scheme != "scrypt": return False
        actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p), dklen=32, maxmem=64 * 1024 * 1024)
        return hmac.compare_digest(actual.hex(), expected)
    except (ValueError, TypeError):
        return False


def _validate_password(password: str):
    if len(password) < 12 or len(password) > 128:
        raise HTTPException(422, "Password must be between 12 and 128 characters.")
    if not (any(c.islower() for c in password) and any(c.isupper() for c in password) and any(c.isdigit() for c in password) and any(not c.isalnum() for c in password)):
        raise HTTPException(422, "Use uppercase, lowercase, number and symbol characters in your password.")
    if password.casefold() in {"password123!", "password1234!", "admin123456!", "qwerty123456!", "welcome12345!"}:
        raise HTTPException(422, "Choose a less common password.")


def _cookie(response: Response, name: str, value: str, *, max_age: int | None, httponly: bool):
    response.set_cookie(name, value, max_age=max_age, httponly=httponly, secure=COOKIE_SECURE, samesite=COOKIE_SAMESITE, path="/")


def _csrf_ok(request: Request):
    cookie = request.cookies.get(CSRF_COOKIE, "")
    header = request.headers.get("x-csrf-token", "")
    if not cookie or not hmac.compare_digest(cookie, header):
        log.warning("CSRF check failed: cookie_present=%s header_present=%s values_match=%s", bool(cookie), bool(header), bool(cookie and header and hmac.compare_digest(cookie, header)))
        raise HTTPException(403, "Refresh the page and try again.")
    origin = request.headers.get("origin")
    allowed = {
        os.getenv("FRONTEND_ORIGIN", "http://localhost:5173"),
        os.getenv("PUBLIC_FRONTEND_URL", ""),
        os.getenv("FRONTEND_URL", ""),
        os.getenv("APP_URL", ""),
        *filter(None, os.getenv("EXTRA_CORS_ORIGINS", "").split(",")),
    }
    if origin:
        clean_origin = origin.rstrip("/")
        allowed_set = {x.strip().rstrip("/") for x in allowed if x}
        is_loopback = clean_origin.startswith("http://localhost:") or clean_origin.startswith("http://127.0.0.1:") or clean_origin in ("http://localhost", "http://127.0.0.1")
        if clean_origin not in allowed_set and not is_loopback:
            log.warning("CSRF origin rejected: origin=%s", origin)
            raise HTTPException(403, "Request origin is not allowed.")


def _current(request: Request, *, touch=True):
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        if os.getenv("AUTH_REQUIRED", "true").lower() in {"0", "false", "no"}:
            return {"id": "local-admin", "email": "admin@example.com", "role": "administrator", "permissions": ["platform:access", "users:manage", "audit:read", "sessions:revoke"]}
        return None
    token_key = hashlib.sha256(token.encode()).hexdigest()
    now = time.time()
    result = None
    def change(db):
        nonlocal result
        session = db.setdefault("sessions", {}).get(token_key)
        if not session or session["expires_at"] <= now or session["last_seen"] + session.get("idle_timeout", IDLE_SECONDS) <= now:
            db.get("sessions", {}).pop(token_key, None)
            return
        user = next((item for item in db.get("users", {}).values() if item.get("id") == session["user_id"]), None)
        if not user or user.get("status") != "active" or session.get("absolute_expiry", 0) <= now:
            db["sessions"].pop(token_key, None)
            return
        if touch: session["last_seen"] = now
        result = {"id": user["id"], "email": user["email"], "full_name": user.get("full_name") or user["email"].split("@")[0].replace(".", " ").title(), "role": user["role"], "permissions": user.get("permissions", [])}
    auth_store.update(change)
    return result


def require_csrf_for_mutation(request: Request):
    _csrf_ok(request)


@router.get("/csrf")
async def csrf(response: Response):
    value = secrets.token_urlsafe(32)
    _cookie(response, CSRF_COOKIE, value, max_age=3600, httponly=False)
    return {"ok": True, "csrf_token": value}


@router.post("/bootstrap")
async def bootstrap(request: Request):
    """One-time admin creation, enabled only when both bootstrap env vars exist."""
    _csrf_ok(request)
    email = os.getenv("AUTH_ADMIN_EMAIL", "").strip().lower()
    password = os.getenv("AUTH_ADMIN_PASSWORD", "")
    if not email or not password:
        raise HTTPException(404, "Bootstrap is unavailable.")
    _validate_password(password)
    encoded = _hash_password(password)
    created = False
    def change(db):
        nonlocal created
        if db.get("users"): return
        user_id = secrets.token_hex(16)
        db["users"][email] = {"id": user_id, "email": email, "password_hash": encoded, "password_history": [], "role": "administrator", "permissions": ["platform:access", "users:manage", "audit:read", "sessions:revoke"], "status": "active", "failed_attempts": 0, "locked_until": 0, "created_at": time.time()}
        auth_store.audit(db, "admin_bootstrap", user_id, user_id)
        created = True
    auth_store.update(change)
    if not created: raise HTTPException(409, "Bootstrap has already been completed.")
    return {"created": True, "message": "Administrator created. Remove bootstrap credentials from the environment now."}


@router.post("/login")
async def login(body: LoginBody, request: Request, response: Response):
    _csrf_ok(request)
    identity = body.identity.strip().lower()
    now = time.time()
    ip = _get_client_ip(request)
    outcome = {"error": None, "session": None, "user": None, "max_age": None, "retry": None}
    # Persist account and source-IP attempt counters under one OS lock.
    def change(db):
        user = next((u for u in db.setdefault("users", {}).values() if u["email"].lower() == identity), None)
        ip_rec = db.setdefault("ip_failures", {}).get(ip, {"count": 0, "window": now})
        if now - ip_rec.get("window", now) > 900: ip_rec = {"count": 0, "window": now}
        if ip_rec["count"] >= 30:
            outcome["error"] = (429, "Too many sign-in attempts. Try again later."); return

        # Check account status before evaluating password
        if user and user.get("status") == "pending_activation":
            outcome["error"] = (403, "Your account is pending activation. Please use the activation link sent to your email to set your password.")
            return

        if user and user.get("status") in {"suspended", "inactive", "disabled"}:
            outcome["error"] = (403, "Your account has been suspended or deactivated. Contact your administrator.")
            return

        # Enforce account lockout before checking or clearing password
        if user and user.get("locked_until", 0) > now:
            remaining = max(1, int(user["locked_until"] - now))
            outcome["error"] = (423, f"Your account is temporarily locked. Try again in {remaining} seconds.")
            return

        clean_pass = body.password.strip()
        stored_hash = user["password_hash"] if user and user.get("password_hash") else "scrypt$32768$8$1$" + ("00" * 16) + "$" + ("00" * 32)
        valid = _verify_password(body.password, stored_hash) or _verify_password(clean_pass, stored_hash)

        # Environment admin password bootstrap fallback (only if password not yet rotated)
        env_admin_pass = os.getenv("AUTH_ADMIN_PASSWORD", "").strip()
        env_admin_email = os.getenv("AUTH_ADMIN_EMAIL", "").strip().lower()
        if not valid and env_admin_pass and env_admin_email:
            if identity == env_admin_email and hmac.compare_digest(clean_pass, env_admin_pass):
                if user and user.get("role") == "administrator" and not user.get("password_history"):
                    valid = True
                    user["password_hash"] = _hash_password(env_admin_pass)
                elif not user and not db.get("users"):
                    user_id = secrets.token_hex(16)
                    user = {
                        "id": user_id,
                        "email": env_admin_email,
                        "full_name": "Super Administrator",
                        "password_hash": _hash_password(env_admin_pass),
                        "password_history": [],
                        "role": "administrator",
                        "permissions": ["platform:access", "statements:upload", "reports:export", "analytics:view", "users:manage", "audit:read", "sessions:revoke"],
                        "status": "active",
                        "failed_attempts": 0,
                        "locked_until": 0,
                        "created_at": now,
                        "activated_at": now,
                        "last_login": now,
                    }
                    db.setdefault("users", {})[env_admin_email] = user
                    auth_store.audit(db, "admin_autobootstrap", user_id, user_id, source=ip)
                    valid = True

        # If password is verified, clear any lockouts
        if valid and user:
            user["locked_until"] = 0
            user["failed_attempts"] = 0
            user["last_login"] = now

        if not user or not valid or user.get("status") != "active":
            ip_rec["count"] += 1; db["ip_failures"][ip] = ip_rec
            if user:
                user["failed_attempts"] = user.get("failed_attempts", 0) + 1
                if user["failed_attempts"] >= 3:
                    user["locked_until"] = now + LOCK_SECONDS
                    user["failed_attempts"] = 0
            auth_store.audit(db, "login_failed", None, user.get("id") if user else None, source=ip)
            if user and user.get("locked_until", 0) > now:
                outcome["error"] = (423, f"Your account is temporarily locked. Try again in {int(user['locked_until'] - now)} seconds.")
            else:
                remaining = 3 - user.get("failed_attempts", 0) if user else None
                outcome["error"] = (401, "Invalid email or password." if remaining is None else f"Invalid email or password. {remaining} attempt(s) remaining.")
            return
        user["failed_attempts"] = 0; user["locked_until"] = 0; user["last_login"] = now
        ip_rec["count"] = 0; db["ip_failures"][ip] = ip_rec
        raw = secrets.token_urlsafe(48); key = hashlib.sha256(raw.encode()).hexdigest()
        max_age = REMEMBER_SECONDS if body.remember else ABSOLUTE_SECONDS
        db["sessions"][key] = {"id": secrets.token_urlsafe(12), "user_id": user["id"], "created_at": now, "last_seen": now, "idle_timeout": max(IDLE_SECONDS, max_age) if body.remember else IDLE_SECONDS, "expires_at": now + max_age, "absolute_expiry": now + max_age}
        auth_store.audit(db, "login_success", user["id"], user["id"], source=ip)
        outcome.update(session=raw, user={"id": user["id"], "email": user["email"], "full_name": user.get("full_name") or user["email"].split("@")[0].replace(".", " ").title(), "role": user["role"], "permissions": user.get("permissions", [])}, max_age=max_age)
    auth_store.update(change)
    if outcome["error"]:
        status, detail = outcome["error"]
        raise HTTPException(status, detail)
    _cookie(response, SESSION_COOKIE, outcome["session"], max_age=outcome["max_age"] if body.remember else None, httponly=True)
    return {"user": outcome["user"]}


@router.get("/me")
async def me(request: Request):
    user = _current(request)
    if not user: raise HTTPException(401, "Sign in required.")
    return {"user": user}


@router.post("/logout")
async def logout(request: Request, response: Response):
    _csrf_ok(request)
    token = request.cookies.get(SESSION_COOKIE, "")
    key = hashlib.sha256(token.encode()).hexdigest()
    def change(db):
        session = db.setdefault("sessions", {}).pop(key, None)
        if session: auth_store.audit(db, "logout", session["user_id"], session["user_id"])
    auth_store.update(change)
    response.delete_cookie(SESSION_COOKIE, path="/", secure=COOKIE_SECURE, httponly=True, samesite=COOKIE_SAMESITE)
    return {"ok": True}


@router.post("/change-password")
async def change_password(body: ChangePasswordBody, request: Request, response: Response):
    _csrf_ok(request)
    current = _current(request)
    if not current: raise HTTPException(401, "Sign in required.")
    _validate_password(body.new_password)
    now = time.time(); new_hash = _hash_password(body.new_password); replacement = secrets.token_urlsafe(48); new_key = hashlib.sha256(replacement.encode()).hexdigest()
    def change(db):
        user = next(u for u in db["users"].values() if u["id"] == current["id"])
        if not _verify_password(body.current_password, user["password_hash"]): raise HTTPException(400, "Current password is incorrect.")
        history = [user["password_hash"], *user.get("password_history", [])][:5]
        if any(_verify_password(body.new_password, old) for old in history): raise HTTPException(400, "Choose a password not used recently.")
        user["password_hash"] = new_hash; user["password_history"] = history
        db["sessions"] = {new_key: {"id": secrets.token_urlsafe(12), "user_id": user["id"], "created_at": now, "last_seen": now, "idle_timeout": IDLE_SECONDS, "expires_at": now + ABSOLUTE_SECONDS, "absolute_expiry": now + ABSOLUTE_SECONDS}}
        auth_store.audit(db, "password_changed", user["id"], user["id"])
    auth_store.update(change)
    _cookie(response, SESSION_COOKIE, replacement, max_age=ABSOLUTE_SECONDS, httponly=True)
    try:
        if not await asyncio.to_thread(_send_password_notice, current["email"]): raise RuntimeError("Email delivery failed")
    except Exception:
        log.warning("Password change notification delivery failed.")
        auth_store.update(lambda db: auth_store.audit(db, "password_notice_delivery_failed", current["id"], current["id"]))
    return {"ok": True}


def _has_email_provider() -> bool:
    api_key = os.getenv("RESEND_API_KEY", "").strip()
    if api_key:
        return bool(os.getenv("RESEND_FROM_EMAIL", "").strip())
    return bool(os.getenv("SMTP_HOST", "").strip() and os.getenv("SMTP_FROM_EMAIL", "").strip())


def _send_email_resend(
    to_email: str,
    subject: str,
    text_content: str,
    html_content: str,
    *,
    idempotency_key: str | None = None
) -> bool:
    api_key = os.getenv("RESEND_API_KEY", "").strip()
    from_email = os.getenv("RESEND_FROM_EMAIL", "").strip()
    from_name = os.getenv("RESEND_FROM_NAME", "SEPL Security").strip()
    if not api_key or not from_email:
        return False

    sender = f"{from_name} <{from_email}>" if from_name else from_email
    payload = {
        "from": sender,
        "to": [to_email],
        "subject": subject,
        "text": text_content,
        "html": html_content,
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "SEPL-AI-Data-Analysis/1.0",
    }
    if idempotency_key:
        headers["Idempotency-Key"] = str(idempotency_key)

    req = urllib.request.Request("https://api.resend.com/emails", data=data, headers=headers, method="POST")
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=10, context=context) as resp:
            if resp.status in (200, 201):
                res_body = json.loads(resp.read().decode("utf-8"))
                if not isinstance(res_body, dict):
                    log.warning("Resend returned unexpected non-object JSON payload.")
                    return False
                email_id = res_body.get("id")
                if not isinstance(email_id, str) or not email_id.strip():
                    log.warning("Resend response missing valid email id.")
                    return False
                log.info("Email dispatched successfully via Resend HTTPS: id=%s", email_id.strip())
                return True
            log.warning("Resend returned unexpected HTTP status: %s", resp.status)
            return False
    except urllib.error.HTTPError as e:
        log.warning("Resend API rejected request: HTTP %s reason=%s", e.code, e.reason)
        return False
    except urllib.error.URLError as e:
        log.warning("Resend API connection error: %s", type(e.reason).__name__ if e.reason else type(e).__name__)
        return False
    except TimeoutError:
        log.warning("Resend API request timed out after 10 seconds.")
        return False
    except Exception as e:
        log.warning("Resend API unexpected failure: %s", type(e).__name__)
        return False


def _send_email_smtp(
    to_email: str,
    subject: str,
    text_content: str,
    html_content: str
) -> bool:
    host = os.getenv("SMTP_HOST", "").strip()
    sender = os.getenv("SMTP_FROM_EMAIL", "").strip()
    port = int(os.getenv("SMTP_PORT", "587"))
    sender_name = os.getenv("SMTP_FROM_NAME", "SEPL Security").strip()
    if not host or not sender:
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{sender_name} <{sender}>" if sender_name else sender
    msg["To"] = to_email
    msg.set_content(text_content)
    msg.add_alternative(html_content, subtype="html")

    context = ssl.create_default_context()
    client = smtplib.SMTP_SSL(host, port, timeout=10, context=context) if port == 465 else smtplib.SMTP(host, port, timeout=10)
    try:
        with client as server:
            if port != 465:
                server.starttls(context=context)
            username = os.getenv("SMTP_USERNAME", "").strip()
            if username:
                server.login(username, os.getenv("SMTP_PASSWORD", ""))
            server.send_message(msg)
        return True
    except Exception as e:
        log.warning("SMTP dispatch failure: %s", type(e).__name__)
        return False


def _send_email(
    to_email: str,
    subject: str,
    text_content: str,
    html_content: str,
    *,
    idempotency_key: str | None = None
) -> bool:
    if os.getenv("RESEND_API_KEY", "").strip():
        return _send_email_resend(to_email, subject, text_content, html_content, idempotency_key=idempotency_key)
    if os.getenv("SMTP_HOST", "").strip() and os.getenv("SMTP_FROM_EMAIL", "").strip():
        return _send_email_smtp(to_email, subject, text_content, html_content)
    return False


def _send_otp(email: str, otp: str, *args, **kwargs) -> bool:
    subject = "SEPL account recovery code"
    text = f"Your SEPL password recovery code is {otp}. It expires in 10 minutes. If you did not request this, ignore this email."
    html = f"<div style='font-family:Arial;color:#12306b'><h2>SEPL account recovery</h2><p>Your verification code is:</p><p style='font-size:28px;font-weight:bold;letter-spacing:6px'>{otp}</p><p>This code expires in 10 minutes. Ignore this message if you did not request it.</p></div>"
    idempotency_key = kwargs.get("idempotency_key") or hashlib.sha256(f"{email}:{otp}".encode()).hexdigest()
    return _send_email(email, subject, text, html, idempotency_key=idempotency_key)


def _send_password_notice(email: str) -> bool:
    subject = "Your SEPL password was changed"
    text = "Your SEPL account password was changed. If you did not make this change, contact your administrator immediately."
    html = "<div style='font-family:Arial;color:#12306b'><h2>SEPL security notice</h2><p>Your account password was changed.</p><p>If you did not make this change, contact your administrator immediately.</p></div>"
    return _send_email(email, subject, text, html)


def _send_invitation(email: str, full_name: str, activation_url: str, expires_in_hours: int = INVITATION_TTL_HOURS) -> bool:
    subject = "Welcome to SEPL — Activate Your Account"
    text = (
        f"Hello {full_name},\n\n"
        "You have been invited to join the SEPL AI Data Analysis Platform.\n\n"
        f"To activate your account and choose your password, visit:\n{activation_url}\n\n"
        f"This link will expire in {expires_in_hours} hours.\n\n"
        "If you did not expect this invitation, please ignore this email."
    )
    html = f"""<div style='font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; padding: 24px; color: #1e293b;'>
      <div style='max-width: 560px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden;'>
        <div style='background: linear-gradient(135deg, #1e3a8a, #0f172a); padding: 24px 32px;'>
          <h1 style='color: #ffffff; margin: 0; font-size: 20px; font-weight: 700;'>SEPL AI Data Analysis Platform</h1>
          <p style='color: #93c5fd; margin: 4px 0 0 0; font-size: 13px;'>Enterprise Financial Intelligence</p>
        </div>
        <div style='padding: 32px;'>
          <h2 style='color: #0f172a; font-size: 18px; margin-top: 0;'>Welcome, {full_name}!</h2>
          <p style='color: #475569; font-size: 14px; line-height: 1.6;'>
            You have been invited by an administrator to access your enterprise workspace on the <strong>SEPL AI Data Analysis Platform</strong>.
          </p>
          <p style='color: #475569; font-size: 14px; line-height: 1.6;'>
            Click the secure button below to activate your account and choose your password:
          </p>
          <div style='text-align: center; margin: 28px 0;'>
            <a href='{activation_url}' style='background: #2563eb; color: #ffffff; text-decoration: none; padding: 12px 28px; border-radius: 8px; font-weight: 600; font-size: 14px; display: inline-block;'>Activate Account & Set Password</a>
          </div>
          <p style='color: #64748b; font-size: 12px; line-height: 1.5;'>
            Or copy and paste this secure link directly into your browser:<br/>
            <a href='{activation_url}' style='color: #2563eb; word-break: break-all;'>{activation_url}</a>
          </p>
          <div style='margin-top: 24px; padding: 12px 16px; background-color: #f1f5f9; border-radius: 8px; border-left: 3px solid #3b82f6;'>
            <p style='margin: 0; color: #334155; font-size: 12px;'>
              <strong>Security Notice:</strong> This activation link is single-use and will expire in {expires_in_hours} hours.
            </p>
          </div>
        </div>
        <div style='padding: 16px 32px; background: #f8fafc; border-top: 1px solid #e2e8f0; text-align: center;'>
          <p style='color: #94a3b8; font-size: 11px; margin: 0;'>
            Powered by SEPL &bull; Smart Solutions. Better Tomorrow.
          </p>
        </div>
      </div>
    </div>"""
    return _send_email(email, subject, text, html)


@router.get("/activate/verify")
async def verify_activation_token(token: str):
    clean_token = str(token).strip()
    if not clean_token:
        raise HTTPException(400, "Invitation token is required.")
    token_hash = hashlib.sha256(clean_token.encode()).hexdigest()
    now = time.time()
    db = auth_store.read()
    user = next((u for u in db.get("users", {}).values() if u.get("invitation_token_hash") == token_hash and u.get("invitation_expires_at", 0) > now and u.get("status") == "pending_activation"), None)
    if not user:
        raise HTTPException(400, "This invitation link is invalid, expired, or has already been used.")
    return {
        "ok": True,
        "email": user["email"],
        "full_name": user.get("full_name") or user["email"].split("@")[0].replace(".", " ").title(),
        "role": user["role"],
        "expires_at": user.get("invitation_expires_at"),
    }


@router.post("/activate")
async def activate_account(body: AccountActivate, request: Request):
    _csrf_ok(request)
    clean_token = body.token.strip()
    _validate_password(body.password)
    token_hash = hashlib.sha256(clean_token.encode()).hexdigest()
    encoded = _hash_password(body.password)
    now = time.time()
    activated_info = {"id": None, "email": None}
    def change(db):
        user = next((u for u in db.setdefault("users", {}).values() if u.get("invitation_token_hash") == token_hash and u.get("invitation_expires_at", 0) > now and u.get("status") == "pending_activation"), None)
        if not user:
            raise HTTPException(400, "This invitation link is invalid, expired, or has already been used.")
        user["password_hash"] = encoded
        user["password_history"] = [encoded]
        user["status"] = "active"
        user["activated_at"] = now
        user["invitation_token_hash"] = None
        user["invitation_expires_at"] = None
        user["failed_attempts"] = 0
        user["locked_until"] = 0
        auth_store.audit(db, "account_activated", user["id"], user["id"], source=_get_client_ip(request))
        activated_info["id"] = user["id"]
        activated_info["email"] = user["email"]
    auth_store.update(change)
    return {"ok": True, "message": "Account activated successfully. You can now sign in with your email and password.", "email": activated_info["email"]}


@router.post("/recovery/request")
async def recovery_request(body: RecoveryRequest, request: Request):
    _csrf_ok(request)
    if not _has_email_provider():
        raise HTTPException(503, "Password recovery is temporarily unavailable. Contact your administrator.")
    email = str(body.email).strip().lower()
    if "@" not in email or "." not in email.rsplit("@", 1)[-1]: raise HTTPException(422, "Enter a valid email address.")
    now = time.time(); otp = f"{secrets.randbelow(1_000_000):06d}"; code_hash = _hash_password(otp)
    created = {"send": False, "key": None, "rate_limited": False}
    ip = request.client.host if request.client else "unknown"
    def change(db):
        ip_limits = db.setdefault("recovery_ip", {})
        ip_record = ip_limits.get(ip, {"count": 0, "window": now})
        if now - ip_record.get("window", now) > 3600: ip_record = {"count": 0, "window": now}
        if ip_record["count"] >= 10:
            created["rate_limited"] = True
            return
        ip_record["count"] += 1; ip_limits[ip] = ip_record
        user = next((u for u in db.setdefault("users", {}).values() if u["email"] == email and u.get("status") == "active"), None)
        if not user: return
        previous = db.setdefault("recovery", {}).get(email, {})
        if now - previous.get("issued_at", 0) < 60: return
        db["recovery"][email] = {"otp_hash": code_hash, "issued_at": now, "expires_at": now + 600, "attempts": 0, "user_id": user["id"], "used": False}
        created.update(send=True, key=email)
    auth_store.update(change)
    if created["rate_limited"]: raise HTTPException(429, "Too many recovery requests. Try again later.")
    if created["send"]:
        try:
            sent = await asyncio.to_thread(_send_otp, email, otp)
            if not sent: raise RuntimeError("Email delivery failed")
        except Exception:
            def failed(db): db.get("recovery", {}).pop(email, None); auth_store.audit(db, "recovery_delivery_failed", None, None)
            auth_store.update(failed)
            log.warning("Password recovery delivery failed; configure email delivery provider and retry.")
    return {"message": "If this email belongs to an active account and delivery is available, recovery instructions may arrive. If no message arrives, contact your administrator."}


@router.post("/recovery/verify")
async def recovery_verify(body: OTPVerify, request: Request):
    _csrf_ok(request)
    email = str(body.email).strip().lower(); now = time.time(); outcome = {"token": None, "error": False}
    def change(db):
        record = db.setdefault("recovery", {}).get(email)
        if not record or record.get("used") or record.get("expires_at", 0) <= now or record.get("attempts", 0) >= 5:
            outcome["error"] = True; return
        record["attempts"] += 1
        if not _verify_password(body.otp, record["otp_hash"]):
            outcome["error"] = True; return
        record["used"] = True
        token = secrets.token_urlsafe(32); record["reset_token_hash"] = hashlib.sha256(token.encode()).hexdigest(); record["reset_expires_at"] = now + 600
        outcome["token"] = token
    auth_store.update(change)
    if outcome["error"]: raise HTTPException(400, "Verification code is invalid or expired.")
    return {"reset_token": outcome["token"]}


@router.post("/recovery/reset")
async def recovery_reset(body: PasswordReset, request: Request):
    _csrf_ok(request); _validate_password(body.new_password)
    now = time.time(); reset_hash = hashlib.sha256(body.reset_token.encode()).hexdigest(); new_hash = _hash_password(body.new_password); done = {"ok": False, "user_id": None}
    def change(db):
        target = next(((email,rec) for email,rec in db.setdefault("recovery", {}).items() if rec.get("reset_token_hash") == reset_hash and rec.get("reset_expires_at", 0) > now), None)
        if not target: return
        email, rec = target; user = next((u for u in db["users"].values() if u["id"] == rec["user_id"]), None)
        if not user: return
        old = [user["password_hash"], *user.get("password_history", [])][:5]
        if any(_verify_password(body.new_password, h) for h in old): raise HTTPException(400, "Choose a password not used recently.")
        user["password_history"] = old; user["password_hash"] = new_hash
        db["sessions"] = {k:v for k,v in db.setdefault("sessions", {}).items() if v.get("user_id") != user["id"]}
        rec.pop("reset_token_hash", None); rec["reset_expires_at"] = 0
        auth_store.audit(db, "password_reset", user["id"], user["id"]); done.update(ok=True, user_id=user["id"])
    auth_store.update(change)
    if not done["ok"]: raise HTTPException(400, "Reset authorization is invalid or expired.")
    record = auth_store.read()
    target_user_id = done["user_id"]
    email = next((address for address, user in record.get("users", {}).items() if user.get("id") == target_user_id), None)
    if email:
        try:
            if not await asyncio.to_thread(_send_password_notice, email): raise RuntimeError("Email delivery failed")
        except Exception:
            log.warning("Password reset notification delivery failed.")
            auth_store.update(lambda db: auth_store.audit(db, "password_notice_delivery_failed", target_user_id, target_user_id))
    return {"ok": True, "message": "Password reset. Sign in with the new password."}


def current_user(request: Request):
    return _current(request)


def _admin(request: Request):
    user = _current(request)
    if not user: raise HTTPException(401, "Sign in required.")
    if user.get("role") != "administrator" or "users:manage" not in user.get("permissions", []): raise HTTPException(403, "Administrator permission required.")
    return user


@router.get("/sessions")
async def list_sessions(request: Request):
    current = _current(request)
    if not current: raise HTTPException(401, "Sign in required.")
    active = []
    token = request.cookies.get(SESSION_COOKIE, "")
    current_hash = hashlib.sha256(token.encode()).hexdigest()
    def read_records(db):
        active.extend({"id": item.get("id"), "current": key == current_hash, "created_at": item["created_at"], "last_seen": item["last_seen"], "expires_at": item["expires_at"]} for key, item in db.setdefault("sessions", {}).items() if item.get("user_id") == current["id"] and item.get("expires_at", 0) > time.time())
    auth_store.update(read_records)
    return {"sessions": active}


@router.delete("/sessions/{session_hash}")
async def revoke_session(session_hash: str, request: Request):
    _csrf_ok(request)
    current = _current(request)
    if not current: raise HTTPException(401, "Sign in required.")
    removed = {"value": False, "current": False}
    current_hash = hashlib.sha256(request.cookies.get(SESSION_COOKIE, "").encode()).hexdigest()
    def change(db):
        match = next(((key, value) for key, value in db.setdefault("sessions", {}).items() if value.get("id") == session_hash), None)
        if match and match[1].get("user_id") == current["id"]:
            removed["current"] = match[0] == current_hash
            db["sessions"].pop(match[0], None); removed["value"] = True
            auth_store.audit(db, "session_revoked", current["id"], current["id"])
    auth_store.update(change)
    if not removed["value"]: raise HTTPException(404, "Session not found.")
    response = Response(status_code=204)
    if removed["current"]:
        response.delete_cookie(SESSION_COOKIE, path="/", secure=COOKIE_SECURE, httponly=True, samesite=COOKIE_SAMESITE)
    return response


@router.get("/admin/users")
async def admin_users(request: Request):
    _admin(request)
    db = auth_store.read()
    users_list = []
    for u in db.get("users", {}).values():
        full_name = u.get("full_name") or u["email"].split("@")[0].replace(".", " ").title()
        default_perms = ["platform:access", "statements:upload", "reports:export", "analytics:view", "users:manage", "audit:read", "sessions:revoke"] if u.get("role") == "administrator" else ["platform:access", "statements:upload", "reports:export", "analytics:view"]
        users_list.append({
            "id": u["id"],
            "email": u["email"],
            "full_name": full_name,
            "role": u["role"],
            "status": u["status"],
            "permissions": u.get("permissions", default_perms),
            "created_at": u.get("created_at", 0),
            "activated_at": u.get("activated_at"),
            "locked_until": u.get("locked_until", 0),
            "last_login": u.get("last_login"),
            "invitation_expires_at": u.get("invitation_expires_at"),
        })
    return {"users": users_list}


def _is_permanent_super_admin(email: str | None) -> bool:
    if not email:
        return False
    super_admin = os.getenv("AUTH_ADMIN_EMAIL", "itsmaatech@gmail.com").strip().lower()
    return email.strip().lower() == super_admin


def _get_public_frontend_url(request: Request | None = None) -> str:
    # 1. Explicit production / deployment environment variables take absolute precedence
    for key in ("PUBLIC_FRONTEND_URL", "FRONTEND_URL", "APP_URL"):
        val = os.getenv(key, "").strip().rstrip("/")
        if val:
            if not val.startswith("http://") and not val.startswith("https://"):
                val = f"https://{val}"
            return val
    # 2. Vercel deployment URL
    vercel_url = os.getenv("VERCEL_URL", "").strip().rstrip("/")
    if vercel_url:
        return f"https://{vercel_url}"
    # 3. Derive from incoming request origin or referer if available (e.g. local dev port 5173/5174)
    if request:
        origin = request.headers.get("origin") or request.headers.get("referer")
        if origin:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(origin)
                if parsed.scheme and parsed.netloc:
                    return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
            except Exception:
                pass
    # 4. Fallback to FRONTEND_ORIGIN or default local development port
    configured = os.getenv("FRONTEND_ORIGIN", "").strip().rstrip("/")
    if configured:
        return configured
    return "http://localhost:5173"


@router.post("/admin/users", status_code=201)
async def admin_create_user(body: AccountCreate, request: Request):
    actor = _admin(request)
    _csrf_ok(request)
    email = body.email.strip().lower()
    if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        raise HTTPException(422, "Enter a valid email address.")
    full_name = body.full_name.strip() if body.full_name and body.full_name.strip() else email.split("@")[0].replace(".", " ").title()

    default_perms = (
        ["platform:access", "statements:upload", "reports:export", "analytics:view", "users:manage", "audit:read", "sessions:revoke"]
        if body.role == "administrator"
        else ["platform:access", "statements:upload", "reports:export", "analytics:view"]
    )
    permissions = body.permissions if body.permissions is not None else default_perms
    now = time.time()
    frontend_origin = _get_public_frontend_url(request)

    # Check for duplicate email upfront
    existing_db = auth_store.read()
    if email in existing_db.get("users", {}):
        raise HTTPException(409, "Account already exists.")

    if body.password:
        _validate_password(body.password)
        encoded = _hash_password(body.password)
        created = {"user": None}
        def change(db):
            if email in db.setdefault("users", {}):
                raise HTTPException(409, "Account already exists.")
            user_id = secrets.token_hex(16)
            user = {
                "id": user_id,
                "email": email,
                "full_name": full_name,
                "password_hash": encoded,
                "password_history": [encoded],
                "role": body.role,
                "permissions": permissions,
                "status": "active",
                "failed_attempts": 0,
                "locked_until": 0,
                "created_at": now,
                "activated_at": now,
                "last_login": None,
                "invitation_token_hash": None,
                "invitation_expires_at": None,
            }
            db["users"][email] = user
            auth_store.audit(db, "account_created", actor["id"], user_id, role=body.role, source=_get_client_ip(request))
            created["user"] = {
                "id": user_id,
                "email": email,
                "full_name": full_name,
                "role": body.role,
                "status": "active",
                "permissions": permissions,
                "created_at": now,
                "activated_at": now,
            }
        auth_store.update(change)
        return created["user"]

    # Invitation workflow: create pending user with expiring single-use token
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = now + INVITATION_TTL_SECONDS
    activation_url = f"{frontend_origin}/activate?token={raw_token}"
    created = {"user": None}

    def change(db):
        if email in db.setdefault("users", {}):
            raise HTTPException(409, "Account already exists.")
        user_id = secrets.token_hex(16)
        user = {
            "id": user_id,
            "email": email,
            "full_name": full_name,
            "password_hash": None,
            "password_history": [],
            "role": body.role,
            "permissions": permissions,
            "status": "pending_activation",
            "failed_attempts": 0,
            "locked_until": 0,
            "created_at": now,
            "activated_at": None,
            "last_login": None,
            "invitation_token_hash": token_hash,
            "invitation_expires_at": expires_at,
        }
        db["users"][email] = user
        auth_store.audit(db, "user_invited", actor["id"], user_id, role=body.role, source=_get_client_ip(request))
        created["user"] = {
            "id": user_id,
            "email": email,
            "full_name": full_name,
            "role": body.role,
            "status": "pending_activation",
            "permissions": permissions,
            "created_at": now,
            "invitation_expires_at": expires_at,
        }
    auth_store.update(change)

    email_sent = False
    try:
        email_sent = await asyncio.to_thread(_send_invitation, email, full_name, activation_url, expires_in_hours=INVITATION_TTL_HOURS)
        if email_sent:
            auth_store.update(lambda db: auth_store.audit(db, "invitation_email_sent", actor["id"], created["user"]["id"]))
    except Exception as exc:
        log.warning("Invitation email delivery failed: %s", exc)
        auth_store.update(lambda db: auth_store.audit(db, "invitation_email_delivery_failed", actor["id"], created["user"]["id"], error=str(exc)))

    return {
        "id": created["user"]["id"],
        "email": created["user"]["email"],
        "full_name": created["user"]["full_name"],
        "role": created["user"]["role"],
        "status": created["user"]["status"],
        "permissions": created["user"]["permissions"],
        "email_sent": email_sent,
        "invitation_url": activation_url,
        "message": "User created and invitation email sent." if email_sent else "User created. Email provider is not configured, so email could not be sent automatically. Copy and share the invitation link.",
    }


@router.patch("/admin/users/{user_id}")
async def admin_update_user(user_id: str, body: AccountUpdate, request: Request):
    actor = _admin(request)
    _csrf_ok(request)
    outcome = {"user": None}
    def change(db):
        user = next((u for u in db.setdefault("users", {}).values() if u["id"] == user_id), None)
        if not user: raise HTTPException(404, "Account not found.")
        is_super_admin = _is_permanent_super_admin(user["email"])
        if is_super_admin:
            if body.status is not None and body.status != "active":
                raise HTTPException(403, "The permanent Super Admin account cannot be suspended or deactivated.")
            if body.role is not None and body.role != "administrator":
                raise HTTPException(403, "The permanent Super Admin account cannot be demoted.")
            if actor["email"].lower() != user["email"].lower():
                raise HTTPException(403, "Only the permanent Super Admin can modify their own account profile.")
        old_status, old_role = user["status"], user["role"]
        if body.full_name is not None and body.full_name.strip():
            user["full_name"] = body.full_name.strip()
        if body.status is not None:
            user["status"] = body.status
        if body.role is not None:
            user["role"] = body.role
            if body.permissions is None:
                user["permissions"] = ["platform:access", "statements:upload", "reports:export", "analytics:view", "users:manage", "audit:read", "sessions:revoke"] if body.role == "administrator" else ["platform:access", "statements:upload", "reports:export", "analytics:view"]
        if body.permissions is not None:
            user["permissions"] = body.permissions

        active_admins = [u for u in db["users"].values() if u["role"] == "administrator" and u["status"] == "active"]
        if old_role == "administrator" and old_status == "active" and len(active_admins) == 0:
            user["status"], user["role"] = old_status, old_role
            user["permissions"] = ["platform:access", "users:manage", "audit:read", "sessions:revoke"]
            raise HTTPException(409, "Cannot remove the last active administrator.")

        if user["status"] != "active":
            db["sessions"] = {k: v for k, v in db.setdefault("sessions", {}).items() if v.get("user_id") != user_id}

        if body.status is not None: auth_store.audit(db, "account_status_changed", actor["id"], user_id, old=old_status, new=user["status"], source=_get_client_ip(request))
        if body.role is not None: auth_store.audit(db, "account_role_changed", actor["id"], user_id, old=old_role, new=user["role"], source=_get_client_ip(request))
        outcome["user"] = {
            "id": user["id"],
            "email": user["email"],
            "full_name": user.get("full_name") or user["email"].split("@")[0].replace(".", " ").title(),
            "role": user["role"],
            "status": user["status"],
            "permissions": user.get("permissions", []),
        }
    auth_store.update(change)
    return outcome["user"]


@router.post("/admin/users/{user_id}/resend-invitation")
async def admin_resend_invitation(user_id: str, request: Request):
    actor = _admin(request)
    _csrf_ok(request)
    now = time.time()
    frontend_origin = _get_public_frontend_url(request)
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = now + INVITATION_TTL_SECONDS
    activation_url = f"{frontend_origin}/activate?token={raw_token}"
    target = {"email": None, "full_name": None}

    def change(db):
        user = next((u for u in db.setdefault("users", {}).values() if u["id"] == user_id), None)
        if not user:
            raise HTTPException(404, "User account not found.")
        if user.get("status") != "pending_activation":
            raise HTTPException(400, "Invitation can only be resent for accounts pending activation.")
        user["invitation_token_hash"] = token_hash
        user["invitation_expires_at"] = expires_at
        target["email"] = user["email"]
        target["full_name"] = user.get("full_name") or user["email"].split("@")[0].replace(".", " ").title()
        auth_store.audit(db, "invitation_resent", actor["id"], user_id, source=_get_client_ip(request))

    auth_store.update(change)

    email_sent = False
    try:
        email_sent = await asyncio.to_thread(_send_invitation, target["email"], target["full_name"], activation_url, expires_in_hours=INVITATION_TTL_HOURS)
        if email_sent:
            auth_store.update(lambda db: auth_store.audit(db, "invitation_email_sent", actor["id"], user_id))
    except Exception as exc:
        log.warning("Resend invitation email delivery failed: %s", exc)

    return {
        "ok": True,
        "email_sent": email_sent,
        "invitation_url": activation_url,
        "message": "Invitation resent." if email_sent else "Invitation renewed. Email delivery provider is not configured, so email could not be sent automatically. Share the invitation link manually.",
    }


@router.delete("/admin/users/{user_id}")
async def admin_delete_user(user_id: str, request: Request):
    actor = _admin(request)
    _csrf_ok(request)
    if user_id == actor["id"]:
        raise HTTPException(400, "You cannot delete your own account.")

    def change(db):
        email_to_remove = None
        target_user = None
        for em, u in list(db.setdefault("users", {}).items()):
            if u.get("id") == user_id:
                email_to_remove = em
                target_user = u
                break
        if not target_user:
            raise HTTPException(404, "User account not found.")

        # Safety: Permanent Super Admin cannot be deleted
        if _is_permanent_super_admin(target_user.get("email")):
            raise HTTPException(403, "The permanent Super Admin account cannot be deleted.")

        # Safety: Cannot delete last active admin
        if target_user.get("role") == "administrator" and target_user.get("status") == "active":
            active_admins = [u for u in db["users"].values() if u.get("role") == "administrator" and u.get("status") == "active" and u.get("id") != user_id]
            if not active_admins:
                raise HTTPException(409, "Cannot delete the last active administrator.")

        # Revoke all sessions for this user
        db["sessions"] = {k: v for k, v in db.setdefault("sessions", {}).items() if v.get("user_id") != user_id}
        if email_to_remove:
            db.setdefault("recovery", {}).pop(email_to_remove, None)
            db["users"].pop(email_to_remove, None)

        auth_store.audit(db, "account_deleted", actor["id"], user_id, email=email_to_remove, source=_get_client_ip(request))

    auth_store.update(change)
    return {"ok": True, "message": "User deleted successfully."}


@router.get("/admin/audit")
async def admin_audit(request: Request):
    user = _admin(request)
    if "audit:read" not in user.get("permissions", []): raise HTTPException(403, "Audit permission required.")
    db = auth_store.read()
    return {"events": db.get("audit", [])[-500:]}


@router.post("/admin/users/{user_id}/unlock")
async def admin_unlock(user_id: str, request: Request):
    actor = _admin(request); _csrf_ok(request); found = {"value": False}
    def change(db):
        user = next((u for u in db.setdefault("users", {}).values() if u["id"] == user_id), None)
        if not user: return
        user["failed_attempts"] = 0; user["locked_until"] = 0; found["value"] = True
        auth_store.audit(db, "account_unlocked", actor["id"], user_id, source=_get_client_ip(request))
    auth_store.update(change)
    if not found["value"]: raise HTTPException(404, "Account not found.")
    return {"ok": True}


@router.delete("/admin/users/{user_id}/sessions")
async def admin_revoke_sessions(user_id: str, request: Request):
    actor = _admin(request); _csrf_ok(request); revoked = {"count": 0}
    def change(db):
        if not any(u.get("id") == user_id for u in db.setdefault("users", {}).values()): raise HTTPException(404, "Account not found.")
        before = len(db.setdefault("sessions", {}))
        db["sessions"] = {key:value for key,value in db["sessions"].items() if value.get("user_id") != user_id}
        revoked["count"] = before - len(db["sessions"])
        auth_store.audit(db, "administrator_revoked_sessions", actor["id"], user_id, count=revoked["count"], source=_get_client_ip(request))
    auth_store.update(change)
    return {"ok": True, "revoked_count": revoked["count"]}


@router.post("/admin/users/{user_id}/reset-password")
async def admin_reset_password(user_id: str, body: AdministratorPasswordReset, request: Request):
    actor = _admin(request); _csrf_ok(request); _validate_password(body.new_password)
    replacement_hash = _hash_password(body.new_password); found = {"email": None}
    def change(db):
        user = next((u for u in db.setdefault("users", {}).values() if u["id"] == user_id), None)
        if not user: raise HTTPException(404, "Account not found.")
        history = [user["password_hash"], *user.get("password_history", [])][:5]
        if any(_verify_password(body.new_password, old) for old in history): raise HTTPException(400, "Choose a password not used recently.")
        user["password_hash"] = replacement_hash; user["password_history"] = history
        db["sessions"] = {key:value for key,value in db.setdefault("sessions", {}).items() if value.get("user_id") != user_id}
        auth_store.audit(db, "administrator_password_reset", actor["id"], user_id, source=_get_client_ip(request))
        found["email"] = user["email"]
    auth_store.update(change)
    try:
        if not await asyncio.to_thread(_send_password_notice, found["email"]): raise RuntimeError("Email delivery failed")
    except Exception:
        log.warning("Administrator password reset notification delivery failed.")
        auth_store.update(lambda db: auth_store.audit(db, "password_notice_delivery_failed", actor["id"], user_id))
    return {"ok": True, "sessions_revoked": True}
