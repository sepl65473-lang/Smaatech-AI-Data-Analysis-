import requests
from collections import Counter
import re

with open('active_session_id.txt') as f:
    sid = f.read().strip()
r = requests.get(f'http://127.0.0.1:8000/api/results/{sid}')
data = r.json()
txns = data.get('transactions', [])
debits = [t for t in txns if t['amount'] < 0]

print(f"Total debits: {len(debits)}, sum: {sum(abs(t['amount']) for t in debits):,.2f}")

# Group narrations by patterns
patterns = {
    "Labour & Contractor": [],
    "Site & Project Expenses": [],
    "Materials & Supplies": [],
    "Vendor Payments": [],
    "Rent": [],
    "Salary": [],
    "Director Remuneration / Drawings": [],
    "Loan / Advance Repayment": [],
    "Bank Charges / Taxes": [],
    "Cash Withdrawal": [],
    "Unclassified / Other": []
}

for t in debits:
    desc = (t.get('description') or '') + ' ' + (t.get('clean_description') or '')
    d_lower = desc.lower()
    amt = abs(t['amount'])
    
    if re.search(r'labour|laybour|makar\s*labour|pramod\s*labour|dinesh\s*labour|local\s*lab', d_lower):
        patterns["Labour & Contractor"].append(t)
    elif re.search(r'director|manoj|sujata', d_lower):
        patterns["Director Remuneration / Drawings"].append(t)
    elif re.search(r'loan\s*return|advance\s*return', d_lower):
        patterns["Loan / Advance Repayment"].append(t)
    elif re.search(r'payment\s*against\s*sw|flow\s*control|vendor|priyadars|electro\s*tray|panel\s*switchgear', d_lower):
        patterns["Vendor Payments"].append(t)
    elif re.search(r'material|hardware|sand\s*removal|agregate|hard\s*rock|brick|plastering|cable|tray|steel|structure', d_lower):
        patterns["Materials & Supplies"].append(t)
    elif re.search(r'site\s*expense|travellin|travel|factory\s*expense|scaffolding|shuttering', d_lower):
        patterns["Site & Project Expenses"].append(t)
    elif re.search(r'salary|salar', d_lower):
        patterns["Salary"].append(t)
    elif re.search(r'rent|room\s*ren|rental', d_lower):
        patterns["Rent"].append(t)
    elif re.search(r'gst|charges\s*for\s*a\s*c|consolidated\s*charge', d_lower):
        patterns["Bank Charges / Taxes"].append(t)
    elif re.search(r'cash\s*wdl|self', d_lower):
        patterns["Cash Withdrawal"].append(t)
    else:
        patterns["Unclassified / Other"].append(t)

print("\n" + "="*70)
print(f"{'CATEGORY':35s} | {'COUNT':5s} | {'TOTAL AMOUNT':15s} | {'% SPEND':7s}")
print("="*70)
total_dr = sum(abs(t['amount']) for t in debits)
for cat, items in patterns.items():
    tot = sum(abs(t['amount']) for t in items)
    pct = (tot / total_dr) * 100
    print(f"{cat:35s} | {len(items):5d} | INR {tot:12,.2f} | {pct:6.1f}%")

print("\nTransactions left in Unclassified / Other:")
for t in patterns["Unclassified / Other"]:
    print(f"  [{t['date']}] amt={abs(t['amount']):9.2f} | cp={t.get('counterparty') or t.get('merchant')} | desc={t['clean_description']}")
