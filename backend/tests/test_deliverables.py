"""
Deliverables Verification Suite.

Tests generation, formatting, integrity, and API delivery for:
1. Multi-page Professional PDF Report
2. Advanced 7-Sheet Excel Workbook (.xlsx)
3. Standalone Interactive HTML Dashboard (.html)
4. Complete Report Package (.zip)
5. FastAPI Export Router Integration
"""

from datetime import date, datetime, timezone
import io
import json
import zipfile
import openpyxl
from pypdf import PdfReader
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.models.transaction import Transaction
from app.models.result import AnalysisResult
from app.services.metrics import compute_metrics, build_category_summary
from app.services.deliverables.dataset import build_report_dataset
from app.services.deliverables.pdf_report import build_pdf
from app.services.deliverables.excel_report import build_xlsx, build_preview
from app.services.deliverables.html_dashboard import build_html_dashboard
from app.session.store import session_store


@pytest.fixture
def sample_analysis_result():
    """Generates a rich, canonical analysis result for deliverable testing."""
    txns = [
        Transaction(
            id="tx-1",
            date=date(2023, 6, 1),
            description="Client Advance Payment - TechCorp",
            clean_description="Client Advance Payment - TechCorp",
            amount=500000.0,
            category="Income",
            balance=600000.0,
            reference_no="UTRCR001",
        ),
        Transaction(
            id="tx-2",
            date=date(2023, 6, 5),
            description="Office Cloud Infrastructure AWS",
            clean_description="Office Cloud Infrastructure AWS",
            amount=-25000.0,
            category="Technology",
            balance=575000.0,
            reference_no="UTROS002",
        ),
        Transaction(
            id="tx-3",
            date=date(2023, 6, 12),
            description="Employee Health Group Insurance",
            clean_description="Employee Health Group Insurance",
            amount=-45000.0,
            category="Insurance",
            balance=530000.0,
            reference_no="UTROS003",
        ),
        Transaction(
            id="tx-4",
            date=date(2023, 6, 20),
            description="Consulting Revenue - Alpha Corp",
            clean_description="Consulting Revenue - Alpha Corp",
            amount=350000.0,
            category="Income",
            balance=880000.0,
            reference_no="UTRCR004",
        ),
        Transaction(
            id="tx-5",
            date=date(2023, 6, 28),
            description="Office Rent & Maintenance",
            clean_description="Office Rent & Maintenance",
            amount=-120000.0,
            category="Rent",
            balance=760000.0,
            reference_no="UTROS005",
        ),
    ]

    metrics = compute_metrics(txns)
    cat_summary = build_category_summary(txns)

    return AnalysisResult(
        session_id="test-session-deliverables",
        transactions=txns,
        metrics=metrics,
        insights=["Healthy cash flow with strong net surplus.", "Top expenditure category is Rent."],
        category_summary=cat_summary,
        recurring_summary=[],
        ai_enabled=False,
        insights_source="rules",
        generated_at=datetime.now(timezone.utc),
    )


class TestPdfReportGeneration:
    """Verifies PDF report generation, layout, pagination and headers."""

    def test_pdf_generation_and_structure(self, sample_analysis_result):
        dataset = build_report_dataset(sample_analysis_result.model_dump(mode="json"))
        pdf_bytes = build_pdf(dataset)

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 5000
        assert pdf_bytes.startswith(b"%PDF-")

        # Read back with pypdf
        reader = PdfReader(io.BytesIO(pdf_bytes))
        assert len(reader.pages) >= 2  # Multi-page requirement

        # Extract text from first page
        page1_text = reader.pages[0].extract_text()
        assert "EXECUTIVE SUMMARY" in page1_text or "FINANCIAL" in page1_text

        # Verify transaction table page contains headers
        all_text = "".join(page.extract_text() for page in reader.pages)
        assert "Debit" in all_text
        assert "Credit" in all_text
        assert "Balance" in all_text


class TestExcelWorkbookGeneration:
    """Verifies 7-sheet Excel generation, formulas, formatting, and preview."""

    EXPECTED_SHEETS = [
        "Executive Summary",
        "Complete Transactions",
        "Income and Expenses",
        "Category Analysis",
        "Daily and Weekly Analysis",
        "Monthly Analysis",
        "Reconciliation and Audit Log",
    ]

    def test_all_seven_sheets_exist(self, sample_analysis_result):
        dataset = build_report_dataset(sample_analysis_result.model_dump(mode="json"))
        xlsx_bytes, meta = build_xlsx(dataset)

        assert isinstance(xlsx_bytes, bytes)
        assert len(xlsx_bytes) > 5000

        # Load with openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes), data_only=False)
        sheet_names = wb.sheetnames

        for expected in self.EXPECTED_SHEETS:
            assert expected in sheet_names, f"Missing required sheet: {expected}"

    def test_excel_formulas_and_structure(self, sample_analysis_result):
        dataset = build_report_dataset(sample_analysis_result.model_dump(mode="json"))
        xlsx_bytes, meta = build_xlsx(dataset)
        wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes), data_only=False)

        # Check Complete Transactions sheet
        ws_tx = wb["Complete Transactions"]
        headers = [cell.value for cell in ws_tx[1]]
        assert any("Date" in str(h) for h in headers)
        assert any("Debit" in str(h) for h in headers)
        assert any("Credit" in str(h) for h in headers)
        assert any("Balance" in str(h) for h in headers)

        # Verify frozen panes
        assert ws_tx.freeze_panes is not None

        # Check formulas exist in sheets
        formula_found = False
        for name in ["Category Analysis", "Executive Summary", "Income and Expenses"]:
            ws = wb[name]
            for row in ws.iter_rows(values_only=False):
                for cell in row:
                    if isinstance(cell.value, str) and cell.value.startswith("="):
                        formula_found = True
                        break
                if formula_found:
                    break
            if formula_found:
                break
        assert formula_found, "Expected native Excel formula in workbook"

    def test_workbook_preview_builder(self, sample_analysis_result):
        dataset = build_report_dataset(sample_analysis_result.model_dump(mode="json"))
        xlsx_bytes, meta = build_xlsx(dataset)
        preview = build_preview(xlsx_bytes, meta)

        assert "sheets" in preview
        assert len(preview["sheets"]) == 7
        for sheet_info in preview["sheets"]:
            assert "name" in sheet_info
            assert "rows" in sheet_info
            assert len(sheet_info["rows"]) > 0


