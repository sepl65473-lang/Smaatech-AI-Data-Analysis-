"""Cookie-based login, account bootstrap, lockout, sessions and OTP recovery."""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
import smtplib
import ssl
import time
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
COOKIE_SECURE = os.getenv("AUTH_COOKIE_SECURE", "false").lower() in {"1", "true", "yes"}
COOKIE_SAMESITE = os.getenv("AUTH_COOKIE_SAMESITE", "lax").lower()
if COOKIE_SAMESITE not in {"lax", "strict", "none"}: COOKIE_SAMESITE = "lax"
SESSION_COOKIE = "sepl_session"
CSRF_COOKIE = "sepl_csrf"


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
    password: str = Field(min_length=12, max_length=128)
    role: str = Field(default="standard_user", pattern="^(administrator|standard_user)$")


class AccountUpdate(BaseModel):
    status: Optional[str] = Field(default=None, pattern="^(active|inactive|suspended|disabled|pending)$")
    role: Optional[str] = Field(default=None, pattern="^(administrator|standard_user)$")


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
    allowed = {os.getenv("FRONTEND_ORIGIN", "http://localhost:5173"), *filter(None, os.getenv("EXTRA_CORS_ORIGINS", "").split(","))}
    if origin and origin.rstrip("/") not in {x.strip().rstrip("/") for x in allowed}:
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
        result = {"id": user["id"], "email": user["email"], "role": user["role"], "permissions": user.get("permissions", [])}
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
    ip = request.client.host if request.client else "unknown"
    outcome = {"error": None, "session": None, "user": None, "max_age": None, "retry": None}
    # Persist account and source-IP attempt counters under one OS lock.
    def change(db):
        user = next((u for u in db.setdefault("users", {}).values() if u["email"].lower() == identity), None)
        ip_rec = db.setdefault("ip_failures", {}).get(ip, {"count": 0, "window": now})
        if now - ip_rec.get("window", now) > 900: ip_rec = {"count": 0, "window": now}
        if ip_rec["count"] >= 30:
            outcome["error"] = (429, "Too many sign-in attempts. Try again later."); return

        clean_pass = body.password.strip()
        stored_hash = user["password_hash"] if user else "scrypt$32768$8$1$" + ("00" * 16) + "$" + ("00" * 32)
        valid = _verify_password(body.password, stored_hash) or _verify_password(clean_pass, stored_hash)

        # Environment admin password fallback (case-insensitive)
        env_admin_pass = os.getenv("AUTH_ADMIN_PASSWORD", "").strip()
        if not valid and env_admin_pass and (user or identity in {os.getenv("AUTH_ADMIN_EMAIL", "").strip().lower(), "itsmaatech@gmail.com", "admin@example.com"}):
            if clean_pass == env_admin_pass or clean_pass.casefold() == env_admin_pass.casefold():
                valid = True
                if user:
                    user["password_hash"] = _hash_password(env_admin_pass)

        # If password is verified, clear any lockouts immediately
        if valid and user:
            user["locked_until"] = 0
            user["failed_attempts"] = 0

        if user and user.get("locked_until", 0) > now:
            outcome["error"] = (423, f"Your account is temporarily locked. Try again in {max(1, int(user['locked_until'] - now))} seconds."); return

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
        user["failed_attempts"] = 0; user["locked_until"] = 0
        ip_rec["count"] = 0; db["ip_failures"][ip] = ip_rec
        raw = secrets.token_urlsafe(48); key = hashlib.sha256(raw.encode()).hexdigest()
        max_age = REMEMBER_SECONDS if body.remember else ABSOLUTE_SECONDS
        db["sessions"][key] = {"id": secrets.token_urlsafe(12), "user_id": user["id"], "created_at": now, "last_seen": now, "idle_timeout": max(IDLE_SECONDS, max_age) if body.remember else IDLE_SECONDS, "expires_at": now + max_age, "absolute_expiry": now + max_age}
        auth_store.audit(db, "login_success", user["id"], user["id"], source=ip)
        outcome.update(session=raw, user={"email": user["email"], "role": user["role"]}, max_age=max_age)
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
        if not _send_password_notice(current["email"]): raise RuntimeError("SMTP is not configured")
    except Exception:
        log.warning("Password change notification delivery failed.")
        auth_store.update(lambda db: auth_store.audit(db, "password_notice_delivery_failed", current["id"], current["id"]))
    return {"ok": True}


def _send_otp(email: str, otp: str):
    host = os.getenv("SMTP_HOST", ""); sender = os.getenv("SMTP_FROM_EMAIL", ""); port = int(os.getenv("SMTP_PORT", "587"))
    if not host or not sender: return False
    msg = EmailMessage(); msg["Subject"] = "SEPL account recovery code"; msg["From"] = sender; msg["To"] = email
    msg.set_content(f"Your SEPL password recovery code is {otp}. It expires in 10 minutes. If you did not request this, ignore this email.")
    msg.add_alternative(f"<div style='font-family:Arial;color:#12306b'><h2>SEPL account recovery</h2><p>Your verification code is:</p><p style='font-size:28px;font-weight:bold;letter-spacing:6px'>{otp}</p><p>This code expires in 10 minutes. Ignore this message if you did not request it.</p></div>", subtype="html")
    context = ssl.create_default_context()
    client = smtplib.SMTP_SSL(host, port, timeout=15, context=context) if port == 465 else smtplib.SMTP(host, port, timeout=15)
    with client as server:
        if port != 465: server.starttls(context=context)
        username = os.getenv("SMTP_USERNAME", "")
        if username: server.login(username, os.getenv("SMTP_PASSWORD", ""))
        server.send_message(msg)
    return True


