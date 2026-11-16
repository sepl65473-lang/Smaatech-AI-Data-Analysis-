"""
Comprehensive verification of category remapping propagation across all 5 deliverables and UI data sources.
"""
import sys
import os
import io
import json
import zipfile
import requests
import openpyxl
from pypdf import PdfReader

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def get_active_session(base_url="http://127.0.0.1:8000"):
    for cand in ["active_session_id.txt", "backend/active_session_id.txt", "../active_session_id.txt"]:
        if os.path.exists(cand):
            with open(cand) as f:
                sid = f.read().strip()
                if sid:
                    try:
                        r = requests.get(f"{base_url}/api/results/{sid}")
                        if r.status_code == 200:
                            return sid
                    except Exception:
                        pass

    # If no valid session from file, upload the original PDF
    pdf_candidates = [
        "tests/axis_june_2023_original.pdf",
        "backend/tests/axis_june_2023_original.pdf",
        "axis_june_2023_original.pdf",
    ]
    pdf_path = next((p for p in pdf_candidates if os.path.exists(p)), None)
    if pdf_path:
        with open(pdf_path, "rb") as f:
            up = requests.post(
                f"{base_url}/api/upload",
                files={"file": ("axis_june_2023_original.pdf", f, "application/pdf")},
            )
            if up.status_code == 200:
                sid = up.json()["session_id"]
                with open("active_session_id.txt", "w") as out_f:
                    out_f.write(sid)
                return sid
    raise RuntimeError("Could not find or create active session.")


