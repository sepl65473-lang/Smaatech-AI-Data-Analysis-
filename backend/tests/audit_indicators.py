"""
Deep audit of the 6 Transaction Intelligence indicators on Axis Bank June 2023 statement
via the real API pipeline and canonical dataset.
"""
import sys
import os
import requests
import json
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")

pdf_path = "tests/axis_june_2023_original.pdf"
print("Uploading original Axis Bank June 2023 PDF to API...")
with open(pdf_path, "rb") as f:
    up = requests.post("http://127.0.0.1:8000/api/upload", files={"file": ("axis_june_2023_original.pdf", f, "application/pdf")})
assert up.status_code == 200, f"Upload failed: {up.text}"
session_id = up.json()["session_id"]
with open("active_session_id.txt", "w") as f:
    f.write(session_id)
print(f"Session established: {session_id}")

res = requests.get(f"http://127.0.0.1:8000/api/results/{session_id}").json()
txns = res["transactions"]
metrics = res["metrics"]

print(f"\nTotal Transactions: {len(txns)}")
debits = [t for t in txns if t["amount"] < 0]
credits = [t for t in txns if t["amount"] > 0]
total_dr = sum(abs(t["amount"]) for t in debits)
total_cr = sum(t["amount"] for t in credits)
print(f"Debits: {len(debits)}, Total Dr: INR {total_dr:,.2f}")
print(f"Credits: {len(credits)}, Total Cr: INR {total_cr:,.2f}")
print(f"Opening Balance: INR {metrics['opening_balance']:,.2f}")
print(f"Closing Balance: INR {metrics['closing_balance']:,.2f}")
print(f"Reconciled: {metrics['is_reconciled']} (Delta: INR {metrics['reconciliation_delta']:,.2f})")

# Check Category Breakdown
print("\n=== EXPENSE CATEGORY DISTRIBUTION (IMPROVED NARRATION RULES) ===")
cat_sums = defaultdict(float)
cat_counts = defaultdict(int)
for t in debits:
    cat = t.get("category", "Other")
    cat_sums[cat] += abs(t["amount"])
    cat_counts[cat] += 1

for cat, amt in sorted(cat_sums.items(), key=lambda x: x[1], reverse=True):
    pct = (amt / total_dr) * 100
    print(f"  {cat:<15}: INR {amt:>12,.2f} ({pct:>5.1f}%) | {cat_counts[cat]:>3} txns")

# 1. High-value transfers (abs(amount) >= 100,000)
high_val_debits = [t for t in debits if abs(t["amount"]) >= 100000]
high_val_credits = [t for t in credits if t["amount"] >= 100000]
print("\n=== 1. HIGH-VALUE TRANSFERS (>= 1,00,000) ===")
print(f"Detection Rule: abs(amount) >= 100,000.00")
print(f"Distinct Debits: {len(high_val_debits)}, Total Dr: INR {sum(abs(t['amount']) for t in high_val_debits):,.2f}")
print(f"Distinct Credits: {len(high_val_credits)}, Total Cr: INR {sum(t['amount'] for t in high_val_credits):,.2f}")
print("Debit records:")
for t in high_val_debits:
    print(f"  ID: {t['id']} | Date: {t['date'][:10]} | Amount: INR {abs(t['amount']):>10,.2f} | Party: {t.get('counterparty')} | Narration: {t.get('description', '')[:35]}")
print("Credit records:")
for t in high_val_credits:
    print(f"  ID: {t['id']} | Date: {t['date'][:10]} | Amount: INR {t['amount']:>10,.2f} | Party: {t.get('counterparty')} | Narration: {t.get('description', '')[:35]}")

# 2. Recurring payees (Debits only, >= 2 transfers to same counterparty)
debit_party_counts = defaultdict(list)
for t in debits:
    p = t.get("counterparty") or t.get("merchant") or "Unknown"
    debit_party_counts[p].append(t)

recurring_debits = []
print("\n=== 2. RECURRING PAYEES (DEBITS ONLY, >= 2 TRANSFERS) ===")
print("Detection Rule: Counterparty received >= 2 debit disbursements in the statement period.")
for p, p_txns in sorted(debit_party_counts.items(), key=lambda x: len(x[1]), reverse=True):
    if len(p_txns) >= 2:
        recurring_debits.extend(p_txns)
        print(f"  Payee: '{p:<20}' | Count: {len(p_txns):>2} | Total Dr: INR {sum(abs(t['amount']) for t in p_txns):>10,.2f}")

print(f"Total Recurring Debits Count: {len(recurring_debits)} distinct txns")
print(f"Total Recurring Debits Amount: INR {sum(abs(t['amount']) for t in recurring_debits):,.2f} ({(sum(abs(t['amount']) for t in recurring_debits)/total_dr)*100:.1f}% of total debits)")

# Recurring remitters (Credits only, >= 2 transfers from same counterparty)
credit_party_counts = defaultdict(list)
for t in credits:
    p = t.get("counterparty") or t.get("merchant") or "Unknown"
    credit_party_counts[p].append(t)

recurring_credits = []
print("\n=== RECURRING CLIENT REMITTERS (CREDITS ONLY, >= 2 TRANSFERS) ===")
print("Detection Rule: Counterparty credited >= 2 deposits in the statement period.")
for p, p_txns in sorted(credit_party_counts.items(), key=lambda x: len(x[1]), reverse=True):
    if len(p_txns) >= 2:
        recurring_credits.extend(p_txns)
        print(f"  Remitter: '{p:<20}' | Count: {len(p_txns):>2} | Total Cr: INR {sum(t['amount'] for t in p_txns):>10,.2f}")

