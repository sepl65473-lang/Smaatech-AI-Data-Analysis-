import requests

with open('active_session_id.txt') as f:
    sid = f.read().strip()
r = requests.get(f'http://127.0.0.1:8000/api/results/{sid}')
data = r.json()
txns = data.get('transactions', [])
debits = [t for t in txns if t['amount'] < 0]
credits = [t for t in txns if t['amount'] > 0]

all_party_freq = {}
for t in txns:
    name = t.get('counterparty') or t.get('merchant') or ''
    if name:
        all_party_freq[name] = all_party_freq.get(name, 0) + 1

repeated_all = [t for t in txns if all_party_freq.get(t.get('counterparty') or t.get('merchant') or '', 0) > 1]
print('repeated_all count:', len(repeated_all))
print('repeated_all total (abs):', sum(abs(t['amount']) for t in repeated_all))

cr_in_repeat = [t for t in repeated_all if t['amount'] > 0]
dr_in_repeat = [t for t in repeated_all if t['amount'] < 0]
print(f'Credits in repeated set: {len(cr_in_repeat)}, sum = {sum(t["amount"] for t in cr_in_repeat):,.2f}')
print(f'Debits in repeated set:  {len(dr_in_repeat)}, sum = {sum(abs(t["amount"]) for t in dr_in_repeat):,.2f}')

print('\nCredits included in repeated set:')
for c in cr_in_repeat:
    print(f'  ID: {c["id"]} | Date: {c["date"]} | Amount: INR {c["amount"]:,.2f} | Party: {c.get("counterparty") or c.get("merchant")}')

print('\nTop recurring debit payees:')
dr_party_totals = {}
dr_party_counts = {}
for t in dr_in_repeat:
    name = t.get('counterparty') or t.get('merchant') or 'Unknown'
    dr_party_totals[name] = dr_party_totals.get(name, 0) + abs(t['amount'])
    dr_party_counts[name] = dr_party_counts.get(name, 0) + 1

for name, tot in sorted(dr_party_totals.items(), key=lambda x: x[1], reverse=True)[:10]:
    print(f'  {name:25s}: {dr_party_counts[name]} transfers | total = INR {tot:10,.2f}')