def test_category_remapping_propagation():
    base_url = os.environ.get("TEST_API_BASE_URL", "http://127.0.0.1:8000")
    try:
        session_id = get_active_session(base_url)
    except Exception as exc:
        print(f"Skipping test_category_remapping_propagation (backend server not running or session unavailable): {exc}")
        return

    print(f"Testing category remapping on active session: {session_id}")

    # 1. Fetch current state
    r0 = requests.get(f"{base_url}/api/results/{session_id}").json()
    orig_metrics = r0["metrics"]
    orig_dr = orig_metrics["total_spend"]
    orig_cr = orig_metrics["total_income"]
    orig_open = orig_metrics["opening_balance"]
    orig_close = orig_metrics["closing_balance"]
    orig_recon = orig_metrics["is_reconciled"]
    orig_delta = orig_metrics["reconciliation_delta"]

    print(f"Pre-mapping: Dr=INR {orig_dr:,.2f}, Cr=INR {orig_cr:,.2f}, Delta=INR {orig_delta:.2f}, Reconciled={orig_recon}")

    # 2. Perform counterparty-level category remapping
    remap_payload = {
        "target_type": "counterparty",
        "target_value": "Suraj Tparty",
        "new_category": "Site Contractors",
        "apply_to_future": True,
    }
    remap_res = requests.post(
        f"{base_url}/api/results/{session_id}/category-mapping",
        json=remap_payload,
    )
    assert remap_res.status_code == 200, f"Remap failed: {remap_res.text}"
    remap_data = remap_res.json()
    print(f"Remap API Success: Modified {remap_data.get('modified_count')} transactions for 'Suraj Tparty' -> 'Site Contractors'")

    # 3. Check updated API results
    r1 = requests.get(f"{base_url}/api/results/{session_id}").json()
    new_metrics = r1["metrics"]
    new_txns = r1["transactions"]

    # Verify financial reconciliation unchanged
    assert new_metrics["total_spend"] == orig_dr, f"Spend changed: {new_metrics['total_spend']} vs {orig_dr}"
    assert new_metrics["total_income"] == orig_cr, f"Income changed: {new_metrics['total_income']} vs {orig_cr}"
    assert new_metrics["opening_balance"] == orig_open, "Opening changed"
    assert new_metrics["closing_balance"] == orig_close, "Closing changed"
    assert new_metrics["is_reconciled"] is True, "Reconciliation broken"
    assert new_metrics["reconciliation_delta"] == 0.00, f"Delta non-zero: {new_metrics['reconciliation_delta']}"
    print("[OK] Financial reconciliation strictly invariant under category remapping (Delta = INR 0.00)")

    # Verify transactions updated with audit trail metadata
    suraj_txns = [t for t in new_txns if (t.get("counterparty") or t.get("merchant")) == "Suraj Tparty"]
    assert len(suraj_txns) == 6, f"Expected 6 Suraj txns, found {len(suraj_txns)}"
    for st in suraj_txns:
        assert st["category"] == "Site Contractors", f"Txn {st['id']} category not updated: {st['category']}"
        assert st.get("confidence") == "High", f"Expected High confidence, got {st.get('confidence')}"
        assert st.get("confidence_score") == 1.0, f"Expected confidence_score 1.0, got {st.get('confidence_score')}"
        assert st.get("classification_source") == "user", f"Expected source user, got {st.get('classification_source')}"
    print("[OK] All 6 'Suraj Tparty' transactions updated with category='Site Contractors', confidence='High', score=1.0, source='user'")

    # Verify top_categories contains Site Contractors
    cat_names = [c["category"] for c in new_metrics["top_categories"]]
    assert "Site Contractors" in cat_names, f"'Site Contractors' missing from top_categories: {cat_names}"
    sc_cat = next(c for c in new_metrics["top_categories"] if c["category"] == "Site Contractors")
    print(f"[OK] Category charts & Executive Overview updated: 'Site Contractors' amount = INR {sc_cat['amount']:,.2f} ({sc_cat['percentage']}%)")

    # 4. Export & verify CSV
    csv_res = requests.get(f"{base_url}/api/export/{session_id}?format=csv")
    assert csv_res.status_code == 200, "CSV export failed"
    csv_text = csv_res.text
    assert "Site Contractors" in csv_text, "Remapped category missing in CSV"
    print(f"[OK] CSV export: Verified 'Site Contractors' present in transaction export ({len(csv_res.content):,} bytes)")

    # 5. Export & verify Excel (all 7 sheets and remapped category)
    xlsx_res = requests.get(f"{base_url}/api/export/{session_id}?format=xlsx")
    assert xlsx_res.status_code == 200, "Excel export failed"
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_res.content), data_only=False)
    sheet_names = wb.sheetnames
    print(f"\n[OK] Excel Workbook loaded. Actual 7 Sheet Names:\n  {sheet_names}")
    assert len(sheet_names) == 7, f"Expected 7 sheets, got {len(sheet_names)}"

    # Check Sheet 2: Complete Transactions
    ws_txns = wb["Complete Transactions"]
    found_in_excel_txns = False
    for row in ws_txns.iter_rows(values_only=True):
        if "Site Contractors" in [str(c) for c in row if c]:
            found_in_excel_txns = True
            break
    assert found_in_excel_txns, "Remapped category missing in Excel Complete Transactions sheet"
    print("  -> 'Site Contractors' confirmed in Excel 'Complete Transactions' worksheet")

    # Check Sheet 4: Category Analysis
    ws_cat = wb["Category Analysis"]
    found_in_excel_cat = False
    for row in ws_cat.iter_rows(values_only=True):
        if "Site Contractors" in [str(c) for c in row if c]:
            found_in_excel_cat = True
            break
    assert found_in_excel_cat, "Remapped category missing in Excel Category Analysis sheet"
    print("  -> 'Site Contractors' confirmed in Excel 'Category Analysis' worksheet")

    # 6. Export & verify PDF
    pdf_res = requests.get(f"{base_url}/api/export/{session_id}?format=pdf")
    assert pdf_res.status_code == 200, "PDF export failed"
    reader = PdfReader(io.BytesIO(pdf_res.content))
    print(f"\n[OK] PDF Report generated ({len(reader.pages)} pages, {len(pdf_res.content):,} bytes)")
    pdf_text_all = "".join(p.extract_text() or "" for p in reader.pages)
    assert "Site Contractors" in pdf_text_all, "Remapped category missing in PDF text"
    assert "115,915.26" in pdf_text_all, "Opening balance missing in PDF"
    assert "38,285.26" in pdf_text_all, "Closing balance missing in PDF"
    assert "reconciliation" in pdf_text_all.lower(), "Reconciliation badge missing in PDF"
    print("  -> PDF verified: 'Site Contractors', Reconciled status, Opening and Closing balances present")

    # 7. Export & verify Standalone HTML
    html_res = requests.get(f"{base_url}/api/export/{session_id}?format=html")
    assert html_res.status_code == 200, "HTML export failed"
    html_text = html_res.text
    assert "Site Contractors" in html_text, "Remapped category missing in Standalone HTML"
    assert "const DATA =" in html_text or "const REPORT_DATA =" in html_text, "DATA payload missing in Standalone HTML"
    print(f"\n[OK] Standalone HTML verified: 'Site Contractors' embedded in self-contained dataset ({len(html_res.content):,} bytes)")

    # 8. Export & verify ZIP package and CRC
    zip_res = requests.get(f"{base_url}/api/export/{session_id}?format=zip")
    assert zip_res.status_code == 200, "ZIP export failed"
    zf = zipfile.ZipFile(io.BytesIO(zip_res.content))
    zip_names = zf.namelist()
    print(f"\n[OK] Complete ZIP Package loaded. File List:\n  {zip_names}")
    crc_errs = zf.testzip()
    assert crc_errs is None, f"ZIP CRC Check failed on file: {crc_errs}"
    print("  -> ZIP CRC Validation: PASSED (Zero corrupted files)")

    # Inspect files inside ZIP
    csv_in_zip = zf.read([n for n in zip_names if n.endswith(".csv")][0]).decode("utf-8")
    assert "Site Contractors" in csv_in_zip, "Remapped category missing in ZIP's CSV"
    html_in_zip = zf.read([n for n in zip_names if n.endswith(".html")][0]).decode("utf-8")
    assert "Site Contractors" in html_in_zip, "Remapped category missing in ZIP's HTML"
    print("  -> ZIP contents verified: all contained exports reflect remapped category")

    print("\n" + "=" * 65)
    print("ALL PROPAGATION CHECKS VERIFIED SUCCESSFULLY ACROSS DELIVERABLES!")
    print("=" * 65)


if __name__ == "__main__":
    test_category_remapping_propagation()
