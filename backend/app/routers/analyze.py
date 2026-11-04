"""
Universal Data Analysis Router

POST /api/analyze         — Upload any dataset for universal analysis
GET  /api/analysis/{id}   — Get analysis results
POST /api/analyze/{id}/qa — Ask a question about the data
POST /api/analyze/{id}/clean — Preview or apply cleaning operations
GET  /api/analyze/{id}/download — Download cleaned data as CSV or Excel
"""

from __future__ import annotations

import io
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, File, HTTPException, UploadFile, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import settings
from app.services.ingestion import extract_dataframe, extract_dataframe_multi_sheet
from app.services.data_analyzer import analyze_data_quality, preview_cleaning, apply_cleaning
from app.services.business_analytics import run_business_analysis, detect_dataset_type
from app.services.ai_qa import answer_question
from app.session.store import session_store

import pandas as pd

router = APIRouter(tags=["analysis"])
log = logging.getLogger(__name__)

_ALLOWED_EXTENSIONS = {"pdf", "csv", "xlsx", "xls", "json"}


def _to_records(df: pd.DataFrame) -> list[dict]:
    """DataFrame → list of dicts with NaN replaced by None (JSON-safe)."""
    return df.astype(object).where(df.notna(), None).to_dict(orient="records")


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class QuestionRequest(BaseModel):
    question: str


class CleaningRequest(BaseModel):
    operations: list[dict]
    apply: bool = False  # If True, apply; if False, just preview


# ---------------------------------------------------------------------------
# POST /api/analyze — Universal file upload & analysis
# ---------------------------------------------------------------------------

