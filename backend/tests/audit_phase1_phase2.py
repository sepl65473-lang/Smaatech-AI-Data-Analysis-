import io
import os
import sys
from decimal import Decimal
import pdfplumber

sys.path.insert(0, os.path.abspath("."))
from app.services.ingestion import extract_transactions
from app.services.cleaner import clean_transactions

pdf_path = os.path.abspath("tests/axis_june_2023_original.pdf")

with open(pdf_path, "rb") as f:
    pdf_bytes = f.read()

print("="*60)
print("AUDIT: PAGE BY PAGE INSPECTION OF ORIGINAL PDF")
print("="*60)

with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
    print(f"Total Pages in PDF: {len(pdf.pages)}")
    for i, page in enumerate(pdf.pages, 1):
        tables = page.extract_tables()
        text = page.extract_text() or ""
        lines = [l for l in text.split("\n") if l.strip()]
        dated_lines = [l for l in lines if l[:10].replace("-", "").isdigit() or "OPENING BALANCE" in l or "CLOSING BALANCE" in l]
        print(f"Page {i}: {len(tables)} tables found. Text lines: {len(lines)}. Dated/Balance lines: {len(dated_lines)}")
        if tables:
            for t_idx, t in enumerate(tables):
                print(f"  Table {t_idx+1}: {len(t)} rows, {len(t[0]) if t else 0} cols")

raw_rows = extract_transactions(pdf_bytes, "axis_june_2023_original.pdf")
print(f"\nRaw rows extracted by ingestion: {len(raw_rows)}")

cleaned, warnings = clean_transactions(raw_rows)
print(f"Cleaned transactions: {len(cleaned)}")
print(f"Warnings: {len(warnings)}")
for w in warnings:
    print("  Warning:", w)

credits = [t for t in cleaned if t.amount > 0]
debits = [t for t in cleaned if t.amount < 0]

print(f"\nCredit count: {len(credits)}")
print(f"Debit count: {len(debits)}")

# Verify all transactions have balance
missing_bal = [t for t in cleaned if t.balance is None]
print(f"Transactions missing balance: {len(missing_bal)}")

# Verify debit/credit sign handling
wrong_signs = []
for t in cleaned:
    if t.amount == 0:
        wrong_signs.append(t)
print(f"Zero amount transactions: {len(wrong_signs)}")

# Decimal-safe reconciliation
tot_cr = sum(Decimal(str(t.amount)) for t in credits)
tot_db = sum(Decimal(str(abs(t.amount))) for t in debits)
net = tot_cr - tot_db

first_t = cleaned[0]
last_t = cleaned[-1]
first_bal = Decimal(str(first_t.balance))
last_bal = Decimal(str(last_t.balance))

# Opening balance = first balance - amount (if credit) or + abs(amount) (if debit)
calc_opening = first_bal + Decimal(str(abs(first_t.amount))) if first_t.amount < 0 else first_bal - Decimal(str(first_t.amount))
calc_closing = last_bal

reconciled = calc_opening + tot_cr - tot_db
variance = reconciled - calc_closing

print("\n" + "="*60)
print("FINANCIAL TOTALS (DECIMAL PRECISION)")
print("="*60)
print(f"Opening Balance : {calc_opening}")
print(f"Total Credits   : {tot_cr}")
print(f"Total Debits    : {tot_db}")
print(f"Net Cash Flow   : {net}")
print(f"Closing Balance : {calc_closing}")
print(f"Reconciled Bal  : {reconciled}")
print(f"Variance        : {variance}")

# Check running balance continuity across EVERY row
continuity_breaks = []
prev_bal = calc_opening
for idx, t in enumerate(cleaned, 1):
    amt = Decimal(str(t.amount))
    expected_cur_bal = prev_bal + amt
    actual_cur_bal = Decimal(str(t.balance))
    if expected_cur_bal != actual_cur_bal:
        continuity_breaks.append((idx, t.date, t.description, prev_bal, amt, actual_cur_bal, expected_cur_bal))
    prev_bal = actual_cur_bal

print(f"\nRunning balance continuity breaks: {len(continuity_breaks)}")
for b in continuity_breaks:
    print(f"  Break at row {b[0]}: prev={b[3]}, amt={b[4]}, actual={b[5]}, expected={b[6]}")

# Check reference numbers extracted
refs_found = sum(1 for t in cleaned if t.reference_no)
print(f"\nTransactions with extracted reference numbers: {refs_found}/{len(cleaned)}")

# Let's inspect all 9 credit transactions
print("\n--- ALL 9 CREDIT TRANSACTIONS ---")
for i, t in enumerate(credits, 1):
    print(f"  [{i}] {t.date} | Rs. {t.amount:,.2f} | Bal: {t.balance:,.2f} | Ref: {t.reference_no} | {t.description}")
