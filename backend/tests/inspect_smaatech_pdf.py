import pypdf
import csv
from decimal import Decimal

pdf_path = r'D:\attedance\bank transaction\SMAATECH_Transaction_Analysis_Report_Jun2023.pdf'
reader = pypdf.PdfReader(pdf_path)

with open('smaatech_extracted.txt', 'w', encoding='utf-8') as out:
    out.write(f"Total Pages: {len(reader.pages)}\n")
    for i, page in enumerate(reader.pages):
        out.write(f"\n--- PAGE {i+1} ---\n")
        out.write(page.extract_text() or "")

# Also inspect bank transaction.csv
csv_path = r'D:\attedance\bank transaction\bank transaction.csv'
with open(csv_path, 'r', encoding='utf-8') as f:
    lines = [line.strip().strip('"') for line in f if line.strip()]

reader = csv.DictReader(lines)
rows = list(reader)

with open('smaatech_csv_summary.txt', 'w', encoding='utf-8') as out:
    out.write(f"CSV Total Rows: {len(rows)}\n")
    credits = [r for r in rows if Decimal(r['Credit_INR']) > 0]
    debits = [r for r in rows if Decimal(r['Debit_INR']) > 0]
    tot_cr = sum(Decimal(r['Credit_INR']) for r in rows)
    tot_db = sum(Decimal(r['Debit_INR']) for r in rows)
    net = tot_cr - tot_db
    out.write(f"Credits count: {len(credits)}\n")
    out.write(f"Debits count: {len(debits)}\n")
    out.write(f"Total Credits: {tot_cr}\n")
    out.write(f"Total Debits: {tot_db}\n")
    out.write(f"Net Cash Flow: {net}\n")
    out.write(f"Opening Balance: {Decimal(rows[0]['Running_Balance_INR']) + Decimal(rows[0]['Debit_INR']) - Decimal(rows[0]['Credit_INR'])}\n")
    out.write(f"Closing Balance: {rows[-1]['Running_Balance_INR']}\n")

print("Inspection output written to files.")
