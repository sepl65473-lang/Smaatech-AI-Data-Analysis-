"""The legacy business-logic API tests predate authentication and test those APIs directly.

The dedicated authentication tests explicitly turn enforcement back on. This setting is
pytest-only; the application defaults to requiring auth unless an operator overrides it.
"""
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
import pytest

os.environ.setdefault("AUTH_REQUIRED", "false")

ROOT = Path(__file__).resolve().parents[2]
FRONTEND_PORT = 5174
BACKEND_PORT = 8000
FRONTEND_URL = f"http://127.0.0.1:{FRONTEND_PORT}"
BACKEND_URL = f"http://127.0.0.1:{BACKEND_PORT}"


def _is_port_open(port: int) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0
    finally:
        s.close()


def _wait_for_http(url: str, timeout: float = 25.0) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "HealthCheck/1.0"})
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status in (200, 304):
                    return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


@pytest.fixture(scope="session")
def ensure_e2e_servers():
    """Ensure both FastAPI backend and Vite frontend preview servers are running for browser tests."""
    os.environ.setdefault("AUTH_ADMIN_EMAIL", "itsmaatech@gmail.com")
    os.environ.setdefault("AUTH_ADMIN_PASSWORD", "SeplAdmin@2026")
    os.environ.setdefault("E2E_FRONTEND_URL", FRONTEND_URL)

    backend_proc = None
    frontend_proc = None

    try:
        # 1. Start FastAPI backend on port 8000 if not open
        if not _is_port_open(BACKEND_PORT):
            backend_env = dict(os.environ)
            backend_env["AUTH_REQUIRED"] = "true"
            backend_env["GROQ_API_KEY"] = ""  # rule-based fallback for instant test runs
            backend_proc = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(BACKEND_PORT)],
                cwd=str(ROOT / "backend"),
                env=backend_env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if not _wait_for_http(f"{BACKEND_URL}/health", timeout=15.0):
                if backend_proc:
                    backend_proc.kill()
                    backend_proc = None

        # 2. Start Vite preview on port 5174 if not open
        if not _is_port_open(FRONTEND_PORT):
            frontend_env = dict(os.environ)
            frontend_env["API_PROXY_TARGET"] = BACKEND_URL
            frontend_cmd = "npx.cmd vite preview --port 5174 --host 127.0.0.1" if sys.platform == "win32" else "npx vite preview --port 5174 --host 127.0.0.1"
            frontend_proc = subprocess.Popen(
                frontend_cmd,
                shell=True,
                cwd=str(ROOT / "frontend"),
                env=frontend_env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if not _wait_for_http(FRONTEND_URL, timeout=20.0):
                if frontend_proc:
                    frontend_proc.kill()
                    frontend_proc = None
    except Exception:
        pass

    yield

    if frontend_proc:
        frontend_proc.terminate()
        try:
            frontend_proc.wait(timeout=3)
        except Exception:
            frontend_proc.kill()
    if backend_proc:
        backend_proc.terminate()
        try:
            backend_proc.wait(timeout=3)
        except Exception:
            backend_proc.kill()

