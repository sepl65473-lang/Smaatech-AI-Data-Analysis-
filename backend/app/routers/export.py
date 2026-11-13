"""
Deliverables Export Router.

Provides verified, downloadable financial deliverables:
  1. PDF Report (multi-page with charts, tables, page numbers)
  2. Excel Workbook (.xlsx with 7 sheets, formulas, totals, charts)
  3. Standalone Interactive HTML Dashboard (.html, offline-capable)
  4. Complete Report Package (.zip containing PDF, Excel, and HTML)
  5. Clean Transactions (.csv)

Also provides in-app preview endpoints and deliverable status verification.
"""

from __future__ import annotations

import io
import logging
import zipfile
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, Response, StreamingResponse

from app.services.deliverables.dataset import build_report_dataset, DatasetVerificationError
from app.services.deliverables.pdf_report import build_pdf
from app.services.deliverables.excel_report import build_xlsx, build_preview
from app.services.deliverables.html_dashboard import build_html_dashboard
from app.services.report_builder import build_csv_report
from app.session.store import session_store

log = logging.getLogger(__name__)
router = APIRouter(tags=["export"])


def _get_dataset(session_id: str) -> dict:
    data = session_store.get(session_id)
    if data is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found or expired. Please upload your statement again.",
        )
    # If session is from generic data analysis track, use financial_result if present
    analysis_dict = data.get("financial_result") if data.get("analysis_type") == "financial" else data
    try:
        return build_report_dataset(analysis_dict)
    except DatasetVerificationError as exc:
        log.warning("Dataset verification issue: %s", exc)
        raise HTTPException(
            status_code=422,
            detail=f"Financial reconciliation failed: {exc}",
        ) from exc


@router.get("/export/{session_id}/status")
def get_export_status(session_id: str):
    """
    Check deliverable readiness and return metadata and canonical filenames.
    """
    ds = _get_dataset(session_id)
    meta = ds.get("meta", {})
    kpis = ds.get("kpis", {})
    period_key = meta.get("period_key", "statement")

    return {
        "status": "ready",
        "period_label": meta.get("period_label", "Financial Analysis"),
        "period_key": period_key,
        "filenames": {
            "pdf": f"Financial_Analysis_{period_key}.pdf",
            "xlsx": f"Financial_Analysis_{period_key}.xlsx",
            "html": f"Financial_Dashboard_{period_key}.html",
            "zip": f"Financial_Report_Package_{period_key}.zip",
            "csv": f"Financial_Transactions_{period_key}.csv",
        },
        "metrics": {
            "transaction_count": kpis.get("transaction_count", 0),
            "total_income": kpis.get("total_income", 0.0),
            "total_expense": kpis.get("total_expense", 0.0),
            "net": kpis.get("net", 0.0),
            "savings_rate": kpis.get("savings_rate", 0.0),
            "is_reconciled": True,
        },
    }


@router.get("/export/{session_id}")
def export_report(
    session_id: str,
    format: str = Query(default="pdf", pattern="^(pdf|xlsx|html|zip|csv)$"),
    preview: bool = Query(default=False),
):
    """
    Download or preview validated deliverables:
      - format=pdf   : PDF Report
      - format=xlsx  : Excel Workbook (7 sheets) / Workbook JSON preview when preview=True
      - format=html  : Standalone Interactive HTML Dashboard
      - format=zip   : Complete Report Package (PDF + Excel + HTML)
      - format=csv   : Flat transaction export
    """
    ds = _get_dataset(session_id)
    meta = ds.get("meta", {})
    period_key = meta.get("period_key", "statement")

    # ── 1. PDF Report ────────────────────────────────────────────────────────
    if format == "pdf":
        try:
            pdf_bytes = build_pdf(ds)
        except Exception as exc:
            log.exception("PDF generation failed")
            raise HTTPException(status_code=500, detail=f"PDF generation failed: {exc}") from exc

        filename = f"Financial_Analysis_{period_key}.pdf"
        disposition = "inline" if preview else f'attachment; filename="{filename}"'

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": disposition},
        )

    # ── 2. Excel Workbook ────────────────────────────────────────────────────
    if format == "xlsx":
        try:
            xlsx_bytes, build_info = build_xlsx(ds)
        except Exception as exc:
            log.exception("Excel generation failed")
            raise HTTPException(status_code=500, detail=f"Excel generation failed: {exc}") from exc

        if preview:
            # Return JSON grid representation for the frontend Excel viewer modal
            preview_data = build_preview(xlsx_bytes, build_info, max_rows=50)
            return JSONResponse(content={
                "period_label": meta.get("period_label"),
                "sheets": preview_data.get("sheets", []),
                "formula_count": preview_data.get("formula_count", 0),
            })

        filename = f"Financial_Analysis_{period_key}.xlsx"
        return StreamingResponse(
            io.BytesIO(xlsx_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    # ── 3. Standalone Interactive HTML Dashboard ──────────────────────────────
    if format == "html":
        try:
            html_str = build_html_dashboard(ds)
        except Exception as exc:
            log.exception("HTML Dashboard generation failed")
            raise HTTPException(status_code=500, detail=f"HTML Dashboard generation failed: {exc}") from exc

        filename = f"Financial_Dashboard_{period_key}.html"
        disposition = "inline" if preview else f'attachment; filename="{filename}"'

        return Response(
            content=html_str.encode("utf-8"),
            media_type="text/html",
            headers={"Content-Disposition": disposition},
        )

    # ── 4. Complete Report Package (ZIP) ──────────────────────────────────────
    if format == "zip":
        try:
            pdf_bytes = build_pdf(ds)
            xlsx_bytes, _ = build_xlsx(ds)
            html_str = build_html_dashboard(ds)

            data = session_store.get(session_id)
            analysis_dict = data.get("financial_result") if data and data.get("analysis_type") == "financial" else (data or {})
            csv_str = build_csv_report(analysis_dict)

            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as z:
                z.writestr(f"Financial_Analysis_{period_key}.pdf", pdf_bytes)
                z.writestr(f"Financial_Analysis_{period_key}.xlsx", xlsx_bytes)
                z.writestr(f"Financial_Dashboard_{period_key}.html", html_str.encode("utf-8"))
                z.writestr(f"Financial_Transactions_{period_key}.csv", csv_str.encode("utf-8-sig"))
            zip_buf.seek(0)
            zip_bytes = zip_buf.getvalue()
        except Exception as exc:
            log.exception("ZIP package generation failed")
            raise HTTPException(status_code=500, detail=f"ZIP package generation failed: {exc}") from exc

        filename = f"Financial_Report_Package_{period_key}.zip"
        return StreamingResponse(
            io.BytesIO(zip_bytes),
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    # ── 5. CSV Export ────────────────────────────────────────────────────────
    # format == "csv"
    data = session_store.get(session_id)
    analysis_dict = data.get("financial_result") if data.get("analysis_type") == "financial" else data
    csv_str = build_csv_report(analysis_dict)
    filename = f"Financial_Transactions_{period_key}.csv"

    return StreamingResponse(
        iter([csv_str.encode("utf-8-sig")]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
