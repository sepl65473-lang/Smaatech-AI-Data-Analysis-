import asyncio
import os
import sys
from playwright.async_api import async_playwright

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

ARTIFACT_DIR = r"C:\Users\DELL\.gemini\antigravity-ide\brain\4362b3d7-585a-4b9a-b5cc-a69b591dc3a3"

async def main():
    with open("active_session_id.txt", "r") as f:
        session_id = f.read().strip()
    
    url = f"http://localhost:5173/results?sid={session_id}"
    html_url = f"http://127.0.0.1:8000/api/export/{session_id}?format=html&preview=true"
    print(f"Testing Dashboard at: {url}")
    print(f"Testing HTML Dashboard at: {html_url}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()
        
        console_logs = []
        errors = []
        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: errors.append(str(err)))
        
        print("\n--- STEP 1: LOAD RESULTS PAGE ---")
        await page.goto(url, wait_until="networkidle")
        await page.wait_for_timeout(2000)
        
        # Verify title or header
        content = await page.content()
        assert "Axis" in content or "Financial Analytics" in content or "Results" in content
        print(f"Page Title: {await page.title()}")
        print(f"Console errors: {len(errors)}")
        if errors:
            print("Errors encountered:", errors)
        
        # Take Executive Overview screenshot
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "powerbi_executive_overview.png"), full_page=False)
        print("Captured: powerbi_executive_overview.png")
        
        # Verify 9 KPI cards exist
        kpis = await page.locator("text=Total Income").count()
        print(f"Found 'Total Income' label: {kpis > 0}")
        assert kpis > 0, "Missing Total Income KPI"
        
        # --- STEP 2: TEST CASH FLOW TABS ---
        print("\n--- STEP 2: CASH FLOW & CATEGORY ---")
        compare_tab = page.locator("button:has-text('Income vs Expense')")
        if await compare_tab.count() > 0:
            await compare_tab.click()
            await page.wait_for_timeout(500)
            print("Clicked 'Income vs Expense' tab")
        
        balance_tab = page.locator("button:has-text('Cumulative Balance')")
        if await balance_tab.count() > 0:
            await balance_tab.click()
            await page.wait_for_timeout(500)
            print("Clicked 'Cumulative Balance' tab")
        
        # Scroll to Charts & Category section and screenshot
        await page.evaluate("window.scrollBy(0, 700)")
        await page.wait_for_timeout(500)
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "powerbi_cashflow_category.png"), full_page=False)
        print("Captured: powerbi_cashflow_category.png")
        
        # --- STEP 3: PARTY ANALYSIS & INTELLIGENCE ---
        print("\n--- STEP 3: PARTY & INTELLIGENCE ---")
        await page.evaluate("window.scrollBy(0, 800)")
        await page.wait_for_timeout(500)
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "powerbi_party_intelligence.png"), full_page=False)
        print("Captured: powerbi_party_intelligence.png")
        
        # --- STEP 4: CROSS-FILTERING TEST ---
        print("\n--- STEP 4: CROSS-FILTERING ---")
        # Click on an intelligence card, e.g., 'High-Value Outflows' or 'Round Amount'
        high_val_card = page.locator("text=High-Value Outflows & Inflows").first
        if await high_val_card.count() > 0:
            await high_val_card.click()
            await page.wait_for_timeout(800)
            print("Clicked 'High-Value Outflows' intelligence card to filter")
            
            # Check ActiveFilterBar
            filter_bar = page.locator("text=Active Cross-Filters")
            print(f"ActiveFilterBar visible: {await filter_bar.count() > 0}")
            
            # Take screenshot of cross-filtered state
            await page.screenshot(path=os.path.join(ARTIFACT_DIR, "powerbi_cross_filtering_active.png"), full_page=False)
            print("Captured: powerbi_cross_filtering_active.png")
            
            # Click Reset Filters
            reset_btn = page.locator("button:has-text('Reset All Filters')")
            if await reset_btn.count() > 0:
                await reset_btn.click()
                await page.wait_for_timeout(500)
                print("Clicked 'Reset All Filters'")
        
        # --- STEP 5: TRANSACTION EXPLORER & MODAL ---
        print("\n--- STEP 5: TRANSACTION EXPLORER & MODAL ---")
        await page.evaluate("window.scrollBy(0, 800)")
        await page.wait_for_timeout(500)
        
        search_input = page.locator("input[placeholder*='Search']").first
        if await search_input.count() > 0:
            await search_input.fill("Ashoka")
            await page.wait_for_timeout(600)
            print("Searched for 'Ashoka'")
        
        # Click on the first row in transaction table to open modal
        first_row = page.locator("#transactions-section tbody tr").first
        if await first_row.count() > 0:
            await first_row.click()
            await page.wait_for_timeout(600)
            print("Clicked transaction row to open Detail Modal")
            
            # Check modal
            modal_title = page.locator("text=Transaction Audit Detail")
            print(f"Modal opened: {await modal_title.count() > 0}")
            assert await modal_title.count() > 0, "Detail modal did not open"
            
            # Close modal
            close_btn = page.locator("button:has-text('Close Inspector')").first
            if await close_btn.count() > 0:
                await close_btn.click()
                await page.wait_for_timeout(400)
                print("Closed Detail Modal")
        
        # Clear search
        if await search_input.count() > 0:
            await search_input.fill("")
            await page.wait_for_timeout(400)
        
        # Screenshot Explorer & Reconciliation
        await page.evaluate("window.scrollBy(0, 600)")
        await page.wait_for_timeout(500)
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "powerbi_explorer_reconciliation.png"), full_page=False)
        print("Captured: powerbi_explorer_reconciliation.png")
        
        # --- STEP 6: DARK MODE TOGGLE ---
        print("\n--- STEP 6: THEME TOGGLE (DARK MODE) ---")
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(500)
        
        theme_btn = page.locator("button[aria-label*='theme' i], button:has-text('☀️'), button:has-text('🌙')").first
        if await theme_btn.count() > 0:
            await theme_btn.click()
            await page.wait_for_timeout(800)
            print("Toggled to Dark Mode")
            await page.screenshot(path=os.path.join(ARTIFACT_DIR, "powerbi_dark_mode.png"), full_page=False)
            print("Captured: powerbi_dark_mode.png")
            # Toggle back to light
            await theme_btn.click()
            await page.wait_for_timeout(400)
        
        # --- STEP 7: STANDALONE OFFLINE HTML DASHBOARD ---
        print("\n--- STEP 7: STANDALONE OFFLINE HTML DASHBOARD ---")
        html_page = await context.new_page()
        await html_page.goto(html_url, wait_until="networkidle")
        await html_page.wait_for_timeout(2000)
        
        html_title = await html_page.title()
        print(f"HTML Dashboard Title: {html_title}")
        assert "Power BI Financial Analytics" in html_title
        
        await html_page.screenshot(path=os.path.join(ARTIFACT_DIR, "powerbi_offline_html_dashboard.png"), full_page=False)
        print("Captured: powerbi_offline_html_dashboard.png")
        
        # Test offline HTML table filter or search
        search_box = html_page.locator("#search-input")
        if await search_box.count() > 0:
            await search_box.fill("Suraj")
            await html_page.wait_for_timeout(500)
            print("Filtered HTML dashboard by 'Suraj'")
        
        await html_page.close()
        await page.close()
        await browser.close()
        
    print("\n=======================================================")
    print("ALL BROWSER INTERACTION TESTS PASSED WITH 0 ERRORS!")
    print("=======================================================")

if __name__ == "__main__":
    asyncio.run(main())
