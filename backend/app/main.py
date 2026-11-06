import logging
import os

from dotenv import load_dotenv
from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# ---------------------------------------------------------------------------
# Logging — configure before anything else so all module-level loggers
# (config, insight_generator, categorizer, etc.) emit to stdout from startup.
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
# Silence noisy third-party loggers
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("multipart").setLevel(logging.WARNING)
logging.getLogger("watchfiles").setLevel(logging.WARNING)

# ---------------------------------------------------------------------------
# Ensure .env is loaded even when uvicorn imports this module before the
# app process has a chance to set environment variables.
# ---------------------------------------------------------------------------
load_dotenv()

from app.config import settings
from app.routers import upload, results, export, analyze, auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Background worker for data-retention and expired session auto-delete."""
    async def retention_worker():
        while True:
            try:
                await asyncio.sleep(900)  # sweep every 15 minutes
                from app.session.store import session_store
                deleted = session_store.prune_expired()
                if deleted:
                    logging.getLogger("app.retention").info("Pruned %d expired sessions/statements", deleted)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logging.getLogger("app.retention").warning("Retention worker error: %s", exc)

    worker_task = asyncio.create_task(retention_worker())
    yield
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass

app = FastAPI(
    lifespan=lifespan,
    title="AI Data Analysis Platform API",
    description="AI-powered universal data analysis platform — backend API",
    version="1.0.0",
)


def _security_headers(response, request: Request):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if request.url.scheme == "https": response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


@app.middleware("http")
async def protect_api(request: Request, call_next):
    """Require a live cookie session on every application API except auth endpoints."""
    path = request.url.path
    if os.getenv("AUTH_REQUIRED", "true").lower() not in {"0", "false", "no"} and path.startswith("/api/") and not path.startswith("/api/auth/"):
        from app.routers.auth import current_user
        try:
            user = current_user(request)
        except Exception:
            user = None
        if not user:
            return _security_headers(JSONResponse({"detail": "Sign in required."}, status_code=401), request)
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            from app.routers.auth import require_csrf_for_mutation
            try:
                require_csrf_for_mutation(request)
            except Exception as exc:
                status_code = getattr(exc, "status_code", 403)
                detail = getattr(exc, "detail", "Request verification failed.")
                return _security_headers(JSONResponse({"detail": detail}, status_code=status_code), request)
    response = await call_next(request)
    return _security_headers(response, request)

# ---------------------------------------------------------------------------
# CORS — build the allowed-origins list from env vars only.
# In production (Docker, same-origin) FRONTEND_ORIGIN == the public URL.
# In local dev set FRONTEND_ORIGIN=http://localhost:5173 in backend/.env.
# EXTRA_CORS_ORIGINS can hold a comma-separated list of additional origins
# (useful for staging / preview URLs) e.g. "https://preview.example.com"
# ---------------------------------------------------------------------------
_cors_origins: list[str] = [settings.FRONTEND_ORIGIN.rstrip("/")]
_extra = os.getenv("EXTRA_CORS_ORIGINS", "")
if _extra:
    _cors_origins.extend(o.strip().rstrip("/") for o in _extra.split(",") if o.strip())

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(upload.router, prefix="/api")
app.include_router(results.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(analyze.router, prefix="/api")
app.include_router(auth.router, prefix="/api")


# ---------------------------------------------------------------------------
# Root and Health check
# ---------------------------------------------------------------------------
@app.get("/", tags=["root"])
async def root():
    """Root endpoint providing service metadata, system status, and links to documentation."""
    from app.session.store import check_database_health
    return {
        "name": "AI Data Analysis Platform API",
        "version": "1.0.0",
        "status": "operational",
        "documentation": "/docs",
        "health": "/health",
        "api_prefix": "/api",
        "ai_enabled": settings.ai_enabled,
        "database": check_database_health(),
    }


@app.get("/health", tags=["health"])
@app.get("/api/health", tags=["health"])
async def health_check():
    """Liveness probe — returns status, AI status, and database connectivity."""
    from app.session.store import check_database_health
    db = check_database_health()
    status = "ok"
    status_code = 200
    require_mongo = os.getenv("REQUIRE_MONGODB", "").strip().lower() in ("true", "1", "yes") or os.getenv("ENV", "").strip().lower() == "production"
    if (db.get("configured") and not db.get("connected")) or (require_mongo and not db.get("connected")):
        status = "degraded"
        status_code = 503
    return JSONResponse({
        "status": status,
        "ai_enabled": settings.ai_enabled,
        "model": settings.GROQ_MODEL if settings.ai_enabled else None,
        "database": db,
    }, status_code=status_code)


# ---------------------------------------------------------------------------
# Serve built frontend static files in production
# Works for both:
#   - Docker layout:  WORKDIR=/app, frontend built to /app/static
#   - Local dev:      uvicorn run from backend/, frontend built to ../../frontend/dist
# ---------------------------------------------------------------------------
_here = os.path.dirname(os.path.abspath(__file__))
_static_candidates = [
    os.path.join(_here, "..", "static"),                    # Docker: /app/static
    os.path.join(_here, "..", "..", "frontend", "dist"),    # local dev: frontend/dist
]
for _static_dir in _static_candidates:
    if os.path.isdir(_static_dir):
        app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")
        break
