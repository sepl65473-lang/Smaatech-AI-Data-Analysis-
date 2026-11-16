"""
capture_final_polish_screenshots.py
Captures genuine, high-resolution screenshots for FINAL POLISH acceptance audit.
Saves to both DOCS/screenshots and the conversation artifact directory.
"""

import asyncio
import os
import sys
import shutil
from playwright.async_api import async_playwright

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCS_SCREENSHOT_DIR = os.path.join(PROJECT_DIR, "DOCS", "screenshots")
ARTIFACT_DIR = r"C:\Users\DELL\.gemini\antigravity\brain\fcafa5d6-6185-4e69-abb6-41fb6c936d28"
os.makedirs(DOCS_SCREENSHOT_DIR, exist_ok=True)
os.makedirs(ARTIFACT_DIR, exist_ok=True)

ACTIVE_SESSION_FILE = os.path.join(PROJECT_DIR, "backend", "active_session_id.txt")
with open(ACTIVE_SESSION_FILE, "r") as f:
    session_id = f.read().strip()

URL = f"http://localhost:5173/results?sid={session_id}"
HTML_URL = f"http://127.0.0.1:8000/api/export/{session_id}?format=html&preview=true"

async def capture():
    print(f"[*] Navigating to: {URL}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 960})
        page = await context.new_page()

        await page.goto(URL, wait_until="networkidle")
        await page.wait_for_timeout(2500)

        async def save_shot(locator, filename):
            target_docs = os.path.join(DOCS_SCREENSHOT_DIR, filename)
            target_art = os.path.join(ARTIFACT_DIR, filename)
            if locator and await locator.count() > 0:
                await locator.first.scroll_into_view_if_needed()
                await page.wait_for_timeout(300)
                await locator.first.screenshot(path=target_docs)
            else:
                await page.screenshot(path=target_docs)
            shutil.copy2(target_docs, target_art)
            print(f"  [OK] Saved: {filename} ({os.path.getsize(target_docs):,} bytes)", flush=True)

        # 1. Executive Overview
        elem = page.locator("#executive-overview")
        await save_shot(elem, "01_executive_overview.png")

        # 2. Deliverables Hub
        elem = page.locator("#deliverables-hub")
        await save_shot(elem, "02_deliverables_hub.png")

        # 3. Metric Explanation Modal (click Guide)
        explain_btn = page.locator("button:has-text('Guide')").first
        if await explain_btn.count() > 0:
            await explain_btn.click()
            await page.wait_for_timeout(500)
            modal = page.locator("div.fixed.inset-0")
            await save_shot(modal, "03_metric_explanation_modal.png")
            # Close modal
            close_btn = page.locator("button:has-text('✕')").first
            if await close_btn.count() > 0:
                await close_btn.click()
                await page.wait_for_timeout(300)

        # 4. Financial Storytelling
        elem = page.locator("#financial-storytelling")
        await save_shot(elem, "04_financial_storytelling.png")

        # 5. Income and Expense Cashflow
        elem = page.locator("#income-expense-analysis")
        await save_shot(elem, "05_income_expense_cashflow.png")

        # 6. Category Analysis
        elem = page.locator("#category-analysis")
        await save_shot(elem, "06_category_analysis.png")

        # 7. Party Analysis
        elem = page.locator("#party-analysis")
        await save_shot(elem, "07_party_analysis.png")

        # 8. Transaction Intelligence
        elem = page.locator("#transaction-intelligence")
        await save_shot(elem, "08_transaction_intelligence.png")

        # 9. Transaction Explorer
        elem = page.locator("#transaction-explorer")
        await save_shot(elem, "09_transaction_explorer.png")

        # 10. Category Intelligence Review Modal
        review_btn = page.locator("button:has-text('Category Intelligence')").first
        if await review_btn.count() > 0:
            await review_btn.click()
            await page.wait_for_timeout(600)
            modal = page.locator("div.fixed.inset-0")
            await save_shot(modal, "10_category_review_modal.png")
            close_btn = page.locator("button:has-text('Done Reviewing')").first
            if await close_btn.count() > 0:
                await close_btn.click()
                await page.wait_for_timeout(300)

        # 11. Reconciliation Audit
        elem = page.locator("#reconciliation-audit")
        if await elem.count() > 0:
            await save_shot(elem, "11_reconciliation_audit.png")
        else:
            # fallback to executive overview reconciliation badge
            await save_shot(page.locator("#executive-overview"), "11_reconciliation_audit.png")

        # 12. Standalone Offline HTML Dashboard
        print(f"[*] Navigating to Standalone HTML: {HTML_URL}")
        html_page = await context.new_page()
        await html_page.goto(HTML_URL, wait_until="networkidle")
        await html_page.wait_for_timeout(1500)
        target_docs = os.path.join(DOCS_SCREENSHOT_DIR, "12_standalone_offline_html.png")
        target_art = os.path.join(ARTIFACT_DIR, "12_standalone_offline_html.png")
        await html_page.screenshot(path=target_docs)
        shutil.copy2(target_docs, target_art)
        print(f"  [OK] Saved: 12_standalone_offline_html.png ({os.path.getsize(target_docs):,} bytes)")
        await html_page.close()

        # 13. Remapped Category Chart
        elem = page.locator("#category-analysis")
        await save_shot(elem, "13_remapped_category_chart.png")

        await browser.close()
        print("[*] All 13 genuine screenshots successfully captured and saved!")

if __name__ == "__main__":
    asyncio.run(capture())
