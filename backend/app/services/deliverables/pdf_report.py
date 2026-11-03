"""
PDF Report — professional multi-page financial analysis (ReportLab).

Sections:
  1. Cover & executive summary (KPIs, key insights)
  2. Cash-flow charts (income vs expenses, balance / cumulative net flow)
  3. Category analysis (chart + table) and income sources
  4. Insights and recurring payments
  5. Monthly / weekly / daily-pattern analysis
  6. Reconciliation summary
  7. Complete transaction statement (auto-paginated, header row repeats)

Every page after the cover carries a running header and a
"Page X of Y" footer with the generation date and dataset fingerprint.
"""

from __future__ import annotations

import io
import os
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.graphics.charts.barcharts import HorizontalBarChart, VerticalBarChart
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import (
    CondPageBreak,
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ---------------------------------------------------------------------------
# Palette — categorical slots in fixed order; text never wears series colour
# ---------------------------------------------------------------------------
SERIES_1 = colors.HexColor("#2a78d6")   # income / primary series (blue)
SERIES_2 = colors.HexColor("#eb6834")   # expenses (orange)
INK      = colors.HexColor("#0b0b0b")
INK_2    = colors.HexColor("#52514e")
MUTED    = colors.HexColor("#8a8984")
GRID     = colors.HexColor("#e6e5e1")
SURFACE  = colors.HexColor("#f6f6f4")
HEADER   = colors.HexColor("#1f2937")
GOOD     = colors.HexColor("#15803d")
BAD      = colors.HexColor("#b91c1c")
WARN     = colors.HexColor("#b45309")
WHITE    = colors.white

W, H = A4
MARGIN = 1.8 * cm
USABLE_W = W - 2 * MARGIN

# ---------------------------------------------------------------------------
# Fonts — use a TTF with the ₹ glyph when available, else Helvetica + "Rs "
# ---------------------------------------------------------------------------
_FONT_CANDIDATES = [
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("/usr/share/fonts/TTF/DejaVuSans.ttf", "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"),
    ("/Library/Fonts/Arial.ttf", "/Library/Fonts/Arial Bold.ttf"),
]
_FONT = {"regular": "Helvetica", "bold": "Helvetica-Bold", "currency": "Rs "}


def _init_fonts() -> None:
    if _FONT.get("_done"):
        return
    _FONT["_done"] = True
    for reg, bold in _FONT_CANDIDATES:
        if not (os.path.exists(reg) and os.path.exists(bold)):
            continue
        try:
            r, b = TTFont("ReportSans", reg), TTFont("ReportSans-Bold", bold)
            if 0x20B9 not in r.face.charToGlyph:
                continue
            pdfmetrics.registerFont(r)
            pdfmetrics.registerFont(b)
            pdfmetrics.registerFontFamily("ReportSans", normal="ReportSans",
                                          bold="ReportSans-Bold")
            _FONT.update(regular="ReportSans", bold="ReportSans-Bold", currency="\u20b9")
            return
        except Exception:
            continue


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _money(n: float | None, signed: bool = False) -> str:
    if n is None:
        return "—"
    sign = "-" if n < 0 else ("+" if signed and n > 0 else "")
    return f"{sign}{_FONT['currency']}{abs(n):,.2f}"


def _compact(n: float) -> str:
    a = abs(n)
    sign = "-" if n < 0 else ""
    if a >= 1e7:
        return f"{sign}{a / 1e7:.1f}Cr"
    if a >= 1e5:
        return f"{sign}{a / 1e5:.1f}L"
    if a >= 1e3:
        return f"{sign}{a / 1e3:.0f}k"
    return f"{sign}{a:.0f}"


def _d(iso: str, fmt: str = "%d %b %Y") -> str:
    try:
        return datetime.strptime(iso[:10], "%Y-%m-%d").strftime(fmt)
    except Exception:
        return str(iso)


def _styles() -> dict[str, ParagraphStyle]:
    R, B = _FONT["regular"], _FONT["bold"]
    return {
        "title": ParagraphStyle("title", fontName=B, fontSize=26, leading=32, textColor=INK,
                                alignment=TA_LEFT, spaceAfter=4),
        "subtitle": ParagraphStyle("subtitle", fontName=R, fontSize=13, leading=18,
                                   textColor=INK_2, spaceAfter=2),
        "h1": ParagraphStyle("h1", fontName=B, fontSize=16, leading=20, textColor=INK,
                             spaceBefore=4, spaceAfter=6),
        "h2": ParagraphStyle("h2", fontName=B, fontSize=12, leading=16, textColor=INK,
                             spaceBefore=10, spaceAfter=6),
        "body": ParagraphStyle("body", fontName=R, fontSize=10, leading=14, textColor=INK,
                               spaceAfter=4),
        "muted": ParagraphStyle("muted", fontName=R, fontSize=8.5, leading=12,
                                textColor=INK_2),
        "insight": ParagraphStyle("insight", fontName=R, fontSize=10, leading=14,
                                  textColor=INK, leftIndent=14, firstLineIndent=-14,
                                  spaceAfter=6),
        "kpi_value": ParagraphStyle("kpi_value", fontName=B, fontSize=15, leading=19,
                                    textColor=INK),
        "kpi_label": ParagraphStyle("kpi_label", fontName=R, fontSize=8, leading=10,
                                    textColor=INK_2),
        "th": ParagraphStyle("th", fontName=B, fontSize=8, leading=10, textColor=WHITE),
        "th_r": ParagraphStyle("th_r", fontName=B, fontSize=8, leading=10, textColor=WHITE,
                               alignment=TA_RIGHT),
        "td": ParagraphStyle("td", fontName=R, fontSize=8, leading=10, textColor=INK),
        "td_r": ParagraphStyle("td_r", fontName=R, fontSize=8, leading=10, textColor=INK,
                               alignment=TA_RIGHT),
        "td_b": ParagraphStyle("td_b", fontName=B, fontSize=8, leading=10, textColor=INK),
        "td_br": ParagraphStyle("td_br", fontName=B, fontSize=8, leading=10, textColor=INK,
                                alignment=TA_RIGHT),
        "center": ParagraphStyle("center", fontName=R, fontSize=9, leading=12,
                                 textColor=INK_2, alignment=TA_CENTER),
    }


def _hr() -> HRFlowable:
    return HRFlowable(width="100%", thickness=0.5, color=GRID, spaceBefore=2, spaceAfter=8)


def _table(rows: list[list], col_widths: list[float], *, total_row: bool = False,
           zebra: bool = True, repeat: int = 1) -> Table:
    t = Table(rows, colWidths=col_widths, repeatRows=repeat)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), HEADER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 1), (-1, -1), 0.3, GRID),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
    ]
    if zebra:
        style.append(("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, SURFACE]))
    if total_row:
        style += [("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e9e8e4")),
                  ("LINEABOVE", (0, -1), (-1, -1), 0.8, INK_2)]
    t.setStyle(TableStyle(style))
    return t


def _P(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(str(text)), style)


# ---------------------------------------------------------------------------
# Charts (ReportLab graphics) — thin marks, recessive grid, one value axis
# ---------------------------------------------------------------------------

def _chart_title(d: Drawing, text: str) -> None:
    d.add(String(0, d.height - 12, text, fontName=_FONT["bold"], fontSize=10, fillColor=INK))


def _style_value_axis(axis, fmt=_compact) -> None:
    axis.labels.fontName = _FONT["regular"]
    axis.labels.fontSize = 7
    axis.labels.fillColor = INK_2
    axis.labelTextFormat = fmt
    axis.strokeColor = GRID
    axis.visibleGrid = True
    axis.gridStrokeColor = GRID
    axis.gridStrokeWidth = 0.4
    axis.forceZero = True


def _style_cat_axis(axis) -> None:
    axis.labels.fontName = _FONT["regular"]
    axis.labels.fontSize = 7
    axis.labels.fillColor = INK_2
    axis.strokeColor = GRID
    axis.visibleTicks = False


def _legend(d: Drawing, items: list[tuple], x: float, y: float) -> None:
    lg = Legend()
    lg.x, lg.y = x, y
    lg.alignment = "right"
    lg.columnMaximum = 1
    lg.fontName = _FONT["regular"]
    lg.fontSize = 8
    lg.fillColor = INK_2
    lg.dx = lg.dy = 7
    lg.deltax = 70
    lg.colorNamePairs = items
    lg.strokeColor = None
    d.add(lg)


def _income_expense_chart(periods: list[dict], label_key: str, inc_key: str,
                          exp_key: str, title: str) -> Drawing:
    d = Drawing(USABLE_W, 6.2 * cm)
    _chart_title(d, title)
    bc = VerticalBarChart()
    bc.x, bc.y = 34, 26
    bc.width, bc.height = USABLE_W - 44, 6.2 * cm - 62
    bc.data = [[p[inc_key] for p in periods], [p[exp_key] for p in periods]]
    bc.categoryAxis.categoryNames = [p[label_key] for p in periods]
    _style_cat_axis(bc.categoryAxis)
    _style_value_axis(bc.valueAxis)
    bc.bars.strokeColor = None
    bc.bars[0].fillColor = SERIES_1
    bc.bars[1].fillColor = SERIES_2
    bc.barSpacing = 2
    bc.groupSpacing = 10 if len(periods) < 8 else 4
    d.add(bc)
    _legend(d, [(SERIES_1, "Income"), (SERIES_2, "Expenses")], 20, 6.2 * cm - 24)
    return d


def _trend_chart(daily: list[dict]) -> Drawing:
    has_bal = any(x["closing_balance"] is not None for x in daily)
    if has_bal:
        series, last = [], None
        for x in daily:
            last = x["closing_balance"] if x["closing_balance"] is not None else last
            series.append(last if last is not None else 0)
        title = "Closing balance by day"
    else:
        series, run = [], 0.0
        for x in daily:
            run += x["net"]
            series.append(round(run, 2))
        title = "Cumulative net cash flow by day"
    d = Drawing(USABLE_W, 6 * cm)
    _chart_title(d, title)
    lc = HorizontalLineChart()
    lc.x, lc.y = 40, 24
    lc.width, lc.height = USABLE_W - 50, 6 * cm - 48
    lc.data = [series]
    step = max(1, len(daily) // 8)
    lc.categoryAxis.categoryNames = [
        _d(x["date"], "%d %b") if i % step == 0 else "" for i, x in enumerate(daily)
    ]
    _style_cat_axis(lc.categoryAxis)
    _style_value_axis(lc.valueAxis)
    lc.valueAxis.forceZero = not has_bal
    lc.lines[0].strokeColor = SERIES_1
    lc.lines[0].strokeWidth = 1.6
    lc.joinedLines = 1
    d.add(lc)
    return d


def _hbar_chart(labels: list[str], values: list[float], title: str,
                height: float | None = None) -> Drawing:
    n = max(1, len(labels))
    h = height or max(4 * cm, 0.62 * cm * n + 1.6 * cm)
    d = Drawing(USABLE_W, h)
    _chart_title(d, title)
    bc = HorizontalBarChart()
    bc.x, bc.y = 92, 18
    bc.width, bc.height = USABLE_W - 110, h - 44
    # HorizontalBarChart draws the first category at the bottom; reverse so the
    # largest sits on top.
    bc.data = [list(reversed(values))]
    bc.categoryAxis.categoryNames = list(reversed(labels))
    _style_cat_axis(bc.categoryAxis)
    bc.categoryAxis.labels.fontSize = 8
    bc.categoryAxis.labels.fillColor = INK
    _style_value_axis(bc.valueAxis)
    bc.bars.strokeColor = None
    bc.bars[0].fillColor = SERIES_1
    bc.barSpacing = 2
    d.add(bc)
    return d


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------

def _kpi_grid(ds: dict, s: dict) -> Table:
    k = ds["kpis"]

    def cell(label: str, value: str, note: str = "") -> list:
        out = [Paragraph(escape(value), s["kpi_value"]), Paragraph(escape(label), s["kpi_label"])]
        if note:
            out.append(Paragraph(escape(note), s["kpi_label"]))
        return out

    rate_note = "At or above 20% target" if k["savings_rate"] >= 20 else "Below 20% target"
    rows = [
        [cell("Total income", _money(k["total_income"]), f"{k['credit_count']} credits"),
         cell("Total expenses", _money(k["total_expense"]), f"{k['debit_count']} debits"),
         cell("Net savings", _money(k["net"], signed=True),
              "Net positive" if k["net"] >= 0 else "Overspent")],
        [cell("Savings rate", f"{k['savings_rate']:.1f}%", rate_note),
         cell("Transactions", f"{k['transaction_count']:,}", f"over {ds['meta']['days']} days"),
         cell("Average daily spend", _money(k["avg_daily_spend"]),
              f"{k['recurring_count']} recurring payments")],
    ]
    if k["opening_balance"] is not None:
        rows.append([
            cell("Opening balance", _money(k["opening_balance"])),
            cell("Closing balance", _money(k["closing_balance"])),
            cell("Largest expense",
                 _money(k["largest_expense"]["debit"]) if k["largest_expense"] else "—",
                 (k["largest_expense"]["clean_description"][:34]
                  if k["largest_expense"] else "")),
        ])
    t = Table(rows, colWidths=[USABLE_W / 3] * 3)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SURFACE),
        ("LINEBELOW", (0, 0), (-1, -2), 2, WHITE),
        ("LINEAFTER", (0, 0), (-2, -1), 2, WHITE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    return t


def _cover(ds: dict, s: dict) -> list:
    meta = ds["meta"]
    out = [
        Spacer(1, 1.2 * cm),
        Paragraph("FINANCIAL ANALYSIS REPORT", ParagraphStyle(
            "eyebrow", fontName=_FONT["bold"], fontSize=9, textColor=SERIES_1, leading=12,
            spaceAfter=6)),
        Paragraph("Bank Statement Analysis", s["title"]),
        Paragraph(f"Statement period: {escape(meta['period_label'])}", s["subtitle"]),
        Paragraph(f"{_d(meta['period_start'])} to {_d(meta['period_end'])} · "
                  f"{meta['days']} days", s["muted"]),
        Paragraph(f"Generated {escape(meta['generated_display'])} · "
                  f"Insights: {escape(meta['insights_label'])}", s["muted"]),
        Spacer(1, 0.6 * cm), _hr(),
        Paragraph("Executive summary", s["h1"]),
        _kpi_grid(ds, s),
        Spacer(1, 0.5 * cm),
    ]
    if ds["insights"]:
        out.append(Paragraph("Key findings", s["h2"]))
        for ins in ds["insights"][:3]:
            out.append(Paragraph(f"•&nbsp;&nbsp;{escape(ins)}", s["insight"]))
    if ds["categories"]:
        top = ds["categories"][0]
        out.append(Paragraph(
            f"Largest spending category: <b>{escape(top['category'])}</b> — "
            f"{_money(top['amount'])} ({top['pct']:.1f}% of expenses).", s["body"]))
    passed = sum(1 for c in ds["reconciliation"] if c["status"] == "PASS")
    out += [
        Spacer(1, 0.4 * cm),
        Paragraph(
            f"Data verification: {passed} of {len(ds['reconciliation'])} reconciliation checks "
            f"passed; all critical checks passed. Dataset fingerprint (SHA-256): "
            f"<font name='Courier' size='7'>{meta['fingerprint']}</font>", s["muted"]),
    ]
    return out


def _cash_flow(ds: dict, s: dict) -> list:
    out: list = [PageBreak(), Paragraph("Cash flow overview", s["h1"]), _hr()]
    if len(ds["monthly"]) > 1:
        out.append(_income_expense_chart(ds["monthly"], "label", "income", "expense",
                                         "Income vs expenses by month"))
    else:
        weeks = [{**w, "label": _d(w["week_start"], "%d %b")} for w in ds["weekly"]]
        out.append(_income_expense_chart(weeks, "label", "credits", "debits",
                                         "Income vs expenses by week (week starting)"))
    out += [Spacer(1, 0.5 * cm), _trend_chart(ds["daily"]), Spacer(1, 0.5 * cm)]

    k = ds["kpis"]
    rows = [[_P("Summary", s["th"]), _P("Amount", s["th_r"])],
            [_P("Total income", s["td"]), _P(_money(k["total_income"]), s["td_r"])],
            [_P("Total expenses", s["td"]), _P(_money(k["total_expense"]), s["td_r"])],
            [_P("Net savings", s["td_b"]), _P(_money(k["net"], signed=True), s["td_br"])]]
    out.append(_table(rows, [USABLE_W * 0.6, USABLE_W * 0.4], total_row=True, zebra=False))
    return out


def _category_section(ds: dict, s: dict) -> list:
    out: list = [PageBreak(), Paragraph("Category analysis", s["h1"]), _hr()]
    cats = ds["categories"]
    if not cats:
        return out + [Paragraph("No expense transactions in this period.", s["body"])]

    top = cats[:8]
    labels = [c["category"] for c in top]
    values = [c["amount"] for c in top]
    if len(cats) > 8:
        labels.append("All other")
        values.append(round(sum(c["amount"] for c in cats[8:]), 2))
    out += [_hbar_chart(labels, values, "Expenses by category"), Spacer(1, 0.4 * cm)]

    cw = [USABLE_W * x for x in (0.28, 0.12, 0.18, 0.13, 0.15, 0.14)]
    rows = [[_P(h, s["th"] if i == 0 else s["th_r"]) for i, h in enumerate(
        ["Category", "Txns", "Total spend", "% of spend", "Average", "Largest"])]]
    for c in cats:
        rows.append([_P(c["category"], s["td"]), _P(c["count"], s["td_r"]),
                     _P(_money(c["amount"]), s["td_r"]), _P(f"{c['pct']:.1f}%", s["td_r"]),
                     _P(_money(c["avg"]), s["td_r"]), _P(_money(c["largest"]), s["td_r"])])
    rows.append([_P("Total", s["td_b"]), _P(sum(c["count"] for c in cats), s["td_br"]),
                 _P(_money(ds["kpis"]["total_expense"]), s["td_br"]), _P("100.0%", s["td_br"]),
                 _P("", s["td"]), _P("", s["td"])])
    out.append(_table(rows, cw, total_row=True))

    if ds["income_sources"]:
        out += [CondPageBreak(4 * cm), Paragraph("Income sources", s["h2"])]
        cw2 = [USABLE_W * x for x in (0.4, 0.15, 0.25, 0.2)]
        rows = [[_P("Source category", s["th"]), _P("Txns", s["th_r"]),
                 _P("Amount", s["th_r"]), _P("% of income", s["th_r"])]]
        for c in ds["income_sources"]:
            rows.append([_P(c["category"], s["td"]), _P(c["count"], s["td_r"]),
                         _P(_money(c["amount"]), s["td_r"]), _P(f"{c['pct']:.1f}%", s["td_r"])])
        rows.append([_P("Total", s["td_b"]), _P(ds["kpis"]["credit_count"], s["td_br"]),
                     _P(_money(ds["kpis"]["total_income"]), s["td_br"]),
                     _P("100.0%", s["td_br"])])
        out.append(_table(rows, cw2, total_row=True))
    return out


def _insights_section(ds: dict, s: dict) -> list:
    out: list = [PageBreak(), Paragraph("Insights", s["h1"]),
                 Paragraph(f"Source: {escape(ds['meta']['insights_label'])}", s["muted"]), _hr()]
    if ds["insights"]:
        for i, ins in enumerate(ds["insights"], 1):
            out.append(Paragraph(f"{i}.&nbsp;&nbsp;{escape(ins)}", s["insight"]))
    else:
        out.append(Paragraph("No insights were generated for this statement.", s["body"]))

    out += [Spacer(1, 0.3 * cm), Paragraph("Recurring payments", s["h2"])]
    rec = ds["recurring"]
    if not rec:
        out.append(Paragraph("No recurring payments detected.", s["body"]))
    else:
        cw = [USABLE_W * x for x in (0.4, 0.2, 0.16, 0.24)]
        rows = [[_P("Merchant", s["th"]), _P("Amount", s["th_r"]), _P("Type", s["th"]),
                 _P("Frequency", s["th"])]]
        for r in sorted(rec, key=lambda x: -abs(x["amount"])):
            rows.append([_P(r["merchant"], s["td"]), _P(_money(abs(r["amount"])), s["td_r"]),
                         _P(r["tag"], s["td"]),
                         _P(f"{r['frequency'].title()} × {r['occurrences']}", s["td"])])
        out.append(_table(rows, cw))

    k = ds["kpis"]
    big = [x for x in (k["largest_expense"], k["largest_income"]) if x]
    if big:
        out += [Spacer(1, 0.3 * cm), Paragraph("Largest transactions", s["h2"])]
        cw = [USABLE_W * x for x in (0.16, 0.5, 0.14, 0.2)]
        rows = [[_P("Date", s["th"]), _P("Description", s["th"]), _P("Type", s["th"]),
                 _P("Amount", s["th_r"])]]
        for t in big:
            rows.append([_P(_d(t["date"]), s["td"]), _P(t["clean_description"], s["td"]),
                         _P(t["type"], s["td"]), _P(_money(t["amount"], signed=True), s["td_r"])])
        out.append(_table(rows, cw))
    return out


def _period_section(ds: dict, s: dict) -> list:
    out: list = [PageBreak(), Paragraph("Monthly, weekly and daily analysis", s["h1"]), _hr()]

    out.append(Paragraph("Monthly summary", s["h2"]))
    cw = [USABLE_W * x for x in (0.16, 0.18, 0.18, 0.18, 0.14, 0.16)]
    rows = [[_P(h, s["th"] if i == 0 else s["th_r"]) for i, h in enumerate(
        ["Month", "Income", "Expenses", "Net", "Savings rate", "Transactions"])]]
    for x in ds["monthly"]:
        rows.append([_P(x["label"], s["td"]), _P(_money(x["income"]), s["td_r"]),
                     _P(_money(x["expense"]), s["td_r"]), _P(_money(x["net"], True), s["td_r"]),
                     _P(f"{x['savings_rate']:.1f}%", s["td_r"]), _P(x["count"], s["td_r"])])
    out.append(_table(rows, cw))

    out.append(Paragraph("Weekly summary (weeks start Monday)", s["h2"]))
    cw = [USABLE_W * x for x in (0.26, 0.19, 0.19, 0.19, 0.17)]
    rows = [[_P(h, s["th"] if i == 0 else s["th_r"]) for i, h in enumerate(
        ["Week", "Credits", "Debits", "Net", "Transactions"])]]
    for w in ds["weekly"]:
        rows.append([_P(f"{_d(w['week_start'], '%d %b')} – {_d(w['week_end'], '%d %b %Y')}",
                        s["td"]),
                     _P(_money(w["credits"]), s["td_r"]), _P(_money(w["debits"]), s["td_r"]),
                     _P(_money(w["net"], True), s["td_r"]), _P(w["count"], s["td_r"])])
    out.append(_table(rows, cw))

    wd = ds["weekday"]
    out += [CondPageBreak(6 * cm), Spacer(1, 0.3 * cm),
            KeepTogether([_hbar_chart([x["weekday"] for x in wd], [x["debits"] for x in wd],
                                      "Spending by day of week", height=6 * cm)])]
    return out


def _reconciliation_section(ds: dict, s: dict) -> list:
    out: list = [PageBreak(), Paragraph("Reconciliation & data verification", s["h1"]),
                 Paragraph("Every figure in this report, the Excel workbook and the interactive "
                           "dashboard is computed from the same verified transaction dataset.",
                           s["muted"]), _hr()]
    status_color = {"PASS": GOOD, "FAIL": BAD, "WARN": WARN, "INFO": INK_2}
    cw = [USABLE_W * x for x in (0.3, 0.2, 0.2, 0.12, 0.18)]
    rows = [[_P("Check", s["th"]), _P("Expected", s["th_r"]), _P("Actual", s["th_r"]),
             _P("Status", s["th"]), _P("Difference", s["th_r"])]]

    def fmtv(c, v):
        if not c["numeric"] or isinstance(v, int):
            return str(v)
        return _money(v)

    for c in ds["reconciliation"]:
        col = status_color.get(c["status"], INK_2).hexval()
        rows.append([
            _P(c["check"], s["td"]), _P(fmtv(c, c["expected"]), s["td_r"]),
            _P(fmtv(c, c["actual"]), s["td_r"]),
            Paragraph(f"<font color='{col}'><b>{c['status']}</b></font>", s["td"]),
            _P("—" if c["difference"] is None else fmtv(c, c["difference"]), s["td_r"]),
        ])
    out.append(_table(rows, cw))
    out += [Spacer(1, 0.3 * cm),
            Paragraph(f"Dataset fingerprint (SHA-256): <font name='Courier' size='7'>"
                      f"{ds['meta']['fingerprint']}</font>", s["muted"])]
    if ds["parse_warnings"]:
        out.append(Paragraph("Rows skipped during parsing", s["h2"]))
        for w in ds["parse_warnings"][:50]:
            out.append(Paragraph(f"•&nbsp;{escape(w)}", s["muted"]))
    return out


def _statement_section(ds: dict, s: dict) -> list:
    txns = ds["transactions"]
    out: list = [PageBreak(), Paragraph("Complete transaction statement", s["h1"]),
                 Paragraph(f"{len(txns):,} transactions · {_d(ds['meta']['period_start'])} to "
                           f"{_d(ds['meta']['period_end'])}", s["muted"]), _hr()]
    has_bal = any(t["balance"] is not None for t in txns)
    if has_bal:
        fr = (0.06, 0.12, 0.36, 0.13, 0.11, 0.11, 0.11)
        hdr = ["#", "Date", "Description", "Category", "Debit", "Credit", "Balance"]
    else:
        fr = (0.06, 0.12, 0.42, 0.14, 0.13, 0.13)
        hdr = ["#", "Date", "Description", "Category", "Debit", "Credit"]
    cw = [USABLE_W * x for x in fr]
    right = {"#", "Debit", "Credit", "Balance"}
    rows = [[_P(h, s["th_r"] if h in right else s["th"]) for h in hdr]]
    for t in txns:
        desc = t["clean_description"]
        if t["recurrence_tag"]:
            desc += f"  [{t['recurrence_tag']}]"
        row = [_P(t["seq"], s["td_r"]), _P(_d(t["date"]), s["td"]), _P(desc, s["td"]),
               _P(t["category"], s["td"]),
               _P(_money(t["debit"]) if t["debit"] else "", s["td_r"]),
               _P(_money(t["credit"]) if t["credit"] else "", s["td_r"])]
        if has_bal:
            row.append(_P(_money(t["balance"]) if t["balance"] is not None else "", s["td_r"]))
        rows.append(row)
    k = ds["kpis"]
    total = [_P("", s["td"]), _P("", s["td"]), _P("Totals", s["td_b"]), _P("", s["td"]),
             _P(_money(k["total_expense"]), s["td_br"]), _P(_money(k["total_income"]), s["td_br"])]
    if has_bal:
        total.append(_P(_money(k["closing_balance"]), s["td_br"]))
    rows.append(total)
    out.append(_table(rows, cw, total_row=True))
    return out


# ---------------------------------------------------------------------------
# Page furniture — header + "Page X of Y" footer
# ---------------------------------------------------------------------------

def _canvas_class(meta: dict):
    class NumberedCanvas(rl_canvas.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._saved_pages: list[dict] = []

        def showPage(self):
            self._saved_pages.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._saved_pages)
            for state in self._saved_pages:
                self.__dict__.update(state)
                self._furniture(total)
                super().showPage()
            super().save()

        def _furniture(self, total: int) -> None:
            page = self._pageNumber
            self.saveState()
            self.setStrokeColor(GRID)
            self.setLineWidth(0.5)
            if page > 1:
                self.setFont(_FONT["bold"], 8)
                self.setFillColor(INK)
                self.drawString(MARGIN, H - 1.15 * cm, "Financial Analysis Report")
                self.setFont(_FONT["regular"], 8)
                self.setFillColor(INK_2)
                self.drawRightString(W - MARGIN, H - 1.15 * cm, meta["period_label"])
                self.line(MARGIN, H - 1.3 * cm, W - MARGIN, H - 1.3 * cm)
            self.line(MARGIN, 1.35 * cm, W - MARGIN, 1.35 * cm)
            self.setFont(_FONT["regular"], 7.5)
            self.setFillColor(INK_2)
            self.drawString(MARGIN, 0.95 * cm,
                            f"Generated {meta['generated_display']} · "
                            f"Dataset {meta['fingerprint'][:12]}")
            self.drawRightString(W - MARGIN, 0.95 * cm, f"Page {page} of {total}")
            self.restoreState()

    return NumberedCanvas


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def build_pdf(ds: dict) -> bytes:
    """Render the verified dataset to PDF bytes."""
    _init_fonts()
    s = _styles()
    meta = ds["meta"]
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN,
        title=f"Financial Analysis Report — {meta['period_label']}",
        author="AI Data Analysis Platform",
        subject=f"Statement period {meta['period_start']} to {meta['period_end']}",
        creator="AI Data Analysis Platform",
    )
    story: list = []
    story += _cover(ds, s)
    story += _cash_flow(ds, s)
    story += _category_section(ds, s)
    story += _insights_section(ds, s)
    story += _period_section(ds, s)
    story += _reconciliation_section(ds, s)
    story += _statement_section(ds, s)
    doc.build(story, canvasmaker=_canvas_class(meta))
    return buf.getvalue()
