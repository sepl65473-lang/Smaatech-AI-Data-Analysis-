"""Real-browser visual and login-state checks at the release viewports."""
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = os.getenv("E2E_FRONTEND_URL", "http://127.0.0.1:5174")
CHROMIUM = Path(os.getenv("PLAYWRIGHT_CHROMIUM_EXE", r"C:\Users\DELL\AppData\Local\ms-playwright\chromium-1243\chrome-win64\chrome.exe"))
SCREENSHOTS = Path(os.environ.get("E2E_SCREENSHOTS_DIR", ROOT / "DOCS" / "screenshots"))


def test_login_viewports_errors_forgot_password_and_real_login(ensure_e2e_servers):
    assert CHROMIUM.is_file()
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=str(CHROMIUM), args=["--disable-crashpad", "--disable-breakpad"])
        context = browser.new_context(viewport={"width": 1680, "height": 860})
        page = context.new_page()
        runtime_errors = []
        page.on("pageerror", lambda error: runtime_errors.append(str(error)))
        try:
            page.goto(FRONTEND, wait_until="domcontentloaded")
            page.get_by_role("heading", name="Welcome Back").wait_for(timeout=30_000)
            assert page.get_by_role("alert").count() == 0
            preview = page.get_by_label("Financial analytics benchmark preview")
            assert preview.is_visible()
            assert preview.locator("svg.board-chart-svg").evaluate("""svg => {
              const box = svg.getBoundingClientRect();
              return box.width > 0 && box.height > 0 && svg.querySelectorAll('path, circle, line').length >= 4;
            }""")

            viewports = [(1920, 1080), (1680, 1050), (1366, 768), (1024, 768), (390, 844), (1672, 862)]
            for width, height in viewports:
                page.set_viewport_size({"width": width, "height": height})
                page.wait_for_timeout(100)
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), f"Horizontal overflow at {width}x{height}"
                assert page.locator(".login-card").is_visible()
                assert page.get_by_role("alert").count() == 0, f"Initial error at {width}x{height}"
                page.screenshot(path=str(SCREENSHOTS / f"login_{width}x{height}.png"), full_page=True)

            page.set_viewport_size({"width": 1680, "height": 860})
            # Bootstrap the isolated test administrator, or accept an already bootstrapped test store.
            bootstrap_status = page.evaluate("""async () => {
              const csrfResponse = await fetch('/api/auth/csrf');
              const { csrf_token } = await csrfResponse.json();
              const response = await fetch('/api/auth/bootstrap', {
                method: 'POST', headers: { 'X-CSRF-Token': csrf_token }
              });
              return response.status;
            }""")
            assert bootstrap_status in (200, 409)

            page.get_by_label("User Name / Email").fill(os.environ["AUTH_ADMIN_EMAIL"])
            page.get_by_label("Password", exact=True).fill("Wrong-Visual-Test!2026")
            page.get_by_role("button", name="Login", exact=True).click()
            error = page.get_by_role("alert")
            error.wait_for(timeout=10_000)
            assert "Invalid email or password" in error.inner_text()

            page.get_by_role("button", name="Forgot Password?").click()
            page.get_by_role("heading", name="Reset Password").wait_for()
            page.get_by_label("Registered Email").fill(os.environ["AUTH_ADMIN_EMAIL"])
            page.get_by_role("button", name="Send recovery code").click()
            recovery_error = page.get_by_role("alert")
            recovery_error.wait_for(timeout=10_000)
            assert "temporarily unavailable" in recovery_error.inner_text().lower()
            page.get_by_role("button", name="Back to sign in").click()

            page.get_by_label("User Name / Email").fill(os.environ["AUTH_ADMIN_EMAIL"])
            page.get_by_label("Password", exact=True).fill(os.environ["AUTH_ADMIN_PASSWORD"])
            page.get_by_role("button", name="Login", exact=True).click()
            page.get_by_text("Drag & drop your bank statement here", exact=False).wait_for(timeout=30_000)
            assert not runtime_errors, runtime_errors
        finally:
            context.close()
            browser.close()
