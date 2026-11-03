"""
PDF Report Builder — Phase 5

Produces a clean multi-page PDF using ReportLab.

Page layout:
  Page 1 — Cover: title, date range, summary metrics
  Page 2 — Category breakdown table
  Page 3 — Recurring payments table
  Page 4 — Financial insights
  Page 5+ — Full transaction list (paginated, 30 rows per page)
"""

from __future__ import annotations

import io
from datetime import date
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ---------------------------------------------------------------------------
# Colour palette (matches frontend category colours)
# ---------------------------------------------------------------------------
GREEN  = colors.HexColor("#16a34a")
RED    = colors.HexColor("#ef4444")
BLUE   = colors.HexColor("#3b82f6")
GRAY   = colors.HexColor("#6b7280")
LIGHT  = colors.HexColor("#f9fafb")
BORDER = colors.HexColor("#e5e7eb")
WHITE  = colors.white
BLACK  = colors.HexColor("#111827")

CATEGORY_COLORS: dict[str, Any] = {
    "Food":          colors.HexColor("#f97316"),
    "Travel":        colors.HexColor("#3b82f6"),
    "Shopping":      colors.HexColor("#8b5cf6"),
    "Bills":         colors.HexColor("#06b6d4"),
    "EMI":           colors.HexColor("#ef4444"),
    "Subscriptions": colors.HexColor("#ec4899"),
    "Salary":        colors.HexColor("#22c55e"),
    "Rent":          colors.HexColor("#f59e0b"),
    "Investments":   colors.HexColor("#10b981"),
    "Healthcare":    colors.HexColor("#14b8a6"),
    "Education":     colors.HexColor("#6366f1"),
    "Income":        colors.HexColor("#84cc16"),
    "Other":         colors.HexColor("#9ca3af"),
}

TAG_COLORS: dict[str, Any] = {
    "EMI":          colors.HexColor("#f97316"),
    "SUBSCRIPTION": colors.HexColor("#8b5cf6"),
    "RENT":         colors.HexColor("#3b82f6"),
    "SIP":          colors.HexColor("#22c55e"),
    "INSURANCE":    colors.HexColor("#f59e0b"),
}

W, H = A4
MARGIN = 1.8 * cm


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _inr(n: float) -> str:
    """Format a number as INR with commas."""
    return f"\u20b9{abs(n):,.0f}"


def _fmt_date(d: str) -> str:
    try:
        from datetime import datetime
        return datetime.strptime(d, "%Y-%m-%d").strftime("%d %b %Y")
    except Exception:
        return str(d)


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title", fontSize=26, leading=32, textColor=BLACK,
            fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=6,
        ),
        "subtitle": ParagraphStyle(
            "subtitle", fontSize=12, leading=16, textColor=GRAY,
            fontName="Helvetica", alignment=TA_CENTER, spaceAfter=4,
        ),
        "section": ParagraphStyle(
            "section", fontSize=14, leading=18, textColor=BLACK,
            fontName="Helvetica-Bold", spaceBefore=12, spaceAfter=8,
        ),
        "body": ParagraphStyle(
            "body", fontSize=10, leading=14, textColor=BLACK,
            fontName="Helvetica", spaceAfter=4,
        ),
        "small": ParagraphStyle(
            "small", fontSize=8, leading=11, textColor=GRAY,
            fontName="Helvetica",
        ),
        "insight": ParagraphStyle(
            "insight", fontSize=10, leading=14, textColor=BLACK,
            fontName="Helvetica", leftIndent=8, spaceAfter=6,
        ),
        "right": ParagraphStyle(
            "right", fontSize=10, leading=14, textColor=BLACK,
            fontName="Helvetica", alignment=TA_RIGHT,
        ),
        "table_header": ParagraphStyle(
            "table_header", fontSize=9, leading=12, textColor=WHITE,
            fontName="Helvetica-Bold", alignment=TA_CENTER,
        ),
        "table_cell": ParagraphStyle(
            "table_cell", fontSize=9, leading=12, textColor=BLACK,
            fontName="Helvetica",
        ),
        "table_cell_r": ParagraphStyle(
            "table_cell_r", fontSize=9, leading=12, textColor=BLACK,
            fontName="Helvetica", alignment=TA_RIGHT,
        ),
    }


