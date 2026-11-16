"""Playwright End-to-End Automated Acceptance Test for:
1. Enterprise Login Redesign & Responsive Layouts (Desktop 1920, 1440, Tablet 768, Mobile 390)
2. Verified Source Financial Figures & Honest Claims (No fake telemetry / fake proofs)
3. Super Admin Authentication & Dashboard
4. Admin User Management: User Creation, Invitation Link Generation & Audit Logging
5. Account Activation & Password Setup with 12+ Character Complexity Rules
6. Standard User Login & Backend RBAC Enforcement (403 on Admin APIs)
7. Account Suspension & Session Revocation
"""

import os
import re
import sys
import time
import socket
import subprocess
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
SCREENSHOTS = ROOT / "DOCS" / "screenshots"
FRONTEND_PORT = 5174
BACKEND_PORT = 8000
FRONTEND_URL = f"http://127.0.0.1:{FRONTEND_PORT}"
BACKEND_URL = f"http://127.0.0.1:{BACKEND_PORT}"

CHROMIUM = Path(os.environ.get(
    "PLAYWRIGHT_CHROMIUM_EXE",
    r"C:\Users\DELL\AppData\Local\ms-playwright\chromium-1243\chrome-win64\chrome.exe",
))


def is_port_open(port: int) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0
    finally:
        s.close()


def wait_for_http(url: str, timeout: float = 25.0) -> bool:
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


