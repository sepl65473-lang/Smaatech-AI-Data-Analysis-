"""
test_duplicate_detection.py
Explicitly verifies three-tier duplicate detection:
1. Exact Duplicate UTR / Reference detection.
2. Potential Duplicate Payment detection (same date, signed amount, normalized counterparty),
   specifically verifying that payments with DIFFERENT UTRs are properly detected.
3. Informational Same-Day Same-Amount Batch Payment detection.
"""

from datetime import date
from app.models.transaction import Transaction
from app.services.metrics import compute_metrics


def test_three_tier_duplicate_detection():
    # 1. Test case: Two payments to SAME counterparty, on SAME date, SAME amount, but DIFFERENT UTRs
    t1 = Transaction(
        id="txn_1",
        seq=1,
        date=date(2023, 6, 15),
        description="NEFT to Manoj Sharma",
        clean_description="NEFT to Manoj Sharma",
        amount=-50000.0,
        debit=50000.0,
        credit=0.0,
        balance=100000.0,
        category="Other",
        counterparty="Manoj Sharma",
        reference_no="UTR11111111",
    )
    t2 = Transaction(
        id="txn_2",
        seq=2,
        date=date(2023, 6, 15),
        description="NEFT to Manoj Sharma duplicate",
        clean_description="NEFT to Manoj Sharma duplicate",
        amount=-50000.0,
        debit=50000.0,
        credit=0.0,
        balance=50000.0,
        category="Other",
        counterparty="Manoj Sharma",
        reference_no="UTR22222222",  # DIFFERENT UTR!
    )

    # 2. Test case: Same day, same amount, but DIFFERENT counterparty (Batch payroll)
    t3 = Transaction(
        id="txn_3",
        seq=3,
        date=date(2023, 6, 15),
        description="NEFT to Dinesh Laybour",
        clean_description="NEFT to Dinesh Laybour",
        amount=-50000.0,
        debit=50000.0,
        credit=0.0,
        balance=0.0,
        category="Other",
        counterparty="Dinesh Laybour",
        reference_no="UTR33333333",
    )

    # 3. Test case: Exact duplicate UTR anomaly
    t4 = Transaction(
        id="txn_4",
        seq=4,
        date=date(2023, 6, 16),
        description="NEFT with duplicate UTR line",
        clean_description="NEFT with duplicate UTR line",
        amount=-20000.0,
        debit=20000.0,
        credit=0.0,
        balance=-20000.0,
        category="Other",
        counterparty="Vendor X",
        reference_no="UTR_DUPLICATE_999",
    )
    t5 = Transaction(
        id="txn_5",
        seq=5,
        date=date(2023, 6, 17),
        description="Second line with same UTR",
        clean_description="Second line with same UTR",
        amount=-20000.0,
        debit=20000.0,
        credit=0.0,
        balance=-40000.0,
        category="Other",
        counterparty="Vendor Y",
        reference_no="UTR_DUPLICATE_999",  # EXACT SAME UTR!
    )

    txns = [t1, t2, t3, t4, t5]
    metrics = compute_metrics(txns)
    intel = metrics.intelligence

    # Tier 1 Verification: Exact Duplicate UTR
    assert intel["exact_duplicate_utr_groups"] == 1
    assert intel["exact_duplicate_utr_count"] == 2

    # Tier 2 Verification: Potential Duplicate Payments with DIFFERENT UTRs
    # t1 and t2 share date (2023-06-15), amount (-50000.0), and counterparty ("manoj sharma")
    # Even though their UTRs are different (UTR11111111 vs UTR22222222), Tier 2 MUST catch them!
    assert intel["potential_duplicate_payment_groups"] == 1
    assert intel["potential_duplicate_payment_count"] == 2
    assert intel["potential_duplicate_payment_spend"] == 100000.0

    # Tier 3 Verification: Same-Day Same-Amount Matches (Informational)
    # On 2023-06-15, all three transactions (t1, t2, t3) share date and -50000.0 amount
    assert intel["same_day_matches_groups"] == 1
    assert intel["same_day_matches_count"] == 3


def test_canonical_axis_statement_duplicate_detection():
    import os
    from app.services.ingestion import extract_transactions
    from app.services.cleaner import clean_transactions
    pdf_path = os.path.join(os.path.dirname(__file__), "axis_june_2023_original.pdf")
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    raw_rows = extract_transactions(pdf_bytes, "axis_june_2023_original.pdf")
    txns, parse_warnings = clean_transactions(raw_rows)
    metrics = compute_metrics(txns)
    intel = metrics.intelligence

    # Tier 1: Canonical dataset has 0 duplicate UTRs
    assert intel["exact_duplicate_utr_groups"] == 0
    assert intel["exact_duplicate_utr_count"] == 0

    # Tier 2: Canonical dataset has 0 potential duplicate payments to the same counterparty
    assert intel["potential_duplicate_payment_groups"] == 0
    assert intel["potential_duplicate_payment_count"] == 0
    assert "No potential duplicates detected under the applied matching rules." in intel["duplicate_detection_status"]

    # Tier 3: Same-Day Same-Amount informational matches (batch payrolls to different workers)
    assert intel["same_day_matches_groups"] == 18
    assert intel["same_day_matches_count"] == 49
    assert intel["same_day_matches_spend"] == 636640.0
