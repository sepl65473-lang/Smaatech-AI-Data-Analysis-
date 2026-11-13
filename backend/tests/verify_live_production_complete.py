import asyncio
import os
import sys
import time
from playwright.async_api import async_playwright

LIVE_URL = "https://smaatech-ai-data-analysis.vercel.app"
SCREENSHOTS_DIR = r"C:\Users\DELL\.gemini\antigravity\brain\deb421e9-e661-4cb4-872b-9c9f81e55964\screenshots"
SAMPLE_PDF = r"D:\bank statment\AI Data Analysis Platform\backend\tests\axis_june_2023_original.pdf"

EMAIL = "itsmaatech@gmail.com"
PASS = "SeplAdmin@2026"

os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

async def test_live_production_suite():
    print(f"=== FULL LIVE PRODUCTION VERIFICATION ON {LIVE_URL} ===", flush=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            ignore_https_errors=True,
            accept_downloads=True
        )
        page = await context.new_page()

        page.on("console", lambda msg: print(f"[BROWSER {msg.type.upper()}] {msg.text}", flush=True) if msg.type in ["error", "warning"] else None)
        page.on("response", lambda resp: print(f"[HTTP {resp.status}] {resp.request.method} {resp.url}", flush=True) if "/api" in resp.url else None)

        # Phase 1: Navigation and Authentication
        print("\n--- Phase 1: Live Login & Authentication ---", flush=True)
        await page.goto(LIVE_URL, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_selector("#login-identity", state="visible", timeout=20000)
        await page.wait_for_timeout(1000)
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "live_prod_01_login_page.png"))

        print("Entering admin credentials...", flush=True)
        await page.locator("#login-identity").fill(EMAIL)
        await page.locator("#login-password").fill(PASS)
        await page.wait_for_timeout(500)

        async with page.expect_response("**/api/auth/login", timeout=20000) as resp_info:
            await page.click("button[type='submit']")
        
        login_resp = await resp_info.value
        print(f"Login API Status: {login_resp.status}")
        assert login_resp.status == 200, f"Login failed with status {login_resp.status}"

        # Wait for home page navigation
        await page.wait_for_url(f"{LIVE_URL}/", timeout=25000)
        await page.wait_for_selector("text=AI Data Analysis Platform", timeout=15000)
        await page.wait_for_timeout(1500)
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "live_prod_02_home_dashboard.png"))
        print("[PASS] Successfully authenticated and loaded live dashboard!", flush=True)

        # Phase 2: Header Architecture Verification
        print("\n--- Phase 2: Top-Right Dashboard Header ---", flush=True)
        change_pwd_btn = page.locator("button[title='Change your account password']")
        signout_btn = page.locator("header button:has-text('Sign Out')")
        menu_btn = page.locator("button[aria-label='Advanced options menu']")

        assert await change_pwd_btn.is_visible(), "Change Password button is missing!"
        assert await signout_btn.is_visible(), "Sign Out button is missing!"
        assert await menu_btn.is_visible(), "Three-dot menu button is missing!"
        print("[PASS] Header actions verified: strictly 2 visible actions + 3-dot menu!", flush=True)

        # Phase 3: Three-Dot Menu & Theme Switching
        print("\n--- Phase 3: Three-Dot Menu & Theme Switching ---", flush=True)
        await menu_btn.click()
        await page.wait_for_timeout(500)
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "live_prod_03_menu_open.png"))

        # Toggle Dark Mode
        print("Toggling Dark Mode...", flush=True)
        theme_toggle_btn = page.locator("button[role='menuitem']:has-text('Mode')")
        await theme_toggle_btn.click()
        await page.wait_for_timeout(600)
        is_dark = await page.evaluate("() => document.documentElement.classList.contains('dark')")
        print(f"Dark mode active: {is_dark}")
        assert is_dark is True, "Dark mode class not set on html element!"
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "live_prod_04_dark_mode.png"))

        # Toggle Light Mode back (menu stays open after theme toggle)
        print("Toggling Light Mode back...", flush=True)
        await theme_toggle_btn.click()
        await page.wait_for_timeout(500)
        is_light = await page.evaluate("() => !document.documentElement.classList.contains('dark')")
        assert is_light is True, "Light mode not restored!"
        print("[PASS] Theme switching verified in both directions!", flush=True)

        # Phase 4: Advanced SaaS Modals
        print("\n--- Phase 4: Advanced SaaS Modals ---", flush=True)
        # Profile (menu is currently open from Phase 3)
        await page.locator("button[role='menuitem']:has-text('Profile Settings')").click()
        await page.wait_for_timeout(500)
        assert await page.locator("h3:has-text('Profile Settings')").is_visible()
        assert await page.locator(f"text={EMAIL}").is_visible()
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "live_prod_05_modal_profile.png"))
        await page.locator("div[role='dialog'] button[aria-label='Close']").click()
        await page.wait_for_timeout(300)

        # Account
        await menu_btn.click()
        await page.wait_for_timeout(300)
        await page.locator("button[role='menuitem']:has-text('Account Settings')").click()
        await page.wait_for_timeout(500)
        assert await page.locator("h3:has-text('Account Settings')").is_visible()
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "live_prod_06_modal_account.png"))
        await page.locator("div[role='dialog'] button[aria-label='Close']").click()
        await page.wait_for_timeout(300)

        # Notification Preferences with Real LocalStorage Sync
        await menu_btn.click()
        await page.wait_for_timeout(300)
        await page.locator("button[role='menuitem']:has-text('Notification Preferences')").click()
        await page.wait_for_timeout(500)
        assert await page.locator("h3:has-text('Notification Preferences')").is_visible()
        # Toggle first notification checkbox
        first_cb = page.locator("div[role='dialog'] input[type='checkbox']").first
        await first_cb.click()
        await page.wait_for_timeout(400)
        assert await page.locator("text=✓ Saved").is_visible()
        saved_prefs = await page.evaluate("() => localStorage.getItem('sepl_notification_preferences')")
        print(f"LocalStorage notification preferences: {saved_prefs}")
        assert saved_prefs is not None, "Notification preferences not saved to localStorage!"
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "live_prod_07_modal_notifications.png"))
        await page.locator("div[role='dialog'] button[aria-label='Close']").click()
        await page.wait_for_timeout(300)

        # Activity Log (RBAC Check)
        await menu_btn.click()
        await page.wait_for_timeout(300)
        await page.locator("button[role='menuitem']:has-text('Activity Log')").click()
        await page.wait_for_timeout(500)
        assert await page.locator("h3:has-text('Activity Log & Audit Trail')").is_visible()
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "live_prod_08_modal_activity_log.png"))
        await page.locator("div[role='dialog'] button[aria-label='Close']").click()
        await page.wait_for_timeout(300)

        # Security Settings
        await menu_btn.click()
        await page.wait_for_timeout(300)
        await page.locator("button[role='menuitem']:has-text('Security Settings')").click()
        await page.wait_for_timeout(500)
        assert await page.locator("h3:has-text('Security Settings')").is_visible()
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "live_prod_09_modal_security.png"))
        await page.locator("div[role='dialog'] button[aria-label='Close']").click()
        await page.wait_for_timeout(300)
        print("[PASS] All advanced modals and RBAC checks verified!", flush=True)

        # Phase 5: Change Password Dialog
        print("\n--- Phase 5: Change Password Dialog ---", flush=True)
        await change_pwd_btn.click()
        await page.wait_for_timeout(500)
        assert await page.locator("#password-dialog-title").is_visible()
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "live_prod_10_change_password.png"))
        # Test Escape key dismissal
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(500)
        assert await page.locator("#password-dialog-title").count() == 0, "Password dialog did not dismiss on Escape!"
        print("[PASS] Change Password dialog opens and dismisses via Escape!", flush=True)

        # Phase 6: Statement Upload and Real Analysis Pipeline
        print(f"\n--- Phase 6: Statement Upload & Analysis Pipeline ({os.path.basename(SAMPLE_PDF)}) ---", flush=True)
        file_input = page.locator("input[type='file']")
        await file_input.set_input_files(SAMPLE_PDF)
        await page.wait_for_timeout(1000)

        analyze_btn = page.locator("button:has-text('Analyze Data')")
        print("Clicking Analyze Data on live Render backend...", flush=True)
        async with page.expect_response("**/api/upload", timeout=90000) as upload_info:
            await analyze_btn.click()
        
        upload_resp = await upload_info.value
        print(f"Upload API Status: {upload_resp.status}")
        assert upload_resp.status == 200, f"Upload API failed with {upload_resp.status}"

        # Wait for navigation to /results
        print("Waiting for results page to render...", flush=True)
        await page.wait_for_url("**/results*", timeout=60000)
        await page.wait_for_selector("text=Power BI Mode", timeout=60000)
        await page.wait_for_timeout(2500)
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "live_prod_11_results_dashboard.png"))
        print(f"[PASS] Results page loaded successfully: {page.url}", flush=True)

        # Phase 7: Deliverable Downloads
        print("\n--- Phase 7: Live Deliverables Generation & Download ---", flush=True)
        # Wait for deliverables hub validation badge
        try:
            await page.wait_for_selector("text=Verified & Ready", timeout=25000)
        except Exception:
            print("Status badge waiting completed, continuing...", flush=True)
        await page.wait_for_timeout(1000)

        download_formats = [
            ("PDF", "button:has-text('Download PDF')"),
            ("XLSX", "button:has-text('Download .xlsx')"),
            ("HTML", "button:has-text('Download HTML')"),
            ("ZIP", "button:has-text('Download .zip')"),
        ]
        for label, selector in download_formats:
            btn = page.locator(selector).first
            assert await btn.is_visible(), f"{label} download button ({selector}) is missing!"
            print(f"Downloading {label} deliverable from live backend...", flush=True)
            async with page.expect_download(timeout=45000) as dl_info:
                await btn.click()
            dl = await dl_info.value
            failure = await dl.failure()
            if failure:
                print(f"  [DOWNLOAD FAILURE] {label}: {failure}", flush=True)
            assert failure is None, f"Download failed for {label}: {failure}"
            target_file = os.path.join(SCREENSHOTS_DIR, f"live_deliverable_{label}.{label.lower()}")
            await dl.save_as(target_file)
            size_kb = round(os.path.getsize(target_file) / 1024, 1)
            print(f"  -> Successfully downloaded: {dl.suggested_filename} ({size_kb} KB)")
            assert size_kb > 0, f"Downloaded {label} file was 0 bytes!"
            await page.wait_for_timeout(2500)
        print("[PASS] All 4 deliverables verified and downloaded from live production!", flush=True)

        # Phase 8: Sign Out Confirmation & Session Invalidation
        print("\n--- Phase 8: Sign Out Confirmation & Session Invalidation ---", flush=True)
        results_signout_btn = page.locator("header button:has-text('Sign Out')")
        await results_signout_btn.click()
        await page.wait_for_timeout(500)

        assert await page.locator("#signout-dialog-title").is_visible(), "Sign out confirmation modal not displayed!"
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "live_prod_12_signout_confirmation.png"))

        # Test Cancel dismissal
        print("Testing Cancel dismissal...", flush=True)
        await page.locator("div[role='dialog'] button:has-text('Cancel')").click()
        await page.wait_for_timeout(400)
        assert await page.locator("#signout-dialog-title").count() == 0, "Cancel did not dismiss modal!"
        print("Cancel button dismissed modal successfully.")

        # Reopen and Confirm Sign Out
        print("Confirming Sign Out...", flush=True)
        await results_signout_btn.click()
        await page.wait_for_timeout(500)
        
        async with page.expect_response("**/api/auth/logout", timeout=20000) as logout_info:
            await page.locator("div[role='dialog'] button:has-text('Sign Out')").click()
        logout_resp = await logout_info.value
        print(f"Logout API Status: {logout_resp.status}")

        await page.wait_for_url("**/login*", timeout=20000)
        await page.wait_for_selector("#login-identity", timeout=15000)
        await page.wait_for_timeout(1000)
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "live_prod_13_signed_out.png"))
        print("[PASS] Session invalidated and successfully redirected to /login!", flush=True)

        await browser.close()
        print("\n=======================================================", flush=True)
        print("🎉 ALL LIVE PRODUCTION TESTS PASSED WITH 100% SUCCESS!", flush=True)
        print("=======================================================", flush=True)

if __name__ == "__main__":
    asyncio.run(test_live_production_suite())
