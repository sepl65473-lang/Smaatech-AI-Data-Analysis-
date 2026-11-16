import io
import json
import os
import zipfile
from datetime import date
from types import SimpleNamespace

import openpyxl
from pypdf import PdfReader
from starlette.testclient import TestClient

from app.main import app
from app.models.transaction import Transaction
from app.services.categorizer import _llm_categorize_batch, categorize_transactions
from app.session.store import SessionStore, session_store


def test_unmatched_and_model_suggestion_metadata(monkeypatch):
    unmatched = Transaction(
        id="unmatched", date=date(2023, 6, 1), description="NEFT/REF/XYZ",
        clean_description="NEFT transfer", amount=-100, balance=900,
        payment_mode="NEFT",
    )
    monkeypatch.setattr("app.services.categorizer._llm_categorize", lambda rows: False)
    categorized, _ = categorize_transactions([unmatched])
    assert categorized[0].category == "Other"
    assert categorized[0].classification_source == "rules_unclassified"
    assert categorized[0].confidence_score == 0.40
    assert "Review Queue" in categorized[0].classification_reason
    assert categorized[0].payment_mode == "NEFT"

    txn = Transaction(
        id="llm", date=date(2023, 6, 2), description="NEFT mystery",
        clean_description="mystery", amount=-20, balance=880,
    )
    response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='[{"id":"llm","category":"Food"}]'))])
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kwargs: response)))
    _llm_categorize_batch(client, [txn], "test-model")
    assert txn.category == "Food"
    assert txn.classification_source == "llm_inferred"
    assert txn.confidence == "Review"
    assert txn.confidence_score == 0.65
    assert "requires user review" in txn.classification_reason


def test_user_remap_propagates_to_all_exports_and_persists():
    source = os.path.join(os.path.dirname(__file__), "axis_june_2023_original.pdf")
    client = TestClient(app)
    with open(source, "rb") as statement:
        upload = client.post("/api/upload", files={"file": ("axis_june_2023_original.pdf", statement, "application/pdf")})
    assert upload.status_code == 200, upload.text
    sid = upload.json()["session_id"]
    try:
        before = client.get(f"/api/results/{sid}").json()
        target = next(t for t in before["transactions"] if t["classification_source"] == "rules_unclassified")
        amount_before = before["metrics"]["total_spend"]
        remap = client.post(f"/api/results/{sid}/category-mapping", json={
            "transaction_id": target["id"], "new_category": "Healthcare",
        })
        assert remap.status_code == 200, remap.text
        assert remap.json()["modified_count"] == 1
        after = client.get(f"/api/results/{sid}").json()
        mapped = next(t for t in after["transactions"] if t["id"] == target["id"])
        assert mapped["category"] == "Healthcare"
        assert mapped["classification_source"] == "user"
        assert mapped["confidence_score"] == 1.0
        assert mapped["classification_reason"].startswith("User confirmed")
        assert after["metrics"]["total_spend"] == amount_before
        assert after["metrics"]["reconciliation_delta"] == 0
        assert after["category_summary"]
        assert round(sum(after["category_summary"].values()), 2) == 4626410.0
        assert after["audit_trail"][-1]["modified_count"] == 1

        persisted = SessionStore(data_dir=session_store._data_dir).get(sid)
        assert persisted["audit_trail"][-1]["transaction_ids"] == [target["id"]]

        csv_response = client.get(f"/api/export/{sid}?format=csv")
        assert csv_response.status_code == 200 and "Healthcare" in csv_response.text
        pdf_response = client.get(f"/api/export/{sid}?format=pdf")
        pdf_text = "".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf_response.content)).pages)
        assert "Healthcare" in pdf_text
        xlsx_response = client.get(f"/api/export/{sid}?format=xlsx")
        wb = openpyxl.load_workbook(io.BytesIO(xlsx_response.content), data_only=False)
        assert len(wb.sheetnames) == 7
        formula_cells = [(sheet.title, cell.coordinate, cell.value)
                         for sheet in wb for row in sheet.iter_rows() for cell in row
                         if isinstance(cell.value, str) and cell.value.startswith("=")]
        # A new confirmed category adds formula rows to Category Analysis;
        # preserve and recalculate the dynamic formula count after remapping.
        assert len(formula_cells) >= 443
        cached = openpyxl.load_workbook(io.BytesIO(xlsx_response.content), data_only=True)
        assert all(cached[sheet][cell].value is not None for sheet, cell, _ in formula_cells)
        assert wb["Complete Transactions"]["G165"].value == "=SUBTOTAL(109,G2:G163)"
        assert cached["Complete Transactions"]["G165"].value == 4626410.0
        assert cached["Complete Transactions"]["H165"].value == 4548780.0
        assert cached["Complete Transactions"]["I165"].value == -77630.0
        assert cached["Complete Transactions"]["A165"].value == 162
        assert "Healthcare" in [cell.value for row in wb["Complete Transactions"].iter_rows() for cell in row]
        assert "Healthcare" in [cell.value for row in wb["Category Analysis"].iter_rows() for cell in row]
        html_response = client.get(f"/api/export/{sid}?format=html")
        assert html_response.status_code == 200 and "Healthcare" in html_response.text
        zip_response = client.get(f"/api/export/{sid}?format=zip")
        with zipfile.ZipFile(io.BytesIO(zip_response.content)) as archive:
            assert archive.testzip() is None
            assert len(archive.namelist()) == 4
            assert all("Healthcare" in archive.read(name).decode("utf-8", errors="ignore")
                       for name in archive.namelist() if name.endswith((".csv", ".html")))
    finally:
        session_store.delete(sid)