print(f"Total Recurring Credits Count: {len(recurring_credits)} distinct txns")
print(f"Total Recurring Credits Amount: INR {sum(t['amount'] for t in recurring_credits):,.2f} ({(sum(t['amount'] for t in recurring_credits)/total_cr)*100:.1f}% of total credits)")

# 3. Potential duplicate pairs (same date + same amount)
date_amt_groups = defaultdict(list)
for t in txns:
    d_str = t["date"][:10]
    k = (d_str, t["amount"])
    date_amt_groups[k].append(t)

dup_groups = {k: v for k, v in date_amt_groups.items() if len(v) > 1}
dup_txns = [t for group in dup_groups.values() for t in group]
dup_debits = [t for t in dup_txns if t["amount"] < 0]
dup_credits = [t for t in dup_txns if t["amount"] > 0]
print("\n=== 3. POTENTIAL DUPLICATE PAIRS / SAME-DAY MATCHES ===")
print("Detection Rule: Same calendar day (YYYY-MM-DD) AND exact matching signed amount.")
print(f"Total Duplicate Groups: {len(dup_groups)}")
print(f"Total Matching Transactions: {len(dup_txns)} (Debits: {len(dup_debits)}, Credits: {len(dup_credits)})")
print(f"Total Debit Amount: INR {sum(abs(t['amount']) for t in dup_debits):,.2f}")
print(f"Total Credit Amount: INR {sum(t['amount'] for t in dup_credits):,.2f}")
for (d, amt), group in sorted(dup_groups.items(), key=lambda x: x[0][0]):
    print(f"  Date: {d} | Amount: INR {abs(amt):>8,.2f} | Count: {len(group)}")
    for t in group:
        print(f"    ID: {t['id']} | Party: {t.get('counterparty')} | Narration: {t.get('description', '')[:35]}")

# 4. Round-number transactions (abs(amount) >= 20000 and abs(amount) % 5000 == 0)
round_debits = [t for t in debits if abs(t["amount"]) >= 20000 and abs(t["amount"]) % 5000 == 0]
round_credits = [t for t in credits if t["amount"] >= 20000 and t["amount"] % 5000 == 0]
print("\n=== 4. ROUND-NUMBER TRANSACTIONS (>= 20k and mod 5k == 0) ===")
print("Detection Rule: abs(amount) >= 20,000 AND abs(amount) % 5,000 == 0.")
print(f"Distinct Debits: {len(round_debits)}, Total Dr: INR {sum(abs(t['amount']) for t in round_debits):,.2f}")
print(f"Distinct Credits: {len(round_credits)}, Total Cr: INR {sum(t['amount'] for t in round_credits):,.2f}")
for t in round_debits[:8]:
    print(f"  Dr ID: {t['id']} | Date: {t['date'][:10]} | Amount: INR {abs(t['amount']):>8,.2f} | Party: {t.get('counterparty')}")
for t in round_credits:
    print(f"  Cr ID: {t['id']} | Date: {t['date'][:10]} | Amount: INR {t['amount']:>8,.2f} | Party: {t.get('counterparty')}")

# 5. Weekend banking activity (Saturday or Sunday)
from datetime import datetime
def is_weekend(d_str):
    dt = datetime.fromisoformat(d_str[:10])
    return dt.weekday() in (5, 6)

weekend_debits = [t for t in debits if is_weekend(t["date"])]
weekend_credits = [t for t in credits if is_weekend(t["date"])]
print("\n=== 5. WEEKEND ACTIVITY (SATURDAY OR SUNDAY) ===")
print("Detection Rule: Transaction post date falls on Saturday (weekday 5) or Sunday (weekday 6).")
print(f"Distinct Debits: {len(weekend_debits)}, Total Dr: INR {sum(abs(t['amount']) for t in weekend_debits):,.2f}")
print(f"Distinct Credits: {len(weekend_credits)}, Total Cr: INR {sum(t['amount'] for t in weekend_credits):,.2f}")
for t in weekend_debits[:6]:
    dt = datetime.fromisoformat(t["date"][:10])
    print(f"  Dr ID: {t['id']} | Date: {t['date'][:10]} ({dt.strftime('%A')}) | Amount: INR {abs(t['amount']):>8,.2f} | Party: {t.get('counterparty')}")

# 6. Missing UTR references
missing_ref_debits = [t for t in debits if not t.get("reference_no")]
missing_ref_credits = [t for t in credits if not t.get("reference_no")]
print("\n=== 6. MISSING UTR REFERENCES ===")
print("Detection Rule: reference_no field is empty, null, or whitespace.")
print(f"Distinct Debits: {len(missing_ref_debits)}, Total Dr: INR {sum(abs(t['amount']) for t in missing_ref_debits):,.2f}")
print(f"Distinct Credits: {len(missing_ref_credits)}, Total Cr: INR {sum(t['amount'] for t in missing_ref_credits):,.2f}")
for t in missing_ref_debits[:6]:
    print(f"  Dr ID: {t['id']} | Date: {t['date'][:10]} | Amount: INR {abs(t['amount']):>8,.2f} | Party: {t.get('counterparty')} | Narration: {t.get('description', '')[:35]}")
for t in missing_ref_credits:
    print(f"  Cr ID: {t['id']} | Date: {t['date'][:10]} | Amount: INR {t['amount']:>8,.2f} | Party: {t.get('counterparty')} | Narration: {t.get('description', '')[:35]}")
