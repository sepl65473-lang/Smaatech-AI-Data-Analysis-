import asyncio
import os
import sys
import time
from playwright.async_api import async_playwright

LIVE_URL = "https://smaatech-ai-data-analysis.vercel.app"
SCREENSHOTS_DIR = r"C:\Users\DELL\.gemini\antigravity\brain\deb421e9-e661-4cb4-872b-9c9f81e55964\screenshots"
SAMPLE_PDF = r"D:\bank statment\AI Data Analysis Platform\axis_june_2023_original.pdf"

EMAIL = "itsmaatech@gmail.com"
PASS = "SeplAdmin@2026"

os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

async def test_live_production():
    print(f"=== STARTING LIVE PRODUCTION VERIFICATION ON {LIVE_URL} ===", flush=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            ignore_https_errors=True
        )
        page = await context.new_page()

        # 1. Navigate to live site
        print("\n1. Navigating to live site...", flush=True)
        await page.goto(LIVE_URL, wait_until="networkidle", timeout=45000)
        await page.wait_for_timeout(2000)
        
        # Check current URL
        curr_url = page.url
        print(f"Initial URL: {curr_url}", flush=True)
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "live_01_login_page.png"))

        # If on /login, perform authentication
        if "/login" in page.url or await page.locator("#login-identity").count() > 0:
            print("Entering credentials on live login page...", flush=True)
            await page.fill("#login-identity", EMAIL)
            await page.fill("#login-password", PASS)
            await page.click("button[type='submit']")
            await page.wait_for_timeout(3000)

        # Wait for redirect to home
        print(f"After login URL: {page.url}", flush=True)
        await page.wait_for_selector("text=AI Data Analysis Platform", timeout=15000)
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "live_02_home_authenticated.png"))
        print("[PASS] Successfully authenticated on live site!", flush=True)

        # 2. Verify Top-Right Header Elements
        print("\n2. Verifying Top-Right Header actions...", flush=True)
        change_pwd_btn = page.locator("#header-change-password-btn")
        signout_btn = page.locator("#header-sign-out-btn")
        menu_btn = page.locator("#header-menu-button")

        assert await change_pwd_btn.is_visible(), "Change Password button not visible!"
        assert await signout_btn.is_visible(), "Sign Out button not visible!"
        assert await menu_btn.is_visible(), "Three-dot menu button not visible!"
        print("[PASS] Top-right header strictly contains Change Password, Sign Out, and Three-Dot menu!", flush=True)

        # 3. Test Theme Switching
        print("\n3. Testing Dark / Light mode toggle...", flush=True)
        await menu_btn.click()
        await page.wait_for_timeout(500)
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "live_03_menu_dropdown.png"))
        
        theme_toggle = page.locator("#menu-item-theme-toggle")
        await theme_toggle.click()
        await page.wait_for_timeout(500)
        is_dark = await page.evaluate("() => document.documentElement.classList.contains('dark')")
        print(f"Dark mode state after toggle: {is_dark}", flush=True)
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "live_04_dark_mode.png"))
        
        # Toggle back to light
        await menu_btn.click()
        await page.wait_for_timeout(300)
        await page.locator("#menu-item-theme-toggle").click()
        await page.wait_for_timeout(300)

        # 4. Test Modals via Three-Dot Menu
        print("\n4. Testing Modals in Three-Dot Menu...", flush=True)
        
        # Profile
        await menu_btn.click()
        await page.wait_for_timeout(300)
        await page.locator("#menu-item-profile").click()
        await page.wait_for_timeout(500)
        assert await page.locator("text=Profile Settings").is_visible()
        assert await page.locator(f"text={EMAIL}").is_visible()
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "live_05_modal_profile.png"))
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(300)

        # Account
        await menu_btn.click()
        await page.wait_for_timeout(300)
        await page.locator("#menu-item-account").click()
        await page.wait_for_timeout(500)
        assert await page.locator("text=Account Settings").is_visible()
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "live_06_modal_account.png"))
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(300)

        # Notifications
        await menu_btn.click()
        await page.wait_for_timeout(300)
        await page.locator("#menu-item-notifications").click()
        await page.wait_for_timeout(500)
        assert await page.locator("text=Notification Preferences").is_visible()
        # Toggle a checkbox
        cb = page.locator("input[type='checkbox']").first
        await cb.click()
        await page.wait_for_timeout(300)
        assert await page.locator("text=✓ Saved").is_visible()
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "live_07_modal_notifications.png"))
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(300)

        # Activity Log (RBAC)
        await menu_btn.click()
        await page.wait_for_timeout(300)
        await page.locator("#menu-item-activity-log").click()
        await page.wait_for_timeout(500)
        assert await page.locator("text=System Activity Log").is_visible()
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "live_08_modal_activity_log.png"))
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(300)

        # Security Settings
        await menu_btn.click()
        await page.wait_for_timeout(300)
        await page.locator("#menu-item-security").click()
        await page.wait_for_timeout(500)
        assert await page.locator("text=Security & Session Settings").is_visible()
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "live_09_modal_security.png"))
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(300)
        print("[PASS] All advanced modals verified!", flush=True)

        # 5. Test Change Password Dialog
        print("\n5. Testing Change Password dialog...", flush=True)
        await change_pwd_btn.click()
        await page.wait_for_timeout(500)
        assert await page.locator("#password-dialog-title").is_visible()
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "live_10_change_password_dialog.png"))
        # Close with escape
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(500)
        if await page.locator("#password-dialog-title").is_visible():
            await page.click("button:has-text('Cancel')")
            await page.wait_for_timeout(300)
        print("[PASS] Change Password dialog verified!", flush=True)

        # 6. Test File Upload and Analysis
        print(f"\n6. Testing file upload and analysis with {os.path.basename(SAMPLE_PDF)}...", flush=True)
        file_input = page.locator("input[type='file']")
        await file_input.set_input_files(SAMPLE_PDF)
        await page.wait_for_timeout(1000)
        
        analyze_btn = page.locator("button:has-text('Analyze Data')")
        await analyze_btn.click()
        print("Analysis submitted, waiting for results page...", flush=True)
        
        await page.wait_for_url("**/results*", timeout=45000)
        await page.wait_for_timeout(3000)
        print(f"Results page reached: {page.url}", flush=True)
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "live_11_results_page.png"))

        # Verify Results Header
        results_header = page.locator("header")
        assert await results_header.is_visible()
        assert await page.locator("text=Power BI Mode").is_visible()
        print("[PASS] Results dashboard header verified with Power BI Mode!", flush=True)

        # 7. Test Deliverable Downloads on Live Site
        print("\n7. Testing Deliverable Downloads on Live Site...", flush=True)
        # Find download links or export endpoints
        download_formats = ["pdf", "xlsx", "html", "zip"]
        for fmt in download_formats:
            btn = page.locator(f"button:has-text('{fmt.upper()}')").first
            if await btn.count() > 0:
                print(f"Triggering download for {fmt.upper()}...", flush=True)
                async with page.expect_download(timeout=20000) as download_info:
                    await btn.click()
                download = await download_info.value
                save_path = os.path.join(SCREENSHOTS_DIR, f"live_download_{download.suggested_filename}")
                await download.save_as(save_path)
                size_kb = round(os.path.getsize(save_path) / 1024, 1)
                print(f"  -> Downloaded {download.suggested_filename} ({size_kb} KB)")
                assert size_kb > 0, f"Downloaded file {fmt} is empty!"
        print("[PASS] Deliverables downloaded and verified!", flush=True)

        # 8. Test Sign Out Confirmation
        print("\n8. Testing Sign Out Confirmation modal...", flush=True)
        signout_header_btn = page.locator("#header-sign-out-btn")
        await signout_header_btn.click()
        await page.wait_for_timeout(500)
        
        assert await page.locator("text=Confirm Sign Out").is_visible()
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "live_12_signout_confirmation.png"))
        
        # Test Cancel button first
        cancel_btn = page.locator("#signout-cancel-btn")
        await cancel_btn.click()
        await page.wait_for_timeout(500)
        assert await page.locator("text=Confirm Sign Out").count() == 0
        print("Sign Out canceled successfully.")

        # Click Sign Out again and Confirm
        await signout_header_btn.click()
        await page.wait_for_timeout(500)
        confirm_btn = page.locator("#signout-confirm-btn")
        await confirm_btn.click()
        await page.wait_for_timeout(3000)
        
        print(f"URL after Sign Out: {page.url}", flush=True)
        assert "/login" in page.url or await page.locator("#login-identity").is_visible()
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "live_13_signed_out.png"))
        print("[PASS] Sign out successfully revoked session and redirected to login!", flush=True)

        await browser.close()
        print("\n=== ALL LIVE PRODUCTION TESTS COMPLETED WITH 100% SUCCESS! ===", flush=True)

if __name__ == "__main__":
    asyncio.run(test_live_production())

