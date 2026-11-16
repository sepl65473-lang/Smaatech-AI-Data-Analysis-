import requests
import json
import sys

def verify():
    import os
    pdf_path = "tests/axis_june_2023_original.pdf"
    with open(pdf_path, "rb") as f:
        up = requests.post("http://127.0.0.1:8000/api/upload", files={"file": ("axis_june_2023_original.pdf", f, "application/pdf")})
    assert up.status_code == 200, f"Upload failed: {up.text}"
    session_id = up.json()["session_id"]
    with open("active_session_id.txt", "w") as f:
        f.write(session_id)
    
    print(f"Verified active live session: {session_id}")
    res = requests.get(f"http://127.0.0.1:8000/api/results/{session_id}").json()
    metrics = res["metrics"]
    
    print("=" * 60)
    print("AXIS BANK JUNE 2023 CANONICAL VERIFICATION")
    print("=" * 60)
    print(f"Total Transactions: {metrics['transaction_count']}")
    print(f"Credits Count:      {metrics['credit_count']} | Total: INR {metrics['total_income']:,.2f}")
    print(f"Debits Count:       {metrics['debit_count']} | Total: INR {metrics['total_spend']:,.2f}")
    print(f"Net Cash Flow:      INR {metrics['total_income'] - metrics['total_spend']:,.2f}")
    print(f"Opening Balance:    INR {metrics['opening_balance']:,.2f}")
    print(f"Closing Balance:    INR {metrics['closing_balance']:,.2f}")
    print(f"Reconciled:         {metrics['is_reconciled']} (Delta: INR {metrics['reconciliation_delta']:,.2f})")
    print(f"Income/Expense:     {metrics.get('income_to_expense_ratio')}")
    print(f"Top Payees:         {len(metrics.get('top_payees', []))} counterparties")
    print(f"Top Payers:         {len(metrics.get('top_payers', []))} counterparties")
    
    intel = metrics.get('intelligence', {})
    print(f"Intelligence Flags:")
    print(f" - High-Value Outflows:  {len(intel.get('high_value_outflows', []))}")
    print(f" - Repeated Txns:        {len(intel.get('repeated_transactions', []))}")
    print(f" - Weekend Banking:      {len(intel.get('weekend_activity', []))}")
    print(f" - Missing Reference:    {len(intel.get('missing_reference', []))}")
    print(f" - Potential Duplicates: {len(intel.get('potential_duplicates', []))}")
    print(f" - Round Number Txns:    {len(intel.get('round_number_txns', []))}")
    print(f" - Uncategorized Txns:   {len(intel.get('uncategorized', []))}")

    # Check canonical assertions
    assert metrics['transaction_count'] == 162, f"Expected 162 txns, got {metrics['transaction_count']}"
    assert metrics['credit_count'] == 9, f"Expected 9 credits, got {metrics['credit_count']}"
    assert metrics['debit_count'] == 153, f"Expected 153 debits, got {metrics['debit_count']}"
    assert round(metrics['total_income'], 2) == 4548780.00, f"Credits mismatch: {metrics['total_income']}"
    assert round(metrics['total_spend'], 2) == 4626410.00, f"Debits mismatch: {metrics['total_spend']}"
    assert round(metrics['opening_balance'], 2) == 115915.26, f"Opening balance mismatch: {metrics['opening_balance']}"
    assert round(metrics['closing_balance'], 2) == 38285.26, f"Closing balance mismatch: {metrics['closing_balance']}"
    assert metrics['is_reconciled'] is True, f"Expected reconciled=True, got {metrics['is_reconciled']}"
    assert round(metrics['reconciliation_delta'], 2) == 0.00, f"Expected delta 0, got {metrics['reconciliation_delta']}"
    
    print("\n" + "=" * 60)
    print("DELIVERABLES EXPORT CHECK")
    print("=" * 60)
    for fmt in ["html", "pdf", "xlsx", "zip", "csv"]:
        r = requests.get(f"http://127.0.0.1:8000/api/export/{session_id}?format={fmt}")
        assert r.status_code == 200, f"Failed export {fmt}: {r.status_code}"
        assert len(r.content) > 1000, f"Deliverable {fmt} too small: {len(r.content)} bytes"
        print(f"Deliverable [{fmt.upper()}]: OK ({len(r.content):,} bytes)")
        if fmt == "html":
            assert b"Power BI Financial Analytics" in r.content, "HTML missing Power BI branding"
            assert b"const DATA =" in r.content, "HTML missing embedded DATA"
            print("  -> Standalone HTML includes embedded dataset & Power BI modules!")

    print("\nALL CANONICAL CHECKS AND DELIVERABLE EXPORTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    verify()
