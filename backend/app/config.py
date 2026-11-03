import os
import logging
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)


class Settings:
    # ── Groq AI ───────────────────────────────────────────────────────────────
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    # ── Session ───────────────────────────────────────────────────────────────
    SESSION_TTL_MINUTES: int = int(os.getenv("SESSION_TTL_MINUTES", "60"))

    # ── Upload ────────────────────────────────────────────────────────────────
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))

    @property
    def MAX_UPLOAD_SIZE_BYTES(self) -> int:
        """Computed from MAX_UPLOAD_SIZE_MB so it always reflects the live value."""
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Primary frontend origin (same-origin in Docker, Vite URL in local dev)
    FRONTEND_ORIGIN: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    # Optional comma-separated extra origins (staging / preview URLs)
    EXTRA_CORS_ORIGINS: str = os.getenv("EXTRA_CORS_ORIGINS", "")

    # ── Server ────────────────────────────────────────────────────────────────
    PORT: int = int(os.getenv("PORT", "8000"))

    @property
    def ai_enabled(self) -> bool:
        """Returns True if a Groq API key is configured."""
        return bool(self.GROQ_API_KEY)


settings = Settings()


# ---------------------------------------------------------------------------
# Groq client — initialised once at import time, reused across requests
# ---------------------------------------------------------------------------
_groq_client = None


def get_groq_client():
    """
    Return a shared Groq client instance.
    Returns None if GROQ_API_KEY is not set (graceful degradation).
    """
    global _groq_client
    if _groq_client is not None:
        return _groq_client
    if not settings.GROQ_API_KEY:
        return None
    try:
        from groq import Groq
        _groq_client = Groq(api_key=settings.GROQ_API_KEY)
        log.info("Groq client initialised (model: %s)", settings.GROQ_MODEL)
    except Exception as exc:
        log.warning("Could not initialise Groq client: %s", exc)
        _groq_client = None
    return _groq_client
