"""Playwright end-to-end acceptance flow against the local Vite + FastAPI app."""

import os
import re
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[2]
STATEMENT = Path(os.environ.get("E2E_FINANCIAL_STATEMENT_PATH", Path(__file__).parent / "axis_june_2023_original.pdf"))
SCREENSHOTS = Path(os.environ.get("E2E_SCREENSHOTS_DIR", ROOT / "DOCS" / "screenshots"))
DOWNLOADS = Path(os.environ.get("E2E_DOWNLOADS_DIR", ROOT / "scratch" / "release_e2e_downloads"))
FRONTEND = os.environ.get("E2E_FRONTEND_URL", "http://127.0.0.1:5174")
CHROMIUM = Path(os.environ.get(
    "PLAYWRIGHT_CHROMIUM_EXE",
    r"C:\Users\DELL\AppData\Local\ms-playwright\chromium-1243\chrome-win64\chrome.exe",
))


def test_full_bank_statement_release_flow(ensure_e2e_servers):
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    assert CHROMIUM.is_file(), f"Playwright Chromium executable missing: {CHROMIUM}"
    session_id = None
    console_errors = []
    completed_downloads = {}

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=str(CHROMIUM),
            args=["--disable-crashpad", "--disable-breakpad"],
        )
        context = browser.new_context(accept_downloads=True, viewport={"width": 1440, "height": 1000})
        page = context.new_page()
        page.on("pageerror", lambda error: console_errors.append(str(error)))

        try:
            page.goto(FRONTEND, wait_until="domcontentloaded")
            page.get_by_role("heading", name="Welcome Back").wait_for(timeout=30_000)
            page.screenshot(path=str(SCREENSHOTS / "release_login.png"), full_page=True)
            page.set_viewport_size({"width": 390, "height": 844})
            page.screenshot(path=str(SCREENSHOTS / "release_login_mobile.png"), full_page=True)
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
            page.set_viewport_size({"width": 1440, "height": 1000})
            csrf_response = page.request.get(f"{FRONTEND}/api/auth/csrf")
            assert csrf_response.ok
            csrf_value = next(cookie["value"] for cookie in context.cookies(FRONTEND) if cookie["name"] == "sepl_csrf")
            bootstrap_response = page.request.post(f"{FRONTEND}/api/auth/bootstrap", headers={"X-CSRF-Token": csrf_value})
            assert bootstrap_response.status in (200, 409), bootstrap_response.text()
            page.get_by_label("User Name / Email").fill(os.environ["AUTH_ADMIN_EMAIL"])
            page.get_by_label("Password", exact=True).fill(os.environ["AUTH_ADMIN_PASSWORD"])
            page.get_by_role("button", name="Login", exact=True).click()
            page.get_by_text("Drag & drop your bank statement here", exact=False).wait_for(timeout=30_000)
            page.screenshot(path=str(SCREENSHOTS / "release_home.png"), full_page=True)
            page.locator('input[type="file"]').set_input_files(str(STATEMENT))
            page.get_by_role("button", name=re.compile("Analyze Data", re.I)).click()
            page.wait_for_url(re.compile(r".*/results\?sid=.*"), timeout=120_000)
            page.get_by_text("Financial Reconciliation", exact=False).wait_for(timeout=30_000)
            body = page.locator("body").inner_text()
            assert "162" in body
            assert "46,26,410" in body
            assert "45,48,780" in body
            session_id = page.url.split("sid=", 1)[1].split("&", 1)[0]
            page.screenshot(path=str(SCREENSHOTS / "release_dashboard.png"), full_page=True)

            reconciliation = page.locator("#reconciliation-audit")
            reconciliation.scroll_into_view_if_needed()
            assert "38,285.26" in reconciliation.inner_text()
            assert "0.00" in reconciliation.inner_text()
            reconciliation.screenshot(path=str(SCREENSHOTS / "release_reconciliation.png"))

            category_filter = page.locator('label:has-text("Category") + select').first
            category_filter.select_option(label="Food")
            page.wait_for_timeout(300)
            assert category_filter.input_value() == "Food"
            category_filter.select_option(label="All")

            page.get_by_role("button", name="Category Intelligence").click()
            modal = page.get_by_text("Category Intelligence & Classification Review", exact=False)
            modal.wait_for()
            page.screenshot(path=str(SCREENSHOTS / "release_review_queue.png"), full_page=True)
            assert "to review" in page.locator("body").inner_text().lower()
            page.get_by_role("combobox").last.select_option(label="Healthcare")
            page.get_by_role("button", name="Confirm Category Mapping").click()
            page.get_by_text("Successfully mapped", exact=False).wait_for(timeout=20_000)
            page.wait_for_timeout(500)
            page.screenshot(path=str(SCREENSHOTS / "release_mapping_confirmed.png"))
            page.get_by_role("button", name="Done Reviewing").click()
            page.get_by_text("Category Analysis", exact=False).wait_for()
            assert page.get_by_text("Healthcare", exact=True).count() > 0

            api_result = page.request.get(f"{FRONTEND}/api/results/{session_id}")
            assert api_result.status == 200
            result = api_result.json()
            confirmed = [t for t in result["transactions"] if t["classification_source"] == "user"]
            assert confirmed
            assert all(t["confidence_score"] == 1.0 for t in confirmed)
            assert result["metrics"]["total_spend"] == 4626410.0
            assert result["metrics"]["reconciliation_delta"] == 0.0

            # Exercise each file download through the rendered UI and retain
            # the bytes for integrity verification by the acceptance runner.
            with page.expect_download(timeout=30_000) as download_info:
                page.get_by_role("button", name=re.compile(r"Export Filtered", re.I)).click()
            csv_download = download_info.value
            csv_target = DOWNLOADS / csv_download.suggested_filename
            csv_download.save_as(str(csv_target))
            completed_downloads["csv"] = {"path": str(csv_target), "bytes": csv_target.stat().st_size}
            for name, locator in [
                ("pdf", page.get_by_role("button", name="Download PDF")),
                ("xlsx", page.get_by_role("button", name="Download .xlsx")),
                ("html", page.get_by_role("button", name="Download HTML")),
                ("zip", page.get_by_role("button", name="Download .zip")),
            ]:
                with page.expect_download(timeout=30_000) as download_info:
                    locator.click()
                download = download_info.value
                target = DOWNLOADS / download.suggested_filename
                download.save_as(str(target))
                completed_downloads[name] = {"path": str(target), "bytes": target.stat().st_size}

            assert not console_errors, f"Browser runtime errors: {console_errors}"
            assert set(completed_downloads) == {"csv", "pdf", "xlsx", "html", "zip"}
            print({"session_id": session_id, "url": page.url,
                   "downloaded": completed_downloads, "console_errors": console_errors,
                   "screenshots": [str(p) for p in sorted(SCREENSHOTS.glob("release_*.png"))]})
        finally:
            context.close()
            browser.close()
            if session_id:
                from app.session.store import session_store
                session_store.delete(session_id)