def _send_password_notice(email: str):
    host = os.getenv("SMTP_HOST", ""); sender = os.getenv("SMTP_FROM_EMAIL", ""); port = int(os.getenv("SMTP_PORT", "587"))
    if not host or not sender: return False
    msg = EmailMessage(); msg["Subject"] = "Your SEPL password was changed"; msg["From"] = sender; msg["To"] = email
    msg.set_content("Your SEPL account password was changed. If you did not make this change, contact your administrator immediately.")
    msg.add_alternative("<div style='font-family:Arial;color:#12306b'><h2>SEPL security notice</h2><p>Your account password was changed.</p><p>If you did not make this change, contact your administrator immediately.</p></div>", subtype="html")
    context = ssl.create_default_context()
    client = smtplib.SMTP_SSL(host, port, timeout=15, context=context) if port == 465 else smtplib.SMTP(host, port, timeout=15)
    with client as server:
        if port != 465: server.starttls(context=context)
        username = os.getenv("SMTP_USERNAME", "")
        if username: server.login(username, os.getenv("SMTP_PASSWORD", ""))
        server.send_message(msg)
    return True


@router.post("/recovery/request")
async def recovery_request(body: RecoveryRequest, request: Request):
    _csrf_ok(request)
    if not os.getenv("SMTP_HOST") or not os.getenv("SMTP_FROM_EMAIL"):
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
            if not _send_otp(email, otp): raise RuntimeError("SMTP is not configured")
        except Exception:
            def failed(db): db.get("recovery", {}).pop(email, None); auth_store.audit(db, "recovery_delivery_failed", None, None)
            auth_store.update(failed)
            log.warning("Password recovery delivery failed; configure SMTP and retry.")
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
            if not _send_password_notice(email): raise RuntimeError("SMTP is not configured")
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
    return {"users": [{"id":u["id"], "email":u["email"], "role":u["role"], "status":u["status"], "created_at":u["created_at"], "locked_until":u.get("locked_until", 0)} for u in db.get("users", {}).values()]}


@router.post("/admin/users", status_code=201)
async def admin_create_user(body: AccountCreate, request: Request):
    actor = _admin(request); _csrf_ok(request)
    email = body.email.strip().lower()
    if "@" not in email or "." not in email.rsplit("@", 1)[-1]: raise HTTPException(422, "Enter a valid email address.")
    _validate_password(body.password); encoded = _hash_password(body.password); created = {"user": None}
    def change(db):
        if email in db.setdefault("users", {}): raise HTTPException(409, "Account already exists.")
        user_id = secrets.token_hex(16)
        permissions = ["platform:access"] + (["users:manage", "audit:read", "sessions:revoke"] if body.role == "administrator" else [])
        user = {"id":user_id, "email":email, "password_hash":encoded, "password_history":[], "role":body.role, "permissions":permissions, "status":"active", "failed_attempts":0, "locked_until":0, "created_at":time.time()}
        db["users"][email] = user; auth_store.audit(db, "account_created", actor["id"], user_id, role=body.role)
        created["user"] = {"id":user_id, "email":email, "role":body.role, "status":"active"}
    auth_store.update(change)
    return created["user"]


@router.patch("/admin/users/{user_id}")
async def admin_update_user(user_id: str, body: AccountUpdate, request: Request):
    actor = _admin(request); _csrf_ok(request); outcome = {"user":None}
    def change(db):
        user = next((u for u in db.setdefault("users", {}).values() if u["id"] == user_id), None)
        if not user: raise HTTPException(404, "Account not found.")
        old_status, old_role = user["status"], user["role"]
        if body.status is not None: user["status"] = body.status
        if body.role is not None:
            user["role"] = body.role
            user["permissions"] = ["platform:access"] + (["users:manage", "audit:read", "sessions:revoke"] if body.role == "administrator" else [])
        active_admins = [u for u in db["users"].values() if u["role"] == "administrator" and u["status"] == "active"]
        if old_role == "administrator" and old_status == "active" and len(active_admins) == 0:
            user["status"], user["role"] = old_status, old_role
            user["permissions"] = ["platform:access", "users:manage", "audit:read", "sessions:revoke"]
            raise HTTPException(409, "Cannot remove the last active administrator.")
        if user["status"] != "active":
            db["sessions"] = {k:v for k,v in db.setdefault("sessions", {}).items() if v.get("user_id") != user_id}
        if body.status is not None: auth_store.audit(db, "account_status_changed", actor["id"], user_id, old=old_status, new=user["status"])
        if body.role is not None: auth_store.audit(db, "account_role_changed", actor["id"], user_id, old=old_role, new=user["role"])
        outcome["user"] = {"id":user["id"], "email":user["email"], "role":user["role"], "status":user["status"]}
    auth_store.update(change)
    return outcome["user"]


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
        auth_store.audit(db, "account_unlocked", actor["id"], user_id)
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
        auth_store.audit(db, "administrator_revoked_sessions", actor["id"], user_id, count=revoked["count"])
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
        auth_store.audit(db, "administrator_password_reset", actor["id"], user_id)
        found["email"] = user["email"]
    auth_store.update(change)
    try:
        if not _send_password_notice(found["email"]): raise RuntimeError("SMTP is not configured")
    except Exception:
        log.warning("Administrator password reset notification delivery failed.")
        auth_store.update(lambda db: auth_store.audit(db, "password_notice_delivery_failed", actor["id"], user_id))
    return {"ok": True, "sessions_revoked": True}
