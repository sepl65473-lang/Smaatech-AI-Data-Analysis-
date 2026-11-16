import sys
import os
import json
import zipfile
import io
from decimal import Decimal

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath("."))

from app.services.ingestion import extract_transactions
from app.services.cleaner import clean_transactions
from app.services.categorizer import categorize_transactions
from app.services.recurring_detector import detect_recurring
from app.services.metrics import compute_metrics, build_category_summary
from app.services.insight_generator import generate_insights
from app.models.result import AnalysisResult

from app.services.deliverables.dataset import build_report_dataset
from app.services.deliverables.pdf_report import build_pdf
from app.services.deliverables.excel_report import build_xlsx, build_preview
from app.services.deliverables.html_dashboard import build_html_dashboard
from app.services.report_builder import build_csv_report

pdf_path = os.path.abspath("tests/axis_june_2023_original.pdf")
print("=== PHASE 1: ORIGINAL PDF EXTRACTION ===")
print(f"Target PDF: {pdf_path}")
print(f"File Size: {os.path.getsize(pdf_path):,} bytes")

with open(pdf_path, "rb") as f:
    pdf_bytes = f.read()

# 1. Extraction
raw_rows = extract_transactions(pdf_bytes, filename="TransactionSummary_JUNE 23.pdf")
print(f"Raw Extracted Rows Count: {len(raw_rows)}")

# 2. Pipeline processing
cleaned_txs, clean_warnings = clean_transactions(raw_rows)
categorized_txs, categorizer_used_llm = categorize_transactions(cleaned_txs)
categorized_txs, recurring_items = detect_recurring(categorized_txs)
metrics = compute_metrics(categorized_txs)
cat_summary = build_category_summary(categorized_txs)
insights, insights_source = generate_insights(metrics, cat_summary, recurring_items)

parse_warnings = clean_warnings
print(f"Cleaned Transactions Count: {len(categorized_txs)}")
print(f"Parse Warnings Count: {len(parse_warnings)}")

analysis_res = AnalysisResult(
    session_id="axis-original-june-2023-audit",
    transactions=categorized_txs,
    metrics=metrics,
    insights=insights,
    category_summary=cat_summary,
    recurring_summary=recurring_items,
    parse_warnings=parse_warnings + clean_warnings,
    ai_enabled=False,
    insights_source="fallback",
)

analysis_dict = analysis_res.model_dump()

# Credits & Debits audit
credits = [t for t in categorized_txs if t.amount > 0]
debits = [t for t in categorized_txs if t.amount < 0]
print(f"\nExtracted Credit Count: {len(credits)}")
print(f"Extracted Debit Count: {len(debits)}")
print(f"Total Transactions: {len(categorized_txs)}")

print("\n--- First 3 Transactions Extracted ---")
for i, t in enumerate(categorized_txs[:3]):
    tx_type = "CREDIT" if t.amount > 0 else "DEBIT"
    bal_str = f"Rs. {t.balance:,.2f}" if t.balance is not None else "N/A"
    print(f"  [{i+1}] Date={t.date.strftime('%Y-%m-%d')} | Type={tx_type} | Amount=Rs. {abs(t.amount):,.2f} | Balance={bal_str} | Ref={t.reference_no} | Desc={t.description[:45]}")

print("\n--- Last 3 Transactions Extracted ---")
for i, t in enumerate(categorized_txs[-3:], start=len(categorized_txs)-2):
    tx_type = "CREDIT" if t.amount > 0 else "DEBIT"
    bal_str = f"Rs. {t.balance:,.2f}" if t.balance is not None else "N/A"
    print(f"  [{i}] Date={t.date.strftime('%Y-%m-%d')} | Type={tx_type} | Amount=Rs. {abs(t.amount):,.2f} | Balance={bal_str} | Ref={t.reference_no} | Desc={t.description[:45]}")

# === PHASE 2: FINANCIAL RECONCILIATION ===
print("\n=== PHASE 2: FINANCIAL RECONCILIATION ===")
total_credits = sum(Decimal(str(t.amount)) for t in credits)
total_debits = sum(Decimal(str(abs(t.amount))) for t in debits)
net_cash_flow = total_credits - total_debits

first_t = categorized_txs[0]
last_t = categorized_txs[-1]
first_balance = Decimal(str(first_t.balance))
last_balance = Decimal(str(last_t.balance))

if first_t.amount > 0:
    calculated_opening = first_balance - Decimal(str(first_t.amount))
else:
    calculated_opening = first_balance + Decimal(str(abs(first_t.amount)))

closing_balance = last_balance
reconciled_closing = calculated_opening + total_credits - total_debits
variance = reconciled_closing - closing_balance