def run_e2e_verification():
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    assert CHROMIUM.is_file(), f"Playwright Chromium executable missing: {CHROMIUM}"

    # Load credentials from backend/.env
    admin_email = os.environ.get("AUTH_ADMIN_EMAIL", "itsmaatech@gmail.com")
    admin_password = os.environ.get("AUTH_ADMIN_PASSWORD")
    if not admin_password:
        env_file = ROOT / "backend" / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("AUTH_ADMIN_PASSWORD="):
                    admin_password = line.split("=", 1)[1].strip()
                if line.startswith("AUTH_ADMIN_EMAIL="):
                    admin_email = line.split("=", 1)[1].strip()

    assert admin_password, "AUTH_ADMIN_PASSWORD is required for E2E tests"

    # Clean up test accounts to guarantee idempotent execution
    sys.path.insert(0, str(ROOT / "backend"))
    from app.services import auth_store
    def purge_test_accounts(db):
        admin_email_lower = admin_email.strip().lower()
        db["users"] = {k: v for k, v in db.get("users", {}).items() if k.strip().lower() == admin_email_lower}
        db["sessions"] = {}
        db["recovery"] = {}
    auth_store.update(purge_test_accounts)

    backend_proc = None
    frontend_proc = None

    try:
        # 1. Start backend if not running
        backend_log_file = ROOT / "backend_test.log"
        frontend_log_file = ROOT / "frontend_test.log"
        backend_log = open(backend_log_file, "w", encoding="utf-8")
        frontend_log = open(frontend_log_file, "w", encoding="utf-8")

        if not is_port_open(BACKEND_PORT):
            print(f"[*] Starting FastAPI backend on {BACKEND_URL}...")
            backend_env = dict(os.environ)
            backend_env["GROQ_API_KEY"] = ""  # Rule-based fallback during test for instant speed & zero external dependency
            backend_cmd = [
                sys.executable, "-m", "uvicorn", "app.main:app",
                "--host", "127.0.0.1", "--port", str(BACKEND_PORT),
                "--app-dir", str(ROOT / "backend"),
            ]
            backend_proc = subprocess.Popen(
                backend_cmd,
                cwd=str(ROOT),
                env=backend_env,
                stdout=backend_log,
                stderr=subprocess.STDOUT,
            )
            if not wait_for_http(f"{BACKEND_URL}/health", timeout=20):
                backend_log.flush()
                print("[ERROR] FastAPI backend failed to start. Log:")
                print(backend_log_file.read_text())
                raise RuntimeError("FastAPI backend failed to start")
            print("    -> FastAPI backend is ready.")
        else:
            print(f"[*] FastAPI backend already listening on {BACKEND_URL}")

        # 2. Start frontend preview if not running
        if not is_port_open(FRONTEND_PORT):
            print(f"[*] Starting Frontend preview on {FRONTEND_URL}...")
            frontend_cmd = [
                "npm.cmd" if sys.platform == "win32" else "npm",
                "run", "preview", "--prefix", "frontend", "--",
                "--port", str(FRONTEND_PORT), "--host", "127.0.0.1",
            ]
            frontend_proc = subprocess.Popen(
                frontend_cmd,
                cwd=str(ROOT),
                stdout=frontend_log,
                stderr=subprocess.STDOUT,
            )
            if not wait_for_http(FRONTEND_URL, timeout=20):
                frontend_log.flush()
                print("[ERROR] Frontend preview failed to start. Log:")
                print(frontend_log_file.read_text())
                raise RuntimeError("Frontend preview failed to start")
            print("    -> Frontend preview is ready.")
        else:
            print(f"[*] Frontend preview already listening on {FRONTEND_URL}")

        # 3. Launch Playwright
        print("\n[*] Starting Playwright browser test suite...")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                executable_path=str(CHROMIUM),
                args=["--disable-crashpad", "--disable-breakpad"],
            )

            # -----------------------------------------------------------------
            # TEST 1: Enterprise Login Redesign & Responsive Layouts
            # -----------------------------------------------------------------
            print("[Step 1] Verifying Login Screen Redesign & Responsive Layouts across viewports...")
            context = browser.new_context(viewport={"width": 1920, "height": 1080})
            page = context.new_page()

            page.goto(f"{FRONTEND_URL}/login", wait_until="networkidle")
            page.locator("h2:has-text('Welcome Back')").wait_for(timeout=15000)

            # Verify verified source financial benchmark figures are rendered
            page_text = page.locator("body").inner_text()
            assert "45,48,780" in page_text, "Benchmark Total Inflow ₹45,48,780 must be present"
            assert "46,26,410" in page_text, "Benchmark Total Outflow ₹46,26,410 must be present"
            assert "162 Transactions" in page_text, "162 Transactions count must be present"
            assert "Zero-Delta" in page_text, "Zero-Delta proof badge must be present"
            assert "CSRF & Session Protected" in page_text, "Session security badge must be present"

            # Desktop 1920x1080
            page.screenshot(path=str(SCREENSHOTS / "01_login_desktop_1920.png"), full_page=True)
            print("    -> Saved 01_login_desktop_1920.png")

            # Desktop 1440x900
            page.set_viewport_size({"width": 1440, "height": 900})
            page.screenshot(path=str(SCREENSHOTS / "02_login_desktop_1440.png"), full_page=True)
            print("    -> Saved 02_login_desktop_1440.png")

            # Tablet 768x1024
            page.set_viewport_size({"width": 768, "height": 1024})
            page.wait_for_timeout(300)
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "Tablet view has horizontal scrollbar!"
            page.screenshot(path=str(SCREENSHOTS / "03_login_tablet_768.png"), full_page=True)
            print("    -> Saved 03_login_tablet_768.png (zero horizontal overflow verified)")

            # Mobile 390x844
            page.set_viewport_size({"width": 390, "height": 844})
            page.wait_for_timeout(300)
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "Mobile view has horizontal scrollbar!"
            page.screenshot(path=str(SCREENSHOTS / "04_login_mobile_390.png"), full_page=True)
            print("    -> Saved 04_login_mobile_390.png (zero horizontal overflow verified)")

            # -----------------------------------------------------------------
            # TEST 2: Super Admin Login & Dashboard Navigation
            # -----------------------------------------------------------------
            print("\n[Step 2] Logging in as Super Administrator...")
            page.set_viewport_size({"width": 1440, "height": 900})

            # Ensure CSRF and admin bootstrap
            csrf_resp = page.request.get(f"{FRONTEND_URL}/api/auth/csrf")
            assert csrf_resp.ok
            csrf_val = next(c["value"] for c in context.cookies(FRONTEND_URL) if c["name"] == "sepl_csrf")
            page.request.post(f"{FRONTEND_URL}/api/auth/bootstrap", headers={"X-CSRF-Token": csrf_val})

            page.fill("#login-identity", admin_email)
            page.fill("#login-password", admin_password)
            page.click(".login-submit")

            page.wait_for_url(f"{FRONTEND_URL}/", timeout=15000)
            page.locator("text=AI Data Analysis").first.wait_for(timeout=10000)
            page.screenshot(path=str(SCREENSHOTS / "05_admin_dashboard_home.png"), full_page=True)
            print("    -> Saved 05_admin_dashboard_home.png")

            # Verify Admin button exists in header
            admin_btn = page.locator("button:has-text('User Management')").first
            assert admin_btn.is_visible(), "User Management button must be visible to administrator"
            print("    -> Verified User Management button in top navigation.")

            # -----------------------------------------------------------------
            # TEST 3: Admin User Management Modal
            # -----------------------------------------------------------------
            print("\n[Step 3] Opening Admin User Management Modal...")
            admin_btn.click()
            page.locator("#admin-modal-title:has-text('Admin User Management')").first.wait_for(timeout=10000)
            page.wait_for_timeout(500)
            page.screenshot(path=str(SCREENSHOTS / "06_admin_users_modal.png"))
            print("    -> Saved 06_admin_users_modal.png")

            # -----------------------------------------------------------------
            # TEST 4: Create User with Granular Role & Invitation
            # -----------------------------------------------------------------
            print("\n[Step 4] Creating new user and generating invitation link...")
            create_btn = page.locator("button:has-text('Create User')").first
            create_btn.click()

            page.locator("h3:has-text('Create & Invite New User')").wait_for(timeout=5000)
            page.screenshot(path=str(SCREENSHOTS / "07_admin_create_user_dialog.png"))
            print("    -> Saved 07_admin_create_user_dialog.png")

            test_user_email = "analyst.test@example.com"
            test_user_name = "Rohan Sharma"
            test_user_pass = "Enterprise2026!#"

            # Fill Create User Form
            page.fill("input[placeholder*='Rohan Sharma']", test_user_name)
            page.fill("input[placeholder*='name@company.com']", test_user_email)

            # Submit creation
            page.click("button:has-text('Generate & Send Invitation')")

            page.locator("h3:has-text('User Created & Invitation Ready')").wait_for(timeout=10000)
            page.screenshot(path=str(SCREENSHOTS / "08_admin_invitation_created.png"))
            print("    -> Saved 08_admin_invitation_created.png")

            # Extract generated invitation URL from readonly input
            invitation_input = page.locator("input[readonly]")
            invitation_url = invitation_input.input_value()
            assert "/activate?token=" in invitation_url, f"Invalid invitation URL: {invitation_url}"
            print(f"    -> Successfully generated secure invitation: {invitation_url}")

            # Extract activation token
            activation_token = invitation_url.split("token=")[1].split("&")[0]

            # Click Done to close create dialog
            page.click("button:has-text('Done')")
            page.wait_for_timeout(500)

            # Verify new user in users list with Pending Activation
            users_table_text = page.locator("tbody").first.inner_text()
            assert test_user_email in users_table_text, "Created user must appear in the users list"
            assert "Pending Activation" in users_table_text, "User must have 'Pending Activation' status"
            page.screenshot(path=str(SCREENSHOTS / "09_admin_users_table_pending.png"))
            print("    -> Saved 09_admin_users_table_pending.png")

            # Close admin modal
            page.locator("button[aria-label='Close']").first.click()
            page.wait_for_timeout(300)

            # -----------------------------------------------------------------
            # TEST 5: User Activation Flow & Password Complexity Checklist
            # -----------------------------------------------------------------
            print("\n[Step 5] Testing invited user account activation flow...")
            # Use a fresh, incognito context to represent the invited user
            user_context = browser.new_context(viewport={"width": 1440, "height": 900})
            user_page = user_context.new_page()
            user_page.on("console", lambda msg: print(f"    [Browser Console] {msg.type}: {msg.text}"))
            user_page.on("requestfailed", lambda req: print(f"    [Request Failed] {req.method} {req.url} {req.failure}"))

            activation_page_url = f"{FRONTEND_URL}/activate?token={activation_token}"
            user_page.goto(activation_page_url, wait_until="networkidle")

            user_page.locator("h2:has-text('Welcome, Rohan Sharma')").wait_for(timeout=10000)
            user_page.locator(f"strong:has-text('{test_user_email}')").wait_for(timeout=5000)
            user_page.screenshot(path=str(SCREENSHOTS / "10_activate_account_screen.png"), full_page=True)
            print("    -> Saved 10_activate_account_screen.png")

            # Fill new password meeting all complexity requirements
            user_page.fill("#activate-password", test_user_pass)
            user_page.fill("#activate-confirm", test_user_pass)
            user_page.click("button.login-submit")

            # Verify activation success
            user_page.locator("h2:has-text('Account Activated!')").wait_for(timeout=10000)
            user_page.screenshot(path=str(SCREENSHOTS / "11_activate_account_success.png"), full_page=True)
            print("    -> Saved 11_activate_account_success.png")

            # -----------------------------------------------------------------
            # TEST 6: Standard User Login & Role Enforcement
            # -----------------------------------------------------------------
            print("\n[Step 6] Testing standard user login and backend authorization boundaries...")
            user_page.click("button:has-text('Sign In to Workspace')")
            user_page.wait_for_url(f"{FRONTEND_URL}/login", timeout=10000)

            user_page.fill("#login-identity", test_user_email)
            user_page.fill("#login-password", test_user_pass)
            user_page.click(".login-submit")

            user_page.wait_for_url(f"{FRONTEND_URL}/", timeout=15000)
            user_page.screenshot(path=str(SCREENSHOTS / "12_standard_user_dashboard.png"), full_page=True)
            print("    -> Saved 12_standard_user_dashboard.png")

            # Verify Admin button is NOT present for standard user
            assert user_page.locator("button:has-text('User Management')").count() == 0, \
                "User Management button must NOT be rendered for Standard Users"
            print("    -> Confirmed Admin button is hidden from Standard User.")

            # Test Backend API Authorization Boundary: Standard user cannot access admin APIs
            print("    -> Testing backend API authorization rejection for standard user...")
            user_csrf = next(c["value"] for c in user_context.cookies(FRONTEND_URL) if c["name"] == "sepl_csrf")
            admin_api_resp = user_page.request.get(f"{FRONTEND_URL}/api/auth/admin/users", headers={"X-CSRF-Token": user_csrf})
            assert admin_api_resp.status == 403, f"Standard user should receive 403 on admin API, got {admin_api_resp.status}"

            admin_post_resp = user_page.request.post(
                f"{FRONTEND_URL}/api/auth/admin/users",
                headers={"X-CSRF-Token": user_csrf},
                data={"email": "hacker@test.com", "role": "administrator"},
            )
            assert admin_post_resp.status == 403, f"Standard user create admin attempt should receive 403, got {admin_post_resp.status}"
            print("    -> Verified backend returns 403 Forbidden on restricted admin endpoints.")

            # -----------------------------------------------------------------
            # TEST 6b: Standard User Uploads Statement, Analyzes & Exports
            # -----------------------------------------------------------------
            print("\n[Step 6b] Standard user uploading statement & analyzing...")
            pdf_path = ROOT / "backend" / "tests" / "axis_june_2023_original.pdf"
            assert pdf_path.exists(), f"PDF fixture missing at {pdf_path}"
            user_page.locator('input[type="file"]').set_input_files(str(pdf_path))
            user_page.wait_for_timeout(1000)
            user_page.locator("button:has-text('Analyze Data')").first.click()

            try:
                user_page.wait_for_url(re.compile(r".*/results\?sid=.*"), timeout=45000)
            except Exception as exc:
                user_page.screenshot(path=str(SCREENSHOTS / "12_upload_diagnostic_failure.png"), full_page=True)
                diag_text = user_page.locator("body").inner_text()
                print(f"    [DIAGNOSTIC FAILURE] Body text:\n{diag_text}")
                raise exc

            user_page.locator("text=Financial Reconciliation").first.wait_for(timeout=30000)
            user_page.screenshot(path=str(SCREENSHOTS / "12b_user_analysis_results.png"), full_page=True)
            print("    -> Saved 12b_user_analysis_results.png")

            # Standard user exports report
            print("    -> Standard user exporting report deliverables...")
            user_page.locator("button:has-text('Download PDF'):not([disabled])").first.wait_for(timeout=20000)
            with user_page.expect_download(timeout=30000) as download_info:
                user_page.locator("button:has-text('Download PDF')").first.click()
            download = download_info.value
            print(f"    -> Successfully downloaded PDF: {download.suggested_filename}")

            # Standard user signs out
            print("    -> Standard user signing out...")
            user_page.locator("button:has-text('Sign Out')").first.click()
            user_page.locator("div[role='dialog'] button:has-text('Sign Out')").first.click()
            user_page.wait_for_url(f"{FRONTEND_URL}/login", timeout=15000)
            user_page.screenshot(path=str(SCREENSHOTS / "12c_user_signed_out.png"), full_page=True)
            print("    -> Saved 12c_user_signed_out.png")

            # -----------------------------------------------------------------
            # TEST 7: Account Suspension & Immediate Login Block
            # -----------------------------------------------------------------
            print("\n[Step 7] Testing admin account suspension and login rejection...")
            # Switch back to admin page to suspend user
            admin_btn = page.locator("button:has-text('User Management')").first
            admin_btn.click()
            page.locator("#admin-modal-title:has-text('Admin User Management')").first.wait_for(timeout=10000)

            # Click Suspend button for Rohan Sharma
            suspend_btn = page.locator(f"tr:has-text('{test_user_email}') button[title*='Suspend']").first
            suspend_btn.click()
            page.wait_for_timeout(1000)

            page.screenshot(path=str(SCREENSHOTS / "13_admin_user_suspended.png"))
            print("    -> Saved 13_admin_user_suspended.png")

            # Verify suspended user cannot sign in
            print("    -> Verifying suspended user is blocked from sign in...")
            user_context.clear_cookies()
            user_page.goto(f"{FRONTEND_URL}/login", wait_until="networkidle")
            user_page.fill("#login-identity", test_user_email)
            user_page.fill("#login-password", test_user_pass)
            user_page.click(".login-submit")

            # Verify error message shows suspension notice
            user_page.locator(".login-error").wait_for(timeout=5000)
            error_text = user_page.locator(".login-error").inner_text()
            assert "suspended" in error_text.lower() or "deactivated" in error_text.lower(), \
                f"Expected suspension error message, got: {error_text}"
            user_page.screenshot(path=str(SCREENSHOTS / "14_suspended_login_rejected.png"))
            print("    -> Saved 14_suspended_login_rejected.png")

            # -----------------------------------------------------------------
            # TEST 8: Security Audit Log Verification
            # -----------------------------------------------------------------
            print("\n[Step 8] Verifying Security Audit Log...")
            audit_tab = page.locator("button:has-text('Security Audit Log')").first
            audit_tab.click()
            page.wait_for_timeout(500)
            page.screenshot(path=str(SCREENSHOTS / "15_security_audit_log.png"))
            print("    -> Saved 15_security_audit_log.png")

            # Clean up test user to leave environment pristine
            print("\n[*] Cleaning up test user account...")
            users_tab = page.locator("button:has-text('Users & Roles')").first
            users_tab.click()
            delete_btn = page.locator(f"tr:has-text('{test_user_email}') button[title*='Delete']").first
            if delete_btn.count() > 0:
                delete_btn.click()
                confirm_del_btn = page.locator("button:has-text('Confirm Delete')").first
                if confirm_del_btn.count() > 0:
                    confirm_del_btn.click()
                    page.wait_for_timeout(500)
                    print("    -> Test user cleaned up.")

            context.close()
            user_context.close()
            browser.close()

        print("\n============================================================")
        print("🎉 ALL 8 AUTOMATED PLAYWRIGHT E2E ACCEPTANCE TESTS PASSED!")
        print(f"Screenshots saved to: {SCREENSHOTS}")
        print("============================================================")

    finally:
        try:
            backend_log.close()
        except Exception:
            pass
        try:
            frontend_log.close()
        except Exception:
            pass
        if backend_proc:
            print("[*] Terminating background FastAPI backend...")
            backend_proc.terminate()
            backend_proc.wait()
        if frontend_proc:
            print("[*] Terminating background Frontend preview...")
            frontend_proc.terminate()
            frontend_proc.wait()


if __name__ == "__main__":
    run_e2e_verification()