def _hr() -> HRFlowable:
    return HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=8, spaceBefore=4)


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def _cover_section(result: dict, s: dict) -> list:
    """Page 1 — Title + summary metrics."""
    m = result["metrics"]
    start, end = result["metrics"]["date_range"]
    elements = []

    elements.append(Spacer(1, 1.5 * cm))
    elements.append(Paragraph("📊 AI Data Analysis Platform", s["title"]))
    elements.append(Paragraph("Data Analysis Report", s["subtitle"]))
    elements.append(Paragraph(
        f"{_fmt_date(start)} &nbsp;–&nbsp; {_fmt_date(end)}",
        s["subtitle"],
    ))
    elements.append(Spacer(1, 0.6 * cm))
    elements.append(_hr())
    elements.append(Spacer(1, 0.4 * cm))

    # Summary metrics table — 2×2 grid of cards
    ai_label = "AI-powered" if result.get("ai_enabled") else "Rule-based"
    savings_color = GREEN if m["savings"] >= 0 else RED

    card_data = [
        [
            _metric_cell("Total Income", _inr(m["total_income"]), GREEN, s),
            _metric_cell("Total Spend",  _inr(m["total_spend"]),  RED,   s),
        ],
        [
            _metric_cell("Net Savings",  _inr(m["savings"]),       savings_color, s),
            _metric_cell("Savings Rate", f"{m['savings_rate']:.1f}%", BLUE, s),
        ],
    ]
    card_table = Table(card_data, colWidths=[(W - 2 * MARGIN) / 2] * 2, rowHeights=2.6 * cm)
    card_table.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, -1), LIGHT),
        ("BOX",         (0, 0), (-1, -1), 0.5, BORDER),
        ("INNERGRID",   (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 16),
        ("RIGHTPADDING", (0, 0), (-1, -1), 16),
        ("TOPPADDING",   (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 12),
    ]))
    elements.append(card_table)
    elements.append(Spacer(1, 0.5 * cm))

    elements.append(Paragraph(
        f"Transactions: {m['transaction_count']}   ·   "
        f"Insights: {ai_label}   ·   "
        f"Generated by AI Data Analysis Platform",
        s["small"],
    ))
    return elements


def _metric_cell(label: str, value: str, color: Any, s: dict) -> list:
    return [
        Paragraph(f'<font color="{color.hexval()}" size="18"><b>{value}</b></font>', s["body"]),
        Paragraph(f'<font color="{GRAY.hexval()}" size="9">{label}</font>', s["small"]),
    ]


def _category_section(result: dict, s: dict) -> list:
    """Page 2 — Category breakdown."""
    elements: list = [PageBreak()]
    elements.append(Paragraph("Spending by Category", s["section"]))
    elements.append(_hr())

    cats = result["metrics"]["top_categories"]
    if not cats:
        elements.append(Paragraph("No spending data available.", s["body"]))
        return elements

    total_spend = result["metrics"]["total_spend"]

    col_w = (W - 2 * MARGIN) / 4
    header = [
        Paragraph("Category", s["table_header"]),
        Paragraph("Amount", s["table_header"]),
        Paragraph("% of Spend", s["table_header"]),
        Paragraph("Bar", s["table_header"]),
    ]
    rows = [header]
    for cat in cats:
        pct = (cat["amount"] / total_spend * 100) if total_spend else 0
        bar_filled = max(1, int(pct / 2))  # 1 char ≈ 2%
        bar = "█" * bar_filled
        cat_color = CATEGORY_COLORS.get(cat["category"], GRAY)
        rows.append([
            Paragraph(f'<font color="{cat_color.hexval()}">■</font> {cat["category"]}', s["table_cell"]),
            Paragraph(_inr(cat["amount"]), s["table_cell_r"]),
            Paragraph(f'{pct:.1f}%', s["table_cell_r"]),
            Paragraph(f'<font color="{cat_color.hexval()}">{bar}</font>', s["table_cell"]),
        ])

    tbl = Table(rows, colWidths=[col_w * 1.4, col_w * 0.8, col_w * 0.7, col_w * 1.1])
    tbl.setStyle(_table_style())
    elements.append(tbl)
    return elements


def _recurring_section(result: dict, s: dict) -> list:
    """Page 3 — Recurring payments."""
    elements: list = [PageBreak()]
    elements.append(Paragraph("Recurring Payments", s["section"]))
    elements.append(_hr())

    items = result["recurring_summary"]
    if not items:
        elements.append(Paragraph("No recurring payments detected.", s["body"]))
        return elements

    col_w = (W - 2 * MARGIN) / 4
    header = [
        Paragraph("Merchant",   s["table_header"]),
        Paragraph("Amount",     s["table_header"]),
        Paragraph("Tag",        s["table_header"]),
        Paragraph("Frequency",  s["table_header"]),
    ]
    rows = [header]
    for item in sorted(items, key=lambda x: x["amount"], reverse=True):
        tag_color = TAG_COLORS.get(item["tag"].upper(), GRAY)
        rows.append([
            Paragraph(item["merchant"], s["table_cell"]),
            Paragraph(_inr(item["amount"]), s["table_cell_r"]),
            Paragraph(
                f'<font color="{tag_color.hexval()}"><b>{item["tag"]}</b></font>',
                s["table_cell"],
            ),
            Paragraph(f'{item["frequency"].title()} × {item["occurrences"]}', s["table_cell"]),
        ])

    tbl = Table(rows, colWidths=[col_w * 1.4, col_w * 0.8, col_w * 0.9, col_w * 0.9])
    tbl.setStyle(_table_style())
    elements.append(tbl)
    return elements