print(f"Opening Balance (Derived from Statement): Rs. {calculated_opening:,.2f}")
print(f"Total Credits (9 transactions):          Rs. {total_credits:,.2f}")
print(f"Total Debits (153 transactions):         Rs. {total_debits:,.2f}")
print(f"Net Cash Flow:                           Rs. {net_cash_flow:,.2f}")
print(f"Closing Balance (Final Running Balance): Rs. {closing_balance:,.2f}")
print(f"Reconciled Closing (Opening + Cr - Dr):  Rs. {reconciled_closing:,.2f}")
print(f"Variance (Discrepancy):                  Rs. {variance:,.2f}")
print(f"Reconciliation Status: {'PERFECT RECONCILIATION (0.00)' if variance == Decimal('0.00') else 'RECONCILIATION FAILED'}")

# Verify running balance continuity row by row
running_bal_errors = []
curr = calculated_opening
for idx, t in enumerate(categorized_txs):
    amt = Decimal(str(t.amount)) # Already positive or negative
    curr += amt
    stmt_bal = Decimal(str(t.balance)) if t.balance is not None else None
    if stmt_bal is not None and abs(curr - stmt_bal) > Decimal("0.01"):
        running_bal_errors.append((idx, t.date, t.description[:30], float(curr), float(stmt_bal)))

print(f"Continuous Running Balance Errors: {len(running_bal_errors)}")

# === PHASE 3: DELIVERABLES GENERATION ===
print("\n=== PHASE 3: DELIVERABLES GENERATION ===")
ds = build_report_dataset(analysis_dict)
kpis = ds.get("kpis", {})

print(f"Dataset Verified Status: {ds.get('meta', {}).get('is_reconciled')}")
print(f"Dataset KPI Total Income: Rs. {kpis.get('total_income'):,.2f}")
print(f"Dataset KPI Total Expense: Rs. {kpis.get('total_expense'):,.2f}")
print(f"Dataset KPI Net Cash Flow: Rs. {kpis.get('net'):,.2f}")
print(f"Dataset Transaction Count: {kpis.get('transaction_count')}")

# Generate PDF
pdf_bytes = build_pdf(ds)
print(f"1. PDF Report Generated: {len(pdf_bytes):,} bytes")

# Generate Excel
xlsx_bytes, xlsx_info = build_xlsx(ds)
print(f"2. Excel Workbook Generated: {len(xlsx_bytes):,} bytes | Formulas: {xlsx_info['formula_count']}")

# Generate HTML
html_str = build_html_dashboard(ds)
html_bytes = html_str.encode("utf-8")
print(f"3. Standalone HTML Dashboard Generated: {len(html_bytes):,} bytes")

# Generate CSV
csv_str = build_csv_report(analysis_dict)
csv_bytes = csv_str.encode("utf-8")
print(f"4. Clean CSV Report Generated: {len(csv_bytes):,} bytes")

# Generate ZIP
zip_buffer = io.BytesIO()
with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
    zf.writestr("Financial_Analysis_2023-06.pdf", pdf_bytes)
    zf.writestr("Financial_Analysis_2023-06.xlsx", xlsx_bytes)
    zf.writestr("Financial_Dashboard_2023-06.html", html_bytes)
    zf.writestr("Financial_Transactions_2023-06.csv", csv_bytes)
zip_bytes = zip_buffer.getvalue()
print(f"5. Complete ZIP Package Generated: {len(zip_bytes):,} bytes")

# Verify Excel 7 Sheets
preview_meta = build_preview(xlsx_bytes, xlsx_info)
print(f"\nExcel Preview Verification:")
print(f"Total Sheets in Workbook: {len(preview_meta['sheets'])}")
for s in preview_meta["sheets"]:
    print(f"  - Sheet '{s['name']}': {s['total_rows']} rows, {s['total_cols']} cols, truncated={s['truncated']}, charts={s.get('charts', 0)}")

# Save verified outputs
out_dir = os.path.abspath("tests/artifacts_verification")
os.makedirs(out_dir, exist_ok=True)
with open(os.path.join(out_dir, "Financial_Analysis_2023-06.pdf"), "wb") as f:
    f.write(pdf_bytes)
with open(os.path.join(out_dir, "Financial_Analysis_2023-06.xlsx"), "wb") as f:
    f.write(xlsx_bytes)
with open(os.path.join(out_dir, "Financial_Dashboard_2023-06.html"), "wb") as f:
    f.write(html_bytes)
with open(os.path.join(out_dir, "Financial_Report_Package_2023-06.zip"), "wb") as f:
    f.write(zip_bytes)
with open(os.path.join(out_dir, "Financial_Transactions_2023-06.csv"), "wb") as f:
    f.write(csv_bytes)
print(f"\nAll 5 deliverable files saved to: {out_dir}")