@router.post("/analyze")
async def analyze_data(file: UploadFile = File(...)):
    """
    Upload any data file for universal analysis.
    Auto-detects dataset type and runs appropriate analytics.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    filename = file.filename.strip()
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if not ext or ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '.{ext}'. Please upload PDF, CSV, XLSX, or JSON.",
        )

    file_bytes = await file.read()

    if not file_bytes or len(file_bytes) < 10:
        raise HTTPException(status_code=400, detail="File is empty or too small.")

    if len(file_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({len(file_bytes) / (1024*1024):.1f} MB). Max {settings.MAX_UPLOAD_SIZE_MB} MB.",
        )

    session_id = session_store.create()

    try:
        # Extract DataFrame
        try:
            df = extract_dataframe(file_bytes, filename)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        df = df.dropna(how="all").dropna(axis=1, how="all")

        if df.empty:
            raise HTTPException(status_code=422, detail="No data could be extracted from the file.")

        # Detect dataset type
        dataset_type = detect_dataset_type(df)

        # If it looks like a financial dataset, attempt the bank statement pipeline first
        if dataset_type == "financial":
            from app.services.ingestion import extract_transactions
            from app.services.cleaner import clean_transactions
            from app.services.categorizer import categorize_transactions
            from app.services.recurring_detector import detect_recurring
            from app.services.metrics import compute_metrics, build_category_summary
            from app.services.insight_generator import generate_insights
            from app.models.result import AnalysisResult

            raw_rows = []
            try:
                raw_rows = extract_transactions(file_bytes, filename)
            except Exception as exc:
                log.info("Could not extract file as standard bank statement: %s; falling back to universal analysis.", exc)

            transactions = []
            parse_warnings = []
            if raw_rows:
                try:
                    transactions, parse_warnings = clean_transactions(raw_rows)
                except Exception as exc:
                    log.info("Could not clean rows as standard bank transactions: %s; falling back to universal analysis.", exc)

            if transactions:
                transactions, categorizer_used_llm = categorize_transactions(transactions)
                transactions, recurring_summary = detect_recurring(transactions)
                metrics = compute_metrics(transactions)
                category_summary = build_category_summary(transactions)

                if categorizer_used_llm and settings.ai_enabled:
                    import asyncio
                    await asyncio.sleep(5)

                try:
                    insights, insights_source = generate_insights(metrics, category_summary, recurring_summary)
                except Exception:
                    insights, insights_source = [], "fallback"

                result = AnalysisResult(
                    session_id=session_id,
                    transactions=transactions,
                    metrics=metrics,
                    insights=insights,
                    category_summary=category_summary,
                    recurring_summary=recurring_summary,
                    ai_enabled=settings.ai_enabled,
                    insights_source=insights_source,
                    parse_warnings=parse_warnings,
                    generated_at=datetime.now(timezone.utc),
                )

                # Store both the analysis result and the raw DataFrame for Q&A
                session_store.set(session_id, {
                    "analysis_type": "financial",
                    "financial_result": result.model_dump(mode="json"),
                    "dataset_type": "financial",
                    "data_quality": analyze_data_quality(df),
                    "raw_data": _to_records(df),
                    "columns": list(df.columns),
                    "row_count": len(df),
                    "filename": filename,
                    "uploaded_at": datetime.now(timezone.utc).isoformat(),
                })

                return {
                    "session_id": session_id,
                    "status": "complete",
                    "analysis_type": "financial",
                    "dataset_type": "financial",
                    "row_count": len(transactions),
                    "message": f"Financial analysis complete. {len(transactions)} transactions processed.",
                }

            # If no bank statement transactions could be formed, fall back to universal dataset analysis
            log.info("Financial format did not yield standard bank transactions; proceeding with universal business analytics.")
            dataset_type = "general"

        # Universal analysis for non-financial data
        data_quality = analyze_data_quality(df)
        business_analysis = run_business_analysis(df, dataset_type)

        # Store results
        session_store.set(session_id, {
            "analysis_type": "universal",
            "dataset_type": dataset_type,
            "data_quality": data_quality,
            "business_analysis": business_analysis,
            "raw_data": _to_records(df),
            "columns": list(df.columns),
            "row_count": len(df),
            "filename": filename,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        })

        return {
            "session_id": session_id,
            "status": "complete",
            "analysis_type": "universal",
            "dataset_type": dataset_type,
            "row_count": len(df),
            "quality_score": data_quality["quality_score"],
            "message": f"Analysis complete. {len(df)} rows processed as {dataset_type} dataset.",
        }

    except HTTPException:
        session_store.delete(session_id)
        raise
    except MemoryError:
        session_store.delete(session_id)
        raise HTTPException(status_code=413, detail="File is too large to process in memory.")
    except Exception as exc:
        session_store.delete(session_id)
        log.exception("Analysis failed")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc


# ---------------------------------------------------------------------------
# GET /api/analysis/{session_id} — Retrieve analysis results
# ---------------------------------------------------------------------------

@router.get("/analysis/{session_id}")
async def get_analysis(session_id: str):
    """Retrieve universal analysis results."""
    data = session_store.get(session_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Session not found or expired.")

    # For financial datasets, return the financial result format
    if data.get("analysis_type") == "financial":
        return {
            "analysis_type": "financial",
            "dataset_type": "financial",
            "financial_result": data.get("financial_result"),
            "data_quality": data.get("data_quality"),
        }

    return {
        "analysis_type": data.get("analysis_type", "universal"),
        "dataset_type": data.get("dataset_type", "general"),
        "data_quality": data.get("data_quality"),
        "business_analysis": data.get("business_analysis"),
        "columns": data.get("columns"),
        "row_count": data.get("row_count"),
        "filename": data.get("filename"),
        "generated_at": data.get("generated_at"),
        "preview_data": data.get("raw_data", [])[:50],  # First 50 rows
    }


# ---------------------------------------------------------------------------
# POST /api/analyze/{session_id}/qa — Ask a question about the data
# ---------------------------------------------------------------------------

@router.post("/analysis/{session_id}/qa")
async def ask_question_endpoint(session_id: str, request: QuestionRequest):
    """Ask a natural-language question about the uploaded data."""
    data = session_store.get(session_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Session not found or expired.")

    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    raw_data = data.get("raw_data", [])
    df = pd.DataFrame(raw_data)

    analysis = data.get("business_analysis") or data.get("financial_result") or {}

    try:
        result = answer_question(request.question, df, analysis)
        return result
    except Exception as exc:
        log.exception("Q&A failed")
        raise HTTPException(status_code=500, detail=f"Could not answer question: {exc}") from exc


# ---------------------------------------------------------------------------
# POST /api/analysis/{session_id}/clean — Preview or apply cleaning
# ---------------------------------------------------------------------------

@router.post("/analysis/{session_id}/clean")
async def clean_data_endpoint(session_id: str, request: CleaningRequest):
    """Preview or apply cleaning operations on the data."""
    data = session_store.get(session_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Session not found or expired.")

    raw_data = data.get("raw_data", [])
    df = pd.DataFrame(raw_data)

    if request.apply:
        def apply_update(current):
            current_df = pd.DataFrame(current.get("raw_data", []))
            cleaned = apply_cleaning(current_df, request.operations)
            quality = analyze_data_quality(cleaned)
            business = run_business_analysis(cleaned, current.get("dataset_type"))
            current.setdefault("original_data", current.get("raw_data", []))
            current["raw_data"] = _to_records(cleaned)
            current["data_quality"] = quality
            current["business_analysis"] = business
            current["row_count"] = len(cleaned)
            current["columns"] = list(cleaned.columns)
            return {
                "status": "applied",
                "original_rows": len(current_df),
                "cleaned_rows": len(cleaned),
                "quality_score": quality["quality_score"],
                "can_undo": True,
            }
        try:
            _, result = session_store.update(session_id, apply_update)
            return result
        except KeyError:
            raise HTTPException(status_code=404, detail="Session not found or expired.")
    else:
        # Preview only
        preview = preview_cleaning(df, request.operations)
        return {"status": "preview", **preview}


# ---------------------------------------------------------------------------
# POST /api/analysis/{session_id}/undo — Undo cleaning (rollback)
# ---------------------------------------------------------------------------

@router.post("/analysis/{session_id}/undo")
async def undo_cleaning(session_id: str):
    """Undo the last cleaning operation and restore original data."""
    def restore(current):
        original = current.get("original_data")
        if original is None:
            raise HTTPException(status_code=400, detail="No cleaning operations to undo.")
        df = pd.DataFrame(original)
        current["raw_data"] = original
        del current["original_data"]
        current["data_quality"] = analyze_data_quality(df)
        current["business_analysis"] = run_business_analysis(df, current.get("dataset_type"))
        current["row_count"] = len(df)
        current["columns"] = list(df.columns)
        return {"status": "restored", "row_count": len(df),
                "quality_score": current["data_quality"]["quality_score"]}
    try:
        _, result = session_store.update(session_id, restore)
        return result
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found or expired.")


# ---------------------------------------------------------------------------
# GET /api/analysis/{session_id}/download — Download cleaned data
# ---------------------------------------------------------------------------

@router.get("/analysis/{session_id}/download")
async def download_data(
    session_id: str,
    format: str = Query(default="csv", pattern="^(csv|xlsx)$"),
):
    """Download the (optionally cleaned) data as CSV or Excel."""
    data = session_store.get(session_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Session not found or expired.")

    raw_data = data.get("raw_data", [])
    df = pd.DataFrame(raw_data)

    if format == "csv":
        csv_buf = io.StringIO()
        df.to_csv(csv_buf, index=False)
        csv_bytes = csv_buf.getvalue().encode("utf-8-sig")

        return StreamingResponse(
            iter([csv_bytes]),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="data_analysis_export.csv"'},
        )

    # Excel format
    excel_buf = io.BytesIO()
    df.to_excel(excel_buf, index=False, engine="openpyxl")
    excel_buf.seek(0)

    return StreamingResponse(
        excel_buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="data_analysis_export.xlsx"'},
    )