def _insights_section(result: dict, s: dict) -> list:
    """Page 4 — Insights."""
    elements: list = [PageBreak()]
    elements.append(Paragraph("Financial Insights", s["section"]))
    source = result.get("insights_source", "rules")
    source_label = "AI-powered (Groq)" if source == "llm" else "Rule-based"
    elements.append(Paragraph(f"Source: {source_label}", s["small"]))
    elements.append(_hr())

    for i, insight in enumerate(result.get("insights", []), 1):
        elements.append(Paragraph(f"{i}.&nbsp;&nbsp;{insight}", s["insight"]))
        elements.append(Spacer(1, 0.15 * cm))

    return elements


def _transactions_section(result: dict, s: dict) -> list:
    """Page 5+ — Full transaction list, 30 rows per page."""
    elements: list = [PageBreak()]
    elements.append(Paragraph("Transaction History", s["section"]))
    elements.append(_hr())

    txns = result.get("transactions", [])
    if not txns:
        elements.append(Paragraph("No transactions available.", s["body"]))
        return elements

    usable_w = W - 2 * MARGIN
    col_widths = [usable_w * 0.14, usable_w * 0.35, usable_w * 0.18, usable_w * 0.15, usable_w * 0.18]

    header = [
        Paragraph("Date",        s["table_header"]),
        Paragraph("Description", s["table_header"]),
        Paragraph("Category",    s["table_header"]),
        Paragraph("Recurring",   s["table_header"]),
        Paragraph("Amount",      s["table_header"]),
    ]

    ROWS_PER_PAGE = 30
    chunks = [txns[i : i + ROWS_PER_PAGE] for i in range(0, len(txns), ROWS_PER_PAGE)]

    for page_num, chunk in enumerate(chunks):
        if page_num > 0:
            elements.append(PageBreak())
            elements.append(Paragraph(f"Transaction History (cont.)", s["section"]))
            elements.append(_hr())

        rows = [header]
        styles_per_row: list[tuple] = []

        for row_i, t in enumerate(chunk, 1):
            amount_color = GREEN if t["amount"] >= 0 else RED
            amt_str = (
                f'<font color="{amount_color.hexval()}"><b>'
                f'{"+" if t["amount"] >= 0 else "-"}{_inr(t["amount"])}'
                f"</b></font>"
            )
            desc = (t.get("clean_description") or t.get("description") or "")[:50]
            rec_label = t.get("recurrence_tag") or ("Yes" if t.get("is_recurring") else "—")
            rows.append([
                Paragraph(_fmt_date(t["date"]), s["table_cell"]),
                Paragraph(desc, s["table_cell"]),
                Paragraph(t.get("category", "Other"), s["table_cell"]),
                Paragraph(rec_label, s["table_cell"]),
                Paragraph(amt_str, s["table_cell_r"]),
            ])

        tbl = Table(rows, colWidths=col_widths, repeatRows=1)
        tbl.setStyle(_table_style(zebra=True))
        elements.append(tbl)

    return elements


def _table_style(zebra: bool = False) -> TableStyle:
    base = [
        ("BACKGROUND",   (0, 0), (-1, 0),  colors.HexColor("#1f2937")),
        ("TEXTCOLOR",    (0, 0), (-1, 0),  WHITE),
        ("FONTNAME",     (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0),  9),
        ("BOTTOMPADDING",(0, 0), (-1, 0),  8),
        ("TOPPADDING",   (0, 0), (-1, 0),  8),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, LIGHT] if zebra else [WHITE]),
        ("GRID",         (0, 0), (-1, -1), 0.4, BORDER),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING",   (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 1), (-1, -1), 5),
    ]
    return TableStyle(base)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def build_pdf_report(analysis_result: dict) -> bytes:
    """
    Build a multi-page PDF from an AnalysisResult dict.
    Returns raw PDF bytes.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
        title="AI Data Analysis Report",
        author="AI Data Analysis Platform",
    )

    s = _styles()
    story: list = []

    story.extend(_cover_section(analysis_result, s))
    story.extend(_category_section(analysis_result, s))
    story.extend(_recurring_section(analysis_result, s))
    story.extend(_insights_section(analysis_result, s))
    story.extend(_transactions_section(analysis_result, s))

    doc.build(story)
    return buf.getvalue()


def build_csv_report(analysis_result: dict) -> str:
    """
    Build a CSV string from the transaction list.
    Columns: Date, Description, Clean Description, Category, Amount, Recurring, Tag
    """
    import csv, io as _io

    buf = _io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "Date", "Description", "Clean Description",
        "Category", "Amount (INR)", "Recurring", "Tag",
    ])
    for t in analysis_result.get("transactions", []):
        writer.writerow([
            _fmt_date(t.get("date", "")),
            t.get("description", ""),
            t.get("clean_description", ""),
            t.get("category", ""),
            f"{t.get('amount', 0):.2f}",
            "Yes" if t.get("is_recurring") else "No",
            t.get("recurrence_tag") or "",
        ])
    return buf.getvalue()
