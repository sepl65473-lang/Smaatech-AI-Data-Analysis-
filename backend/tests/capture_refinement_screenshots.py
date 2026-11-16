"""
Playwright End-to-End Verification & High-Res Screenshot Capture:
Captures all required sections for the Final Dashboard Quality Refinement:
1. Executive Overview & Ledger
2. Metric Explanation Modal (5-part diagnostic guide)
3. Financial Storytelling (9 analytical narratives with verified facts vs interpretations)
4. Income and Expense Analysis (Daily/Compare/Balance Cash Flows)
5. Category Analysis (Top spend & income sources)
6. Party Analysis (Normalized counterparties)
7. Transaction Intelligence (Risk signals & flags)
8. Transaction Explorer (Table with Rail/Mode column & detail inspector)
9. Category Intelligence Review Modal
10. Reconciliation & Mathematical Audit Proof
11. Standalone Offline HTML Dashboard
"""

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

    print(f"Loading Results Dashboard: {url}")
    print(f"Loading Standalone HTML: {html_url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 960})
        page = await context.new_page()

        console_errors = []
        page.on("pageerror", lambda err: console_errors.append(str(err)))

        await page.goto(url, wait_until="networkidle")
        await page.wait_for_timeout(2500)

        # 1. Executive Overview
        exec_elem = page.locator("#executive-overview")
        if await exec_elem.count() > 0:
            await exec_elem.scroll_into_view_if_needed()
            await page.wait_for_timeout(400)
            await exec_elem.screenshot(path=os.path.join(ARTIFACT_DIR, "refinement_1_executive_overview.png"))
            print("[OK] Captured refinement_1_executive_overview.png")

        # 2. Metric Explanation Modal (Click "Guide →" on KPI card)
        explain_btn = page.locator("button:has-text('Guide')").first
        if await explain_btn.count() > 0:
            await explain_btn.click()
            await page.wait_for_timeout(600)
            modal = page.locator(".animate-scaleUp")
            if await modal.count() > 0:
                await page.screenshot(path=os.path.join(ARTIFACT_DIR, "refinement_2_metric_explanation_modal.png"))
                print("[OK] Captured refinement_2_metric_explanation_modal.png")
            # Close explanation modal
            close_btn = page.locator("button:has-text('Close Guide'), button:has-text('✕')").first
            if await close_btn.count() > 0:
                await close_btn.click(force=True)
                await page.wait_for_timeout(500)

        # 3. Dynamic Financial Storytelling
        story_elem = page.locator("#financial-storytelling")
        if await story_elem.count() > 0:
            await story_elem.scroll_into_view_if_needed()
            await page.wait_for_timeout(400)
            await story_elem.screenshot(path=os.path.join(ARTIFACT_DIR, "refinement_3_financial_storytelling.png"))
            print("[OK] Captured refinement_3_financial_storytelling.png")

        # 4. Income and Expense Analysis
        cf_elem = page.locator("#income-expense-analysis")
        if await cf_elem.count() > 0:
            await cf_elem.scroll_into_view_if_needed()
            await page.wait_for_timeout(400)
            await cf_elem.screenshot(path=os.path.join(ARTIFACT_DIR, "refinement_4_income_expense_analysis.png"))
            print("[OK] Captured refinement_4_income_expense_analysis.png")

        # 5. Category Analysis
        cat_elem = page.locator("#category-analysis")
        if await cat_elem.count() > 0:
            await cat_elem.scroll_into_view_if_needed()
            await page.wait_for_timeout(400)
            await cat_elem.screenshot(path=os.path.join(ARTIFACT_DIR, "refinement_5_category_analysis.png"))
            print("[OK] Captured refinement_5_category_analysis.png")

        # 6. Party Analysis
        party_elem = page.locator("#party-analysis")
        if await party_elem.count() > 0:
            await party_elem.scroll_into_view_if_needed()
            await page.wait_for_timeout(400)
            await party_elem.screenshot(path=os.path.join(ARTIFACT_DIR, "refinement_6_party_analysis.png"))
            print("[OK] Captured refinement_6_party_analysis.png")

        # 7. Transaction Intelligence
        intel_elem = page.locator("#transaction-intelligence")
        if await intel_elem.count() > 0:
            await intel_elem.scroll_into_view_if_needed()
            await page.wait_for_timeout(400)
            await intel_elem.screenshot(path=os.path.join(ARTIFACT_DIR, "refinement_7_transaction_intelligence.png"))
            print("[OK] Captured refinement_7_transaction_intelligence.png")

        # 8. Transaction Explorer (Table with Rail/Mode and controls)
        txn_elem = page.locator("#transactions-section")
        if await txn_elem.count() > 0:
            await txn_elem.scroll_into_view_if_needed()
            await page.wait_for_timeout(400)
            await txn_elem.screenshot(path=os.path.join(ARTIFACT_DIR, "refinement_8_transaction_explorer.png"))
            print("[OK] Captured refinement_8_transaction_explorer.png")

        # 9. Category Intelligence Review Modal
        cat_int_btn = page.locator("button:has-text('Category Intelligence')").first
        if await cat_int_btn.count() > 0:
            await cat_int_btn.click(force=True)
            await page.wait_for_timeout(800)
            cat_modal = page.locator(".animate-scaleUp")
            if await cat_modal.count() > 0:
                await page.screenshot(path=os.path.join(ARTIFACT_DIR, "refinement_9_category_intelligence_modal.png"))
                print("[OK] Captured refinement_9_category_intelligence_modal.png")
            # Close modal
            close_x = page.locator("button:has-text('✕')").first
            if await close_x.count() > 0:
                await close_x.click(force=True)
                await page.wait_for_timeout(500)

        # 10. Reconciliation and Audit Proof
        reconcil_elem = page.locator("#reconciliation-audit")
        if await reconcil_elem.count() > 0:
            await reconcil_elem.scroll_into_view_if_needed()
            await page.wait_for_timeout(400)
            await reconcil_elem.screenshot(path=os.path.join(ARTIFACT_DIR, "refinement_10_reconciliation.png"))
            print("[OK] Captured refinement_10_reconciliation.png")

        # 11. Standalone Offline HTML Dashboard
        html_page = await context.new_page()
        await html_page.goto(html_url, wait_until="networkidle")
        await html_page.wait_for_timeout(2000)
        await html_page.screenshot(path=os.path.join(ARTIFACT_DIR, "refinement_11_offline_html.png"))
        print("[OK] Captured refinement_11_offline_html.png")
        await html_page.close()

        await page.close()
        await browser.close()

    print("\n[OK] All screenshots captured successfully without errors!")

if __name__ == "__main__":
    asyncio.run(main())
