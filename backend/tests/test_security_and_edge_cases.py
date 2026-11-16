import pytest
import io
import json
import os
from unittest.mock import patch
from starlette.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_empty_file_upload_rejected():
    files = {"file": ("empty.pdf", b"", "application/pdf")}
    res = client.post("/api/upload", files=files)
    assert res.status_code in (400, 422), f"Expected 400/422 for empty file, got {res.status_code}"


def test_unsupported_file_extension_rejected():
    files = {"file": ("malicious.exe", b"MZ\x90\x00\x03\x00\x00\x00", "application/x-msdownload")}
    res = client.post("/api/upload", files=files)
    assert res.status_code == 415, f"Expected 415 for .exe, got {res.status_code}"


def test_corrupt_file_upload_rejected():
    files = {"file": ("corrupt.pdf", b"%PDF-1.4 Not a real bank statement content random bytes", "application/pdf")}
    res = client.post("/api/upload", files=files)
    assert res.status_code in (400, 422), f"Expected 400/422 for corrupt PDF, got {res.status_code}"


def test_invalid_session_access():
    invalid_sid = "00000000-0000-0000-0000-000000000000"
    res = client.get(f"/api/results/{invalid_sid}")
    assert res.status_code == 404, f"Expected 404 for invalid session, got {res.status_code}"

    res_export = client.get(f"/api/export/{invalid_sid}?format=pdf")
    assert res_export.status_code == 404, f"Expected 404 for invalid export, got {res_export.status_code}"


@patch("app.services.insight_generator.generate_insights", return_value=(["Insight 1", "Insight 2", "Insight 3", "Insight 4", "Insight 5"], "rules"))
def test_deliverables_no_secret_leakage(mock_insights):
    # Upload original statement to create valid session
    pdf_candidates = [
        "tests/axis_june_2023_original.pdf",
        "backend/tests/axis_june_2023_original.pdf",
        "axis_june_2023_original.pdf",
    ]
    pdf_path = next((p for p in pdf_candidates if os.path.exists(p)), None)
    assert pdf_path is not None, "Original Axis Bank June 2023 PDF statement must exist"

    with open(pdf_path, "rb") as f:
        res = client.post("/api/upload", files={"file": ("axis_june_2023_original.pdf", f, "application/pdf")})
        assert res.status_code == 200, f"Upload failed: {res.text}"
        sid = res.json()["session_id"]

    for fmt in ["pdf", "xlsx", "html", "zip", "csv"]:
        res = client.get(f"/api/export/{sid}?format={fmt}")
        assert res.status_code == 200, f"Expected 200 for format={fmt}, got {res.status_code}"
        content = res.content
        # Check against common secret patterns
        assert b"gsk_" not in content, f"Secret GROQ key leaked in {fmt}"
        assert b"GROQ_API_KEY" not in content, f"Secret env name leaked in {fmt}"
        assert b"SECRET_KEY" not in content, f"SECRET_KEY leaked in {fmt}"
        assert b"password" not in content.lower() or fmt == "xlsx", "Potential password leak detected"
