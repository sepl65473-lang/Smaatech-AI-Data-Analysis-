"""
Financial Accuracy & Calculation Verification Suite.

Tests financial calculations, debit/credit parsing, reconciliation,
category breakdowns, top counterparties, and the June 2023 benchmark statement.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
import pytest

from app.models.transaction import Transaction
from app.models.result import AnalysisResult
from app.services.cleaner import _parse_amount, _clean_description
from app.services.metrics import compute_metrics, build_category_summary
from app.services.deliverables.dataset import build_report_dataset


class TestAmountAndSignParsing:
    """Tests that debit and credit amounts and sign indicators are parsed strictly."""

    def test_dr_sign_and_negative_prefix(self):
        # Ingestion may prefix '-' for debit columns while bank text has 'Dr'
        assert _parse_amount("-500.00 Dr") == -500.0
        assert _parse_amount("500.00 Dr") == -500.0
        assert _parse_amount("-500.00") == -500.0
        assert _parse_amount("(500.00)") == -500.0
        assert _parse_amount("500.00-") == -500.0

    def test_cr_sign_and_positive_prefix(self):
        assert _parse_amount("4548780.00 Cr") == 4548780.0
        assert _parse_amount("4548780.00") == 4548780.0
        assert _parse_amount("+4548780.00") == 4548780.0
        assert _parse_amount("45,48,780.00 Cr") == 4548780.0

    def test_invalid_amounts(self):
        assert _parse_amount("") is None
        assert _parse_amount("N/A") is None
        assert _parse_amount("None") is None


class TestReferenceAndNoiseExtraction:
    """Tests reference number extraction and noise stripping."""

    def test_utr_preservation(self):
        desc, merchant, ref = _clean_description("UPI/317512345678/PAYMENT TO MERCHANT")
        assert ref == "317512345678"
        assert "Payment To Merchant" in desc

    def test_cheque_preservation(self):
        desc, merchant, ref = _clean_description("CHQ NO 654321 ISSUED TO VENDOR")
        assert ref == "654321"

    def test_neft_preservation(self):
        desc, merchant, ref = _clean_description("NEFT UTR HDFC000123456 SALARY")
        assert ref == "HDFC000123456"


class TestJune2023BenchmarkAccuracy:
    """
    Validates dynamic calculations against the canonical June 2023 statement expectations:
    - Total transactions: 162
    - Credits: 9, totaling ₹45,48,780.00
    - Debits: 153, totaling ₹46,26,410.00
    - Net cash flow: -₹77,630.00
    """

    @pytest.fixture
    def june_2023_transactions(self):
        # Construct synthetic benchmark matching the exact 162 transactions
        txns = []
        # 9 credits = 45,48,780.00
        # e.g., 8 credits of 5,00,000.00 and 1 credit of 5,48,780.00
        running_bal = Decimal("100000.00")  # Opening balance
        for i in range(8):
            amt = Decimal("500000.00")
            running_bal += amt
            txns.append(
                Transaction(
                    id=f"tx-cr-{i+1}",
                    date=date(2023, 6, i + 1),
                    description=f"Client Inward Remittance Client-{i+1}",
                    clean_description=f"Client Inward Remittance Client-{i+1}",
                    amount=float(amt),
                    category="Income",
                    balance=float(running_bal),
                    reference_no=f"UTRCR{1000+i}",
                )
            )
        # 9th credit
        amt = Decimal("548780.00")
        running_bal += amt
        txns.append(
            Transaction(
                id="tx-cr-9",
                date=date(2023, 6, 9),
                description="Final Client Settlement",
                clean_description="Final Client Settlement",
                amount=float(amt),
                category="Income",
                balance=float(running_bal),
                reference_no="UTRCR1009",
            )
        )

        # 153 debits = 46,26,410.00
        # 152 debits of 30,000.00 = 45,60,000.00, and 1 debit of 66,410.00 = 46,26,410.00
        for i in range(152):
            amt = Decimal("30000.00")
            running_bal -= amt
            day = (i % 20) + 10
            txns.append(
                Transaction(
                    id=f"tx-db-{i+1}",
                    date=date(2023, 6, day),
                    description=f"Vendor Operational Payment #{i+1}",
                    clean_description=f"Vendor Operational Payment #{i+1}",
                    amount=float(-amt),
                    category="Operations" if i % 2 == 0 else "Utilities",
                    balance=float(running_bal),
                    reference_no=f"UTROS{2000+i}",
                )
            )
        # 153rd debit
        amt = Decimal("66410.00")
        running_bal -= amt
        txns.append(
            Transaction(
                id="tx-db-153",
                date=date(2023, 6, 30),
                description="Monthly Office Rent & Facility",
                clean_description="Monthly Office Rent & Facility",
                amount=float(-amt),
                category="Rent",
                balance=float(running_bal),
                reference_no="UTROS2153",
            )
        )

        return txns

    def test_metrics_match_june_expectations(self, june_2023_transactions):
        assert len(june_2023_transactions) == 162

        metrics = compute_metrics(june_2023_transactions)

        assert metrics.transaction_count == 162
        assert metrics.credit_count == 9
        assert metrics.debit_count == 153

        # Critical financial expectations
        assert metrics.total_income == pytest.approx(4548780.0, rel=1e-5)
        assert metrics.total_spend == pytest.approx(4626410.0, rel=1e-5)
        assert metrics.savings == pytest.approx(-77630.0, rel=1e-5)

        # Opening and closing balance
        assert metrics.opening_balance == 100000.0
        assert metrics.closing_balance == pytest.approx(100000.0 - 77630.0, rel=1e-5)
        assert metrics.is_reconciled is True
        assert abs(metrics.reconciliation_delta) < 0.01

        # Averages & largest
        assert metrics.avg_credit_amount == pytest.approx(4548780.0 / 9, rel=1e-5)
        assert metrics.avg_debit_amount == pytest.approx(4626410.0 / 153, rel=1e-5)
        assert metrics.largest_credit.amount == 548780.0
        assert metrics.largest_debit.amount == -66410.0

    def test_verified_dataset_consistency(self, june_2023_transactions):
        metrics = compute_metrics(june_2023_transactions)
        cat_summary = build_category_summary(june_2023_transactions)

        res = AnalysisResult(
            session_id="test-june-session",
            transactions=june_2023_transactions,
            metrics=metrics,
            insights=["June cash flow analyzed."],
            category_summary=cat_summary,
            recurring_summary=[],
            ai_enabled=False,
            insights_source="rules",
        )

        dataset = build_report_dataset(res.model_dump(mode="json"))
        kpis = dataset["kpis"]

        assert kpis["transaction_count"] == 162
        assert kpis["credit_count"] == 9
        assert kpis["debit_count"] == 153
        assert kpis["total_income"] == 4548780.0
        assert kpis["total_expense"] == 4626410.0
        assert kpis["net"] == -77630.0
        assert kpis["opening_balance"] == 100000.0
        assert kpis["closing_balance"] == 22370.0
        assert dataset["meta"]["period_key"] == "2023-06"
        assert len(dataset["audit_log"]) > 0

    def test_original_axis_bank_pdf_extraction_and_deliverables(self):
        """Extract transactions directly from original Axis Bank PDF and verify metrics and deliverables."""
        import os
        from app.services.ingestion import extract_transactions
        from app.services.cleaner import clean_transactions
        from app.services.deliverables.pdf_report import build_pdf
        from app.services.deliverables.excel_report import build_xlsx
        from app.services.deliverables.html_dashboard import build_html_dashboard

        pdf_path = os.path.join(os.path.dirname(__file__), "axis_june_2023_original.pdf")
        assert os.path.exists(pdf_path), "Original Axis Bank PDF must exist"

        with open(pdf_path, "rb") as f:
            raw_bytes = f.read()

        raw_rows = extract_transactions(raw_bytes, "axis_june_2023_original.pdf")
        assert len(raw_rows) == 162

        txns, warnings = clean_transactions(raw_rows)
        assert len(txns) == 162
        assert len(warnings) == 0

        metrics = compute_metrics(txns)
        assert metrics.transaction_count == 162
        assert metrics.credit_count == 9
        assert metrics.debit_count == 153
        assert metrics.total_income == pytest.approx(4548780.0, rel=1e-5)
        assert metrics.total_spend == pytest.approx(4626410.0, rel=1e-5)
        assert metrics.savings == pytest.approx(-77630.0, rel=1e-5)
        assert metrics.opening_balance == pytest.approx(115915.26, rel=1e-5)
        assert metrics.closing_balance == pytest.approx(38285.26, rel=1e-5)
        assert metrics.is_reconciled is True
        assert metrics.reconciliation_delta == pytest.approx(0.0, abs=1e-2)

        # Generate all 3 deliverables from the actual original bank PDF dataset
        cat_summary = build_category_summary(txns)
        res = AnalysisResult(
            session_id="original-axis-session",
            transactions=txns,
            metrics=metrics,
            insights=["Analysis derived from original Axis statement."],
            category_summary=cat_summary,
            recurring_summary=[],
            ai_enabled=False,
            insights_source="rules",
        )
        dataset = build_report_dataset(res.model_dump(mode="json"))

        # Verify PDF
        pdf_bytes = build_pdf(dataset)
        assert pdf_bytes.startswith(b"%PDF-")
        assert len(pdf_bytes) > 50000

        # Verify Excel
        xlsx_bytes, meta = build_xlsx(dataset)
        assert len(xlsx_bytes) > 20000

        # Verify HTML
        html_str = build_html_dashboard(dataset)
        assert "4548780" in html_str
        assert "4626410" in html_str
        assert "const REPORT_DATA =" in html_str
