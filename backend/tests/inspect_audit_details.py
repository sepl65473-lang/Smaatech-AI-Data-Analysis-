import json
import requests
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

def main():
    with open("active_session_id.txt") as f:
        sid = f.read().strip()
    
    resp = requests.get(f"http://127.0.0.1:8000/api/results/{sid}")
    assert resp.status_code == 200
    data = resp.json()
    txns = data.get("transactions", [])
    print(f"Total transactions: {len(txns)}")
    
    credits = [t for t in txns if t["amount"] > 0]
    debits = [t for t in txns if t["amount"] < 0]
    total_cr = sum(t["amount"] for t in credits)
    total_dr = sum(abs(t["amount"]) for t in debits)
    print(f"Credits: {len(credits)}, sum: INR {total_cr:,.2f}")
    print(f"Debits:  {len(debits)}, sum: INR {total_dr:,.2f}")
    
    # 1. Investigate Recurring calculation
    print("\n" + "="*60)
    print("AUDIT 1: RECURRING & REPEATED PAYMENTS")
    print("="*60)
    
    # Check debits-only repeated counterparties
    debit_party_freq = {}
    for t in debits:
        name = t.get("counterparty") or t.get("merchant") or ""
        if name:
            debit_party_freq[name] = debit_party_freq.get(name, 0) + 1
            
    repeated_debits = [t for t in debits if debit_party_freq.get(t.get("counterparty") or t.get("merchant") or "", 0) > 1]
    repeated_debits_sum = sum(abs(t["amount"]) for t in repeated_debits)
    print(f"Debits-only repeated counterparties (>1 txn): count={len(repeated_debits)}, sum=INR {repeated_debits_sum:,.2f}")
    
    # Check all transactions (credits + debits) repeated counterparties
    all_party_freq = {}
    for t in txns:
        name = t.get("counterparty") or t.get("merchant") or ""
        if name:
            all_party_freq[name] = all_party_freq.get(name, 0) + 1
    repeated_all = [t for t in txns if all_party_freq.get(t.get("counterparty") or t.get("merchant") or "", 0) > 1]
    repeated_all_sum = sum(abs(t["amount"]) for t in repeated_all)
    print(f"Mixed (Credits+Debits) repeated counterparties: count={len(repeated_all)}, sum=INR {repeated_all_sum:,.2f}")
    
    # Check credits with repeat senders:
    repeat_cr = [t for t in repeated_all if t["amount"] > 0]
    print(f"Credits in repeat set: count={len(repeat_cr)}, sum=INR {sum(t['amount'] for t in repeat_cr):,.2f}")
    for c in repeat_cr:
        print(f"  Credit txn: id={c['id']}, date={c['date']}, amt={c['amount']:,.2f}, party={c.get('counterparty')}")

    # Check recurring_summary from backend (detect_recurring)
    rec_summary = data.get("recurring_summary", [])
    print(f"\nBackend recurring_summary (detect_recurring): {len(rec_summary)} items")
    for r in rec_summary:
        print(f"  Item: {r.get('merchant')} | amount={r.get('amount')} | occurrences={r.get('occurrences')} | freq={r.get('frequency')}")

    # 2. Investigate Category Breakdown and "Other" narrations
    print("\n" + "="*60)
    print("AUDIT 2: CATEGORY BREAKDOWN & 'OTHER' NARRATIONS")
    print("="*60)
    cat_counts = {}
    cat_sums = {}
    for t in debits:
        c = t.get("category", "Other")
        cat_counts[c] = cat_counts.get(c, 0) + 1
        cat_sums[c] = cat_sums.get(c, 0) + abs(t["amount"])

    print("Current Debit Category Breakdown:")
    for c, s in sorted(cat_sums.items(), key=lambda x: x[1], reverse=True):
        print(f"  {c:15s}: count={cat_counts[c]:3d}, total=INR {s:12,.2f} ({s/total_dr*100:5.1f}%)")

    others = [t for t in debits if t.get("category") == "Other"]
    print(f"\nAll {len(others)} 'Other' debit transactions:")
    for i, t in enumerate(others):
        print(f"  {i+1:3d}. [{t['date']}] amt={abs(t['amount']):9.2f} | cp={t.get('counterparty') or t.get('merchant')} | desc={t['clean_description']}")

if __name__ == "__main__":
    main()
