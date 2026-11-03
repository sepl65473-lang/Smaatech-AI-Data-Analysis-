"""
POST /api/upload

Accepts a bank statement file (PDF, CSV, XLSX), runs the full processing
pipeline, stores the AnalysisResult in the session store, and returns a session_id.

Pipeline order:
  ingestion → cleaner → categorizer → recurring_detector → metrics → insight_generator
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import settings
from app.models.result import AnalysisResult
from app.services.categorizer import categorize_transactions
from app.services.cleaner import clean_transactions
from app.services.ingestion import extract_transactions
from app.services.insight_generator import generate_insights
from app.services.metrics import build_category_summary, compute_metrics
from app.services.recurring_detector import detect_recurring
from app.session.store import session_store

router = APIRouter(tags=["upload"])
log = logging.getLogger(__name__)

_ALLOWED_EXTENSIONS = {"pdf", "csv", "xlsx", "xls", "json"}
_ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "text/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/octet-stream",  # some browsers send this for CSV
    "text/plain",                # some browsers send this for CSV
    "application/json",
}


@router.post("/upload")
async def upload_statement(file: UploadFile = File(...)):
    """
    Upload a bank statement file for analysis.
    Returns a session_id that can be used to retrieve results via GET /api/results/{session_id}.
    """
    # ---- Basic validation ----
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    filename = file.filename.strip()
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if not ext or ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=(
                f"Unsupported file type '{('.' + ext) if ext else '(none)'}'. "
                "Please upload a PDF, CSV, or XLSX file."
            ),
        )

    # ---- Read file bytes ----
    file_bytes = await file.read()

    if not file_bytes or len(file_bytes) < 10:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty or too small to be a valid bank statement.",
        )

    if len(file_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(
                f"File too large ({len(file_bytes) / (1024 * 1024):.1f} MB). "
                f"Maximum allowed size is {settings.MAX_UPLOAD_SIZE_MB} MB."
            ),
        )

    # ---- Create session early so we can associate errors with it ----
    session_id = session_store.create()

    try:
        # ------------------------------------------------------------------
        try:
            raw_rows = extract_transactions(file_bytes, file.filename)
        except (ValueError, Exception) as exc:
            log.warning("Extraction failed for %s: %s", file.filename, exc)
            raise HTTPException(
                status_code=422,
                detail=f"Could not parse file. The document may be corrupted or unreadable: {exc}",
            ) from exc

        if not raw_rows:
            raise HTTPException(
                status_code=422,
                detail="No transaction rows could be extracted from the file. "
                       "Please check that it is a valid bank statement.",
            )

        # ------------------------------------------------------------------
        # Stage 2 — Cleaning
        # ------------------------------------------------------------------
        transactions, parse_warnings = clean_transactions(raw_rows)

        if not transactions:
            raise HTTPException(
                status_code=422,
                detail=(
                    "No valid transactions could be parsed. "
                    "The file may be corrupted or in an unsupported format. "
                    + (f"Warnings: {'; '.join(parse_warnings)}" if parse_warnings else "")
                ),
            )

        # ------------------------------------------------------------------
        # Stage 3 — Categorisation (rule-based; LLM fallback in Phase 3)
        # ------------------------------------------------------------------
        transactions, categorizer_used_llm = categorize_transactions(transactions)

        # ------------------------------------------------------------------
        # Stage 4 — Recurring detection
        # ------------------------------------------------------------------
        transactions, recurring_summary = detect_recurring(transactions)

        # ------------------------------------------------------------------
        # Stage 5 — Metrics
        # ------------------------------------------------------------------
        metrics = compute_metrics(transactions)
        category_summary = build_category_summary(transactions)

        # ------------------------------------------------------------------
        # Stage 6 — Insights (always AI-generated via Groq)
        # ------------------------------------------------------------------
        # If the categorizer already used Groq this request, give the
        # rate-limit window a moment to clear before the insights call.
        if categorizer_used_llm and settings.ai_enabled:
            import asyncio as _asyncio
            await _asyncio.sleep(5)
        try:
            insights, insights_source = generate_insights(metrics, category_summary, recurring_summary)
        except Exception as exc:
            log.warning("Insight generation error (non-fatal): %s", exc)
            insights, insights_source = [], "fallback"

        # ------------------------------------------------------------------
        # Assemble result
        # ------------------------------------------------------------------
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

        session_store.set(session_id, result.model_dump(mode="json"))

    except HTTPException:
        # Clean up the session if pipeline failed
        session_store.delete(session_id)
        raise
    except MemoryError:
        session_store.delete(session_id)
        raise HTTPException(
            status_code=413,
            detail="File is too large to process in memory. Please try a smaller file.",
        )
    except Exception as exc:
        session_store.delete(session_id)
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred during analysis: {exc}",
        ) from exc

    return {
        "session_id": session_id,
        "status": "complete",
        "transaction_count": len(transactions),
        "parse_warnings": parse_warnings,
        "ai_enabled": settings.ai_enabled,
        "insights_source": insights_source,
        "message": (
            f"Analysis complete. {len(transactions)} transactions processed."
            + (f" ({len(parse_warnings)} rows skipped)" if parse_warnings else "")
        ),
    }