class TestStandaloneHtmlDashboard:
    """Verifies self-contained offline HTML dashboard generation."""

    def test_html_dashboard_offline_integrity(self, sample_analysis_result):
        dataset = build_report_dataset(sample_analysis_result.model_dump(mode="json"))
        html_content = build_html_dashboard(dataset)

        assert isinstance(html_content, str)
        assert "<!DOCTYPE html>" in html_content
        assert "Dashboard" in html_content

        # Verify safe JSON embedding
        assert "const REPORT_DATA =" in html_content
        assert "850000" in html_content

        # Verify NO backend URL dependencies or localhost fetch calls
        assert "http://localhost" not in html_content
        assert "fetch(" not in html_content
        assert "api/" not in html_content

        # Verify security: no secrets/keys leaked
        assert "GEMINI_API_KEY" not in html_content
        assert "GROQ_API_KEY" not in html_content
        assert "sk-" not in html_content


class TestExportApiEndpoints:
    """Tests the /api/export/{session_id} endpoints with all formats."""

    @pytest.fixture(autouse=True)
    def setup_session(self, sample_analysis_result):
        import time
        session_store._store["test-session-deliverables"] = {
            "data": sample_analysis_result.model_dump(mode="json"),
            "expires_at": time.time() + 3600,
        }
        yield
        session_store.delete("test-session-deliverables")

    def test_export_status_endpoint(self):
        client = TestClient(app)
        resp = client.get("/api/export/test-session-deliverables/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"
        assert "pdf" in data["filenames"]
        assert "xlsx" in data["filenames"]
        assert "html" in data["filenames"]
        assert "zip" in data["filenames"]

    def test_export_pdf_download_and_preview(self):
        client = TestClient(app)
        # Download
        resp = client.get("/api/export/test-session-deliverables?format=pdf")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert "attachment" in resp.headers["content-disposition"]
        assert resp.content.startswith(b"%PDF-")

        # Preview
        resp_prev = client.get("/api/export/test-session-deliverables?format=pdf&preview=true")
        assert resp_prev.status_code == 200
        assert resp_prev.headers["content-type"] == "application/pdf"
        assert "inline" in resp_prev.headers["content-disposition"]

    def test_export_excel_download_and_preview(self):
        client = TestClient(app)
        resp = client.get("/api/export/test-session-deliverables?format=xlsx")
        assert resp.status_code == 200
        assert "spreadsheetml" in resp.headers["content-type"]
        assert "attachment" in resp.headers["content-disposition"]

        # Preview JSON endpoint
        resp_prev = client.get("/api/export/test-session-deliverables?format=xlsx&preview=true")
        assert resp_prev.status_code == 200
        assert resp_prev.headers["content-type"].startswith("application/json")
        data = resp_prev.json()
        assert "sheets" in data
        assert len(data["sheets"]) == 7

    def test_export_html_download_and_preview(self):
        client = TestClient(app)
        resp = client.get("/api/export/test-session-deliverables?format=html")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "attachment" in resp.headers["content-disposition"]

        # Preview
        resp_prev = client.get("/api/export/test-session-deliverables?format=html&preview=true")
        assert resp_prev.status_code == 200
        assert "inline" in resp_prev.headers["content-disposition"]

    def test_export_zip_package(self):
        client = TestClient(app)
        resp = client.get("/api/export/test-session-deliverables?format=zip")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/zip"
        assert "attachment" in resp.headers["content-disposition"]

        # Validate ZIP contents
        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        names = zf.namelist()
        assert any(n.endswith(".pdf") for n in names)
        assert any(n.endswith(".xlsx") for n in names)
        assert any(n.endswith(".html") for n in names)
        assert any(n.endswith(".csv") for n in names)
        assert len(names) == 4

    def test_invalid_session_returns_404(self):
        client = TestClient(app)
        resp = client.get("/api/export/non-existent-session?format=pdf")
        assert resp.status_code == 404
