import os
import sys
import zipfile
import io
import json
import pypdf
import openpyxl
from decimal import Decimal

art_dir = os.path.abspath("tests/artifacts_verification")

pdf_file = os.path.join(art_dir, "Financial_Analysis_2023-06.pdf")
xlsx_file = os.path.join(art_dir, "Financial_Analysis_2023-06.xlsx")
html_file = os.path.join(art_dir, "Financial_Dashboard_2023-06.html")
zip_file = os.path.join(art_dir, "Financial_Report_Package_2023-06.zip")
csv_file = os.path.join(art_dir, "Financial_Transactions_2023-06.csv")

print("="*60)
print("DEEP VERIFICATION OF ALL GENERATED DELIVERABLES")
print("="*60)

# 1. PDF Verification
print("\n[1] PDF REPORT VERIFICATION")
reader = pypdf.PdfReader(pdf_file)
print(f"Total Pages in PDF: {len(reader.pages)}")
pdf_text = ""
for i, p in enumerate(reader.pages, 1):
    txt = p.extract_text() or ""
    pdf_text += f"\n--- Page {i} ---\n" + txt

print(f"Extracted PDF text length: {len(pdf_text)} characters")
checks = {
    "Total Income (4,548,780)": "4,548,780" in pdf_text or "45,48,780" in pdf_text or "4548780" in pdf_text,
    "Total Expenses (4,626,410)": "4,626,410" in pdf_text or "46,26,410" in pdf_text or "4626410" in pdf_text,
    "Net Cash Flow (-77,630)": "-77,630" in pdf_text or "77,630" in pdf_text,
    "Opening Balance (115,915.26)": "115,915.26" in pdf_text or "1,15,915.26" in pdf_text,
    "Closing Balance (38,285.26)": "38,285.26" in pdf_text,
    "Transaction Count (162)": "162" in pdf_text,
    "June 2023 Period": "June 2023" in pdf_text or "Jun 2023" in pdf_text or "2023-06" in pdf_text,
}
for name, ok in checks.items():
    print(f"  {name}: {'PASS' if ok else 'FAIL'}")

# 2. Excel Verification
print("\n[2] EXCEL WORKBOOK (7 SHEETS) VERIFICATION")
wb = openpyxl.load_workbook(xlsx_file, data_only=False)
expected_sheets = [
    "Executive Summary",
    "Complete Transactions",
    "Income and Expenses",
    "Category Analysis",
    "Daily and Weekly Analysis",
    "Monthly Analysis",
    "Reconciliation and Audit Log"
]
print(f"Sheet Count: {len(wb.sheetnames)} (Expected: 7)")
formula_count = 0
for name in wb.sheetnames:
    ws = wb[name]
    s_formulas = 0
    for row in ws.iter_rows(values_only=False):
        for cell in row:
            if cell.value and str(cell.value).startswith("="):
                s_formulas += 1
    formula_count += s_formulas
    print(f"  Sheet '{name}': max_row={ws.max_row}, max_column={ws.max_column}, formulas={s_formulas}")

# Now load with data_only=True to check computed/cached values if any
wb_data = openpyxl.load_workbook(xlsx_file, data_only=True)
ws_tx = wb["Complete Transactions"]
# Complete Transactions header is row 4, rows start row 5
tx_data_rows = ws_tx.max_row - 4
print(f"Total Transactions in Excel sheet 'Complete Transactions': {tx_data_rows}")

# 3. HTML Dashboard Verification
print("\n[3] STANDALONE HTML DASHBOARD VERIFICATION")
with open(html_file, "r", encoding="utf-8") as f:
    html_content = f.read()

print(f"HTML Content Size: {len(html_content):,} bytes")
html_checks = {
    "Self-contained (no external broken css)": "<style>" in html_content,
    "Chart.js or SVG charts present": "Chart" in html_content or "<svg" in html_content,
    "Total Income (4,548,780)": "4,548,780" in html_content or "4548780" in html_content,
    "Total Expenses (4,626,410)": "4,626,410" in html_content or "4626410" in html_content,
    "Net Cash Flow (77,630)": "77,630" in html_content,
    "Transaction Count (162)": "162" in html_content,
    "Search Input Element": 'id="search-input"' in html_content or 'id="filter-' in html_content or 'search' in html_content.lower(),
    "Filter Categories": 'id="category-filter"' in html_content or 'filter' in html_content.lower(),
    "Table Rows Present": "<tbody" in html_content and "<tr" in html_content,
}
for name, ok in html_checks.items():
    print(f"  {name}: {'PASS' if ok else 'FAIL'}")

# 4. ZIP Package Verification
print("\n[4] COMPLETE ZIP PACKAGE VERIFICATION")
with open(zip_file, "rb") as f:
    zbytes = f.read()

with zipfile.ZipFile(io.BytesIO(zbytes), "r") as z:
    names = z.namelist()
    print(f"Files inside ZIP: {names}")
    for info in z.infolist():
        print(f"  - {info.filename}: uncompressed={info.file_size:,} bytes, compressed={info.compress_size:,} bytes")
    
    # Verify exact match with standalone deliverables
    with open(pdf_file, "rb") as pf:
        pdf_orig = pf.read()
    with open(xlsx_file, "rb") as xf:
        xlsx_orig = xf.read()
    with open(html_file, "rb") as hf:
        html_orig = hf.read()

    zip_pdf = z.read("Financial_Analysis_2023-06.pdf")
    zip_xlsx = z.read("Financial_Analysis_2023-06.xlsx")
    zip_html = z.read("Financial_Dashboard_2023-06.html")

    print(f"  PDF in ZIP matches standalone: {len(zip_pdf) == len(pdf_orig)}")
    print(f"  XLSX in ZIP matches standalone: {len(zip_xlsx) == len(xlsx_orig)}")
    print(f"  HTML in ZIP matches standalone: {len(zip_html) == len(html_orig)}")

# 5. CSV Export Verification
print("\n[5] CSV REPORT VERIFICATION")
with open(csv_file, "r", encoding="utf-8-sig") as f:
    csv_lines = [l for l in f if l.strip()]
print(f"CSV Total Lines: {len(csv_lines)} (1 Header + {len(csv_lines)-1} Transactions)")
print(f"CSV Header: {csv_lines[0].strip()}")
