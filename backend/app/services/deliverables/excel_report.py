"""
Excel workbook — fully editable seven-sheet financial analysis (openpyxl).

  1. Executive Summary          KPI formulas over the transaction sheet + chart
  2. Complete Transactions      every row, auto-filter, frozen header, SUBTOTAL totals
  3. Income and Expenses        SUMIFS/COUNTIFS by source and category + chart
  4. Category Analysis          per-category formulas, share, average + charts
  5. Daily and Weekly Analysis  SUMIFS by date and by week + charts
  6. Monthly Analysis           SUMIFS by month, savings rate + chart
  7. Reconciliation and Audit Log  engine figures vs live workbook recomputation

Aggregates are live formulas, so editing a transaction updates every sheet and
the reconciliation sheet flags any divergence from the analysed figures.
openpyxl cannot store calculated results, so each formula's value is recorded in
``cache`` for the in-app preview; Excel recalculates everything on open.
"""

from __future__ import annotations
import logging

import io
from datetime import date, datetime

from openpyxl import Workbook, load_workbook
from openpyxl.chart import BarChart, LineChart, PieChart, Reference
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

SHEETS = [
    "Executive Summary",
    "Complete Transactions",
    "Income and Expenses",
    "Category Analysis",
    "Daily and Weekly Analysis",
    "Monthly Analysis",
    "Reconciliation and Audit Log",
]
TX = "'Complete Transactions'"

CUR = '"₹"#,##0.00;[Red]-"₹"#,##0.00'
PCT = "0.0%"
DATE = "dd-mmm-yyyy"
INT = "#,##0"

SERIES_1 = "2A78D6"
SERIES_2 = "EB6834"
HDR_FILL = PatternFill("solid", fgColor="1F2937")
TOTAL_FILL = PatternFill("solid", fgColor="E9E8E4")
BAND_FILL = PatternFill("solid", fgColor="F6F6F4")
HDR_FONT = Font(bold=True, color="FFFFFF")
TITLE_FONT = Font(bold=True, size=16, color="0B0B0B")
H2_FONT = Font(bold=True, size=12, color="0B0B0B")
MUTED_FONT = Font(size=9, color="52514E")
BOLD = Font(bold=True)
THIN = Side(style="thin", color="D4D3CE")
TOTAL_BORDER = Border(top=Side(style="medium", color="52514E"))


def _d(iso: str) -> date:
    return datetime.strptime(iso[:10], "%Y-%m-%d").date()


class _Book:
    def __init__(self) -> None:
        self.wb = Workbook()
        self.cache: dict[tuple[str, str], object] = {}
        self.charts: dict[str, int] = {}

    def sheet(self, title: str) -> Worksheet:
        if len(self.wb.worksheets) == 1 and self.wb.active.title == "Sheet":
            ws = self.wb.active
            ws.title = title
        else:
            ws = self.wb.create_sheet(title)
        ws.sheet_view.showGridLines = False
        return ws

    def put(self, ws: Worksheet, row: int, col: int, value, *, fmt: str | None = None,
            font: Font | None = None, cached=None, fill: PatternFill | None = None,
            align: str | None = None):
        c = ws.cell(row=row, column=col, value=value)
        if isinstance(value, str) and value.startswith("="):
            self.cache[(ws.title, c.coordinate)] = cached
        if fmt:
            c.number_format = fmt
        if font:
            c.font = font
        if fill:
            c.fill = fill
        if align:
            c.alignment = Alignment(horizontal=align, vertical="center")
        return c

    def header(self, ws: Worksheet, row: int, col: int, labels: list[str]) -> None:
        for i, label in enumerate(labels):
            c = self.put(ws, row, col + i, label, font=HDR_FONT, fill=HDR_FILL)
            c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws.row_dimensions[row].height = 22

    def total_row(self, ws: Worksheet, row: int, c1: int, c2: int) -> None:
        for col in range(c1, c2 + 1):
            cell = ws.cell(row=row, column=col)
            cell.fill = TOTAL_FILL
            cell.border = TOTAL_BORDER
            cell.font = BOLD

    def title(self, ws: Worksheet, text: str, meta: dict, span: int = 6) -> None:
        self.put(ws, 1, 1, text, font=TITLE_FONT)
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=span)
        self.put(ws, 2, 1, f"Statement period: {meta['period_label']} "
                           f"({meta['period_start']} to {meta['period_end']}) · "
                           f"Generated {meta['generated_display']}", font=MUTED_FONT)
        ws.row_dimensions[1].height = 26

    def chart(self, ws: Worksheet, ch, anchor: str) -> None:
        ch.x_axis.delete = False
        if hasattr(ch, "y_axis"):
            ch.y_axis.delete = False
        ws.add_chart(ch, anchor)
        self.charts[ws.title] = self.charts.get(ws.title, 0) + 1


def _widths(ws: Worksheet, widths: dict[str, float]) -> None:
    for col, w in widths.items():
        ws.column_dimensions[col].width = w


def _color_series(ch, colors_: list[str], line: bool = False) -> None:
    for s, col in zip(ch.series, colors_):
        if line:
            s.graphicalProperties.line.solidFill = col
            s.graphicalProperties.line.width = 22000
            s.smooth = False
        else:
            s.graphicalProperties.solidFill = col
            s.graphicalProperties.line.noFill = True


# ---------------------------------------------------------------------------
# Sheet builders
# ---------------------------------------------------------------------------

def _transactions(b: _Book, ds: dict) -> dict[str, str]:
    ws = b.sheet(SHEETS[1])
    txns = ds["transactions"]
    n = len(txns)
    cols = ["#", "Date", "Description", "Merchant", "Category", "Type", "Debit", "Credit",
            "Amount", "Balance", "Recurring", "Recurrence Tag", "Week Start", "Month",
            "Transaction ID"]
    b.header(ws, 1, 1, cols)
    for i, t in enumerate(txns, start=2):
        b.put(ws, i, 1, t["seq"])
        b.put(ws, i, 2, _d(t["date"]), fmt=DATE)
        b.put(ws, i, 3, t["clean_description"])
        b.put(ws, i, 4, t["merchant"] or None)
        b.put(ws, i, 5, t["category"])
        b.put(ws, i, 6, t["type"])
        b.put(ws, i, 7, t["debit"], fmt=CUR)
        b.put(ws, i, 8, t["credit"], fmt=CUR)
        b.put(ws, i, 9, f"=H{i}-G{i}", fmt=CUR, cached=t["amount"])
        b.put(ws, i, 10, t["balance"], fmt=CUR)
        b.put(ws, i, 11, "Yes" if t["is_recurring"] else "No", align="center")
        b.put(ws, i, 12, t["recurrence_tag"] or None)
        b.put(ws, i, 13, _d(t["week_start"]), fmt=DATE)
        b.put(ws, i, 14, t["month"])
        b.put(ws, i, 15, t["id"], font=MUTED_FONT)
        if i % 2 == 1:
            for col in range(1, 16):
                ws.cell(row=i, column=col).fill = BAND_FILL

    last = n + 1
    ws.auto_filter.ref = f"A1:O{last}"
    ws.freeze_panes = "C2"
    tr = last + 2
    k = ds["kpis"]
    b.put(ws, tr, 3, "Totals (visible rows — respects filters)")
    b.put(ws, tr, 7, f"=SUBTOTAL(109,G2:G{last})", fmt=CUR, cached=k["total_expense"])
    b.put(ws, tr, 8, f"=SUBTOTAL(109,H2:H{last})", fmt=CUR, cached=k["total_income"])
    b.put(ws, tr, 9, f"=SUBTOTAL(109,I2:I{last})", fmt=CUR, cached=k["net"])
    b.put(ws, tr, 1, f"=SUBTOTAL(103,B2:B{last})", fmt=INT, cached=n)
    b.total_row(ws, tr, 1, 15)
    _widths(ws, {"A": 6, "B": 13, "C": 44, "D": 22, "E": 16, "F": 9, "G": 14, "H": 14,
                 "I": 14, "J": 15, "K": 10, "L": 15, "M": 13, "N": 10, "O": 38})
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_title_rows = "1:1"

    def r(col: str) -> str:
        return f"{TX}!${col}$2:${col}${last}"

    return {"date": r("B"), "cat": r("E"), "debit": r("G"), "credit": r("H"),
            "amount": r("I"), "rec": r("K"), "week": r("M"), "month": r("N")}


def _summary(b: _Book, ds: dict, R: dict, cat_rows: dict[str, int]) -> None:
    ws = b.wb[SHEETS[0]]
    meta, k = ds["meta"], ds["kpis"]
    b.title(ws, "Financial Analysis — Executive Summary", meta, span=4)
    b.put(ws, 3, 1, f"Insights: {meta['insights_label']} · Dataset fingerprint "
                    f"(SHA-256): {meta['fingerprint']}", font=MUTED_FONT)

    b.header(ws, 5, 1, ["Metric", "Value", "Notes"])
    rows = [
        ("Total income", f"=SUM({R['credit']})", CUR, k["total_income"], "Sum of all credits"),
        ("Total expenses", f"=SUM({R['debit']})", CUR, k["total_expense"], "Sum of all debits"),
        ("Net savings", "=B6-B7", CUR, k["net"], "Income minus expenses"),
        ("Savings rate", "=IF(B6>0,B8/B6,0)", PCT, k["savings_rate"] / 100,
         "Target: 20% or more"),
        ("Transactions", f"=COUNTA({R['date']})", INT, k["transaction_count"], ""),
        ("Credit transactions", f'=COUNTIF({R["credit"]},">0")', INT, k["credit_count"], ""),
        ("Debit transactions", f'=COUNTIF({R["debit"]},">0")', INT, k["debit_count"], ""),
        ("Days in period", meta["days"], INT, None,
         f"{meta['period_start']} to {meta['period_end']}"),
        ("Average daily spend", "=IF(B13>0,B7/B13,0)", CUR, k["avg_daily_spend"], ""),
        ("Largest expense", f"=MAX({R['debit']})", CUR,
         k["largest_expense"]["debit"] if k["largest_expense"] else 0,
         k["largest_expense"]["clean_description"] if k["largest_expense"] else ""),
        ("Largest credit", f"=MAX({R['credit']})", CUR,
         k["largest_income"]["credit"] if k["largest_income"] else 0,
         k["largest_income"]["clean_description"] if k["largest_income"] else ""),
    ]
    if k["opening_balance"] is not None:
        rows += [("Opening balance", k["opening_balance"], CUR, None, "Derived from statement"),
                 ("Closing balance", k["closing_balance"], CUR, None, "As printed on statement")]
    for i, (label, val, fmt, cached, note) in enumerate(rows, start=6):
        b.put(ws, i, 1, label, font=BOLD)
        b.put(ws, i, 2, val, fmt=fmt, cached=cached)
        b.put(ws, i, 3, note, font=MUTED_FONT)
    end = 5 + len(rows)

    r0 = end + 2
    b.put(ws, r0, 1, "Top spending categories", font=H2_FONT)
    b.header(ws, r0 + 1, 1, ["Category", "Total spend", "% of expenses"])
    for j, c in enumerate(ds["categories"][:5], start=r0 + 2):
        src = cat_rows[c["category"]]
        b.put(ws, j, 1, f"='{SHEETS[3]}'!A{src}", cached=c["category"])
        b.put(ws, j, 2, f"='{SHEETS[3]}'!C{src}", fmt=CUR, cached=c["amount"])
        b.put(ws, j, 3, f"='{SHEETS[3]}'!D{src}", fmt=PCT, cached=c["pct"] / 100)

    r1 = r0 + 2 + min(5, len(ds["categories"])) + 1
    if ds["insights"]:
        b.put(ws, r1, 1, "Key insights", font=H2_FONT)
        for j, text in enumerate(ds["insights"], start=r1 + 1):
            c = b.put(ws, j, 1, f"{j - r1}. {text}")
            ws.merge_cells(start_row=j, start_column=1, end_row=j, end_column=4)
            c.alignment = Alignment(wrap_text=True, vertical="top")
            ws.row_dimensions[j].height = 32

    ch = BarChart()
    ch.type = "col"
    ch.title = "Income vs expenses"
    ch.legend = None
    ch.add_data(Reference(ws, min_col=2, min_row=6, max_row=7))
    ch.set_categories(Reference(ws, min_col=1, min_row=6, max_row=7))
    ch.series[0].graphicalProperties.solidFill = SERIES_1
    ch.series[0].graphicalProperties.line.noFill = True
    ch.y_axis.numFmt = '"₹"#,##0'
    ch.width, ch.height = 14, 7.5
    b.chart(ws, ch, "E5")
    _widths(ws, {"A": 26, "B": 18, "C": 44, "D": 12})


def _category(b: _Book, ds: dict, R: dict) -> dict[str, int]:
    ws = b.sheet(SHEETS[3])
    b.title(ws, "Category Analysis (expenses)", ds["meta"], span=7)
    b.header(ws, 4, 1, ["Category", "Transactions", "Total spend", "% of spend",
                        "Average transaction", "Largest transaction", "Recurring txns"])
    cats = ds["categories"]
    first = 5
    total = first + len(cats)
    rows: dict[str, int] = {}
    for i, c in enumerate(cats, start=first):
        rows[c["category"]] = i
        b.put(ws, i, 1, c["category"])
        b.put(ws, i, 2, f'=COUNTIFS({R["cat"]},A{i},{R["debit"]},">0")', fmt=INT,
              cached=c["count"])
        b.put(ws, i, 3, f"=SUMIFS({R['debit']},{R['cat']},A{i})", fmt=CUR, cached=c["amount"])
        b.put(ws, i, 4, f"=IF($C${total}>0,C{i}/$C${total},0)", fmt=PCT, cached=c["pct"] / 100)
        b.put(ws, i, 5, f"=IF(B{i}>0,C{i}/B{i},0)", fmt=CUR, cached=c["avg"])
        b.put(ws, i, 6, c["largest"], fmt=CUR)
        b.put(ws, i, 7, f'=COUNTIFS({R["cat"]},A{i},{R["rec"]},"Yes",{R["debit"]},">0")',
              fmt=INT, cached=c["recurring"])
    k = ds["kpis"]
    b.put(ws, total, 1, "Total")
    if cats:
        b.put(ws, total, 2, f"=SUM(B{first}:B{total - 1})", fmt=INT,
              cached=sum(c["count"] for c in cats))
        b.put(ws, total, 3, f"=SUM(C{first}:C{total - 1})", fmt=CUR, cached=k["total_expense"])
        b.put(ws, total, 4, f"=SUM(D{first}:D{total - 1})", fmt=PCT, cached=1.0)
        b.put(ws, total, 7, f"=SUM(G{first}:G{total - 1})", fmt=INT,
              cached=sum(c["recurring"] for c in cats))
    else:
        b.put(ws, total, 3, 0, fmt=CUR)
    b.total_row(ws, total, 1, 7)
    ws.auto_filter.ref = f"A4:G{max(total - 1, 4)}"
    ws.freeze_panes = "A5"
    _widths(ws, {"A": 20, "B": 14, "C": 16, "D": 12, "E": 18, "F": 18, "G": 14})

    if cats:
        ch = BarChart()
        ch.type = "bar"
        ch.title = "Expenses by category"
        ch.legend = None
        ch.add_data(Reference(ws, min_col=3, min_row=4, max_row=total - 1), titles_from_data=True)
        ch.set_categories(Reference(ws, min_col=1, min_row=first, max_row=total - 1))
        ch.x_axis.scaling.orientation = "maxMin"   # largest category on top
        ch.y_axis.numFmt = '"₹"#,##0'
        _color_series(ch, [SERIES_1])
        ch.width, ch.height = 16, max(7.5, 0.8 * len(cats) + 3)
        b.chart(ws, ch, "I4")
        if len(cats) <= 6:
            pie = PieChart()
            pie.title = "Share of expenses"
            pie.add_data(Reference(ws, min_col=3, min_row=4, max_row=total - 1),
                         titles_from_data=True)
            pie.set_categories(Reference(ws, min_col=1, min_row=first, max_row=total - 1))
            pie.width, pie.height = 12, 7.5
            ws.add_chart(pie, f"I{6 + int(max(7.5, 0.8 * len(cats) + 3) * 2)}")
            b.charts[ws.title] += 1
    return rows


def _income_expenses(b: _Book, ds: dict, R: dict) -> None:
    ws = b.sheet(SHEETS[2])
    k = ds["kpis"]
    b.title(ws, "Income and Expenses", ds["meta"], span=5)
    b.header(ws, 4, 1, ["Measure", "Amount"])
    b.put(ws, 5, 1, "Total income", font=BOLD)
    b.put(ws, 5, 2, f"=SUM({R['credit']})", fmt=CUR, cached=k["total_income"])
    b.put(ws, 6, 1, "Total expenses", font=BOLD)
    b.put(ws, 6, 2, f"=SUM({R['debit']})", fmt=CUR, cached=k["total_expense"])
    b.put(ws, 7, 1, "Net savings", font=BOLD)
    b.put(ws, 7, 2, "=B5-B6", fmt=CUR, cached=k["net"])
    b.put(ws, 8, 1, "Savings rate", font=BOLD)
    b.put(ws, 8, 2, "=IF(B5>0,B7/B5,0)", fmt=PCT, cached=k["savings_rate"] / 100)

    def block(start: int, title: str, items: list[dict], amount_rng: str, total_ref: str,
              total_cached: float) -> int:
        b.put(ws, start, 1, title, font=H2_FONT)
        b.header(ws, start + 1, 1, ["Category", "Transactions", "Amount", "Share"])
        first = start + 2
        tot = first + len(items)
        for i, it in enumerate(items, start=first):
            b.put(ws, i, 1, it["category"])
            b.put(ws, i, 2, f'=COUNTIFS({R["cat"]},A{i},{amount_rng},">0")', fmt=INT,
                  cached=it["count"])
            b.put(ws, i, 3, f"=SUMIFS({amount_rng},{R['cat']},A{i})", fmt=CUR,
                  cached=it["amount"])
            b.put(ws, i, 4, f"=IF({total_ref}>0,C{i}/{total_ref},0)", fmt=PCT,
                  cached=it["pct"] / 100)
        b.put(ws, tot, 1, "Total")
        if items:
            b.put(ws, tot, 2, f"=SUM(B{first}:B{tot - 1})", fmt=INT,
                  cached=sum(x["count"] for x in items))
            b.put(ws, tot, 3, f"=SUM(C{first}:C{tot - 1})", fmt=CUR, cached=total_cached)
            b.put(ws, tot, 4, f"=SUM(D{first}:D{tot - 1})", fmt=PCT, cached=1.0)
        b.total_row(ws, tot, 1, 4)
        return tot + 2

    nxt = block(10, "Income sources", ds["income_sources"], R["credit"], "$B$5",
                k["total_income"])
    nxt = block(nxt, "Expenses by category", ds["categories"], R["debit"], "$B$6",
                k["total_expense"])

    def top(start: int, title: str, rows: list[dict], key: str) -> int:
        b.put(ws, start, 1, title, font=H2_FONT)
        b.header(ws, start + 1, 1, ["Date", "Description", "Category", "Amount"])
        for i, t in enumerate(rows, start=start + 2):
            b.put(ws, i, 1, _d(t["date"]), fmt=DATE)
            b.put(ws, i, 2, t["clean_description"])
            b.put(ws, i, 3, t["category"])
            b.put(ws, i, 4, t[key], fmt=CUR)
        return start + 2 + len(rows) + 1

    debits = sorted((t for t in ds["transactions"] if t["debit"]), key=lambda t: -t["debit"])
    credits = sorted((t for t in ds["transactions"] if t["credit"]), key=lambda t: -t["credit"])
    nxt = top(nxt, "Top 10 expenses", debits[:10], "debit")
    top(nxt, "Top 10 credits", credits[:10], "credit")

    ch = BarChart()
    ch.type = "col"
    ch.title = "Income vs expenses"
    ch.legend = None
    ch.add_data(Reference(ws, min_col=2, min_row=5, max_row=6))
    ch.set_categories(Reference(ws, min_col=1, min_row=5, max_row=6))
    _color_series(ch, [SERIES_1])
    ch.y_axis.numFmt = '"₹"#,##0'
    ch.width, ch.height = 14, 7.5
    b.chart(ws, ch, "G4")
    _widths(ws, {"A": 22, "B": 40, "C": 16, "D": 14})


def _daily_weekly(b: _Book, ds: dict, R: dict) -> None:
    ws = b.sheet(SHEETS[4])
    b.title(ws, "Daily and Weekly Analysis", ds["meta"], span=8)
    k = ds["kpis"]
    b.put(ws, 3, 1, "Daily", font=H2_FONT)
    b.header(ws, 4, 1, ["Date", "Weekday", "Credits", "Debits", "Net", "Transactions",
                        "Closing balance"])
    daily = ds["daily"]
    first = 5
    tot = first + len(daily)
    for i, x in enumerate(daily, start=first):
        b.put(ws, i, 1, _d(x["date"]), fmt=DATE)
        b.put(ws, i, 2, x["weekday"])
        b.put(ws, i, 3, f"=SUMIFS({R['credit']},{R['date']},A{i})", fmt=CUR, cached=x["credits"])
        b.put(ws, i, 4, f"=SUMIFS({R['debit']},{R['date']},A{i})", fmt=CUR, cached=x["debits"])
        b.put(ws, i, 5, f"=C{i}-D{i}", fmt=CUR, cached=x["net"])
        b.put(ws, i, 6, f"=COUNTIFS({R['date']},A{i})", fmt=INT, cached=x["count"])
        b.put(ws, i, 7, x["closing_balance"], fmt=CUR)
    b.put(ws, tot, 1, "Total")
    b.put(ws, tot, 3, f"=SUM(C{first}:C{tot - 1})", fmt=CUR, cached=k["total_income"])
    b.put(ws, tot, 4, f"=SUM(D{first}:D{tot - 1})", fmt=CUR, cached=k["total_expense"])
    b.put(ws, tot, 5, f"=SUM(E{first}:E{tot - 1})", fmt=CUR, cached=k["net"])
    b.put(ws, tot, 6, f"=SUM(F{first}:F{tot - 1})", fmt=INT, cached=k["transaction_count"])
    b.total_row(ws, tot, 1, 7)
    ws.auto_filter.ref = f"A4:G{tot - 1}"

    b.put(ws, 3, 9, "Weekly (weeks start Monday)", font=H2_FONT)
    b.header(ws, 4, 9, ["Week start", "Week end", "Credits", "Debits", "Net", "Transactions"])
    weekly = ds["weekly"]
    wtot = first + len(weekly)
    for i, w in enumerate(weekly, start=first):
        b.put(ws, i, 9, _d(w["week_start"]), fmt=DATE)
        b.put(ws, i, 10, _d(w["week_end"]), fmt=DATE)
        b.put(ws, i, 11, f"=SUMIFS({R['credit']},{R['week']},I{i})", fmt=CUR,
              cached=w["credits"])
        b.put(ws, i, 12, f"=SUMIFS({R['debit']},{R['week']},I{i})", fmt=CUR, cached=w["debits"])
        b.put(ws, i, 13, f"=K{i}-L{i}", fmt=CUR, cached=w["net"])
        b.put(ws, i, 14, f"=COUNTIFS({R['week']},I{i})", fmt=INT, cached=w["count"])
    b.put(ws, wtot, 9, "Total")
    b.put(ws, wtot, 11, f"=SUM(K{first}:K{wtot - 1})", fmt=CUR, cached=k["total_income"])
    b.put(ws, wtot, 12, f"=SUM(L{first}:L{wtot - 1})", fmt=CUR, cached=k["total_expense"])
    b.put(ws, wtot, 13, f"=SUM(M{first}:M{wtot - 1})", fmt=CUR, cached=k["net"])
    b.put(ws, wtot, 14, f"=SUM(N{first}:N{wtot - 1})", fmt=INT, cached=k["transaction_count"])
    b.total_row(ws, wtot, 9, 14)
    ws.freeze_panes = "A5"
    _widths(ws, {"A": 13, "B": 11, "C": 14, "D": 14, "E": 14, "F": 13, "G": 16, "H": 3,
                 "I": 13, "J": 13, "K": 14, "L": 14, "M": 14, "N": 13})

    ln = LineChart()
    ln.title = "Daily spending (debits)"
    ln.legend = None
    ln.add_data(Reference(ws, min_col=4, min_row=4, max_row=tot - 1), titles_from_data=True)
    ln.set_categories(Reference(ws, min_col=1, min_row=first, max_row=tot - 1))
    ln.x_axis.number_format = "dd-mmm"
    ln.y_axis.numFmt = '"₹"#,##0'
    _color_series(ln, [SERIES_1], line=True)
    ln.width, ln.height = 18, 8
    b.chart(ws, ln, "P4")

    bc = BarChart()
    bc.type = "col"
    bc.title = "Weekly credits vs debits"
    bc.add_data(Reference(ws, min_col=11, max_col=12, min_row=4, max_row=wtot - 1),
                titles_from_data=True)
    bc.set_categories(Reference(ws, min_col=9, min_row=first, max_row=wtot - 1))
    bc.x_axis.number_format = "dd-mmm"
    bc.y_axis.numFmt = '"₹"#,##0'
    bc.legend.position = "b"
    _color_series(bc, [SERIES_1, SERIES_2])
    bc.width, bc.height = 18, 8
    b.chart(ws, bc, "P22")


def _monthly(b: _Book, ds: dict, R: dict) -> None:
    ws = b.sheet(SHEETS[5])
    b.title(ws, "Monthly Analysis", ds["meta"], span=8)
    k = ds["kpis"]
    b.header(ws, 4, 1, ["Month", "Label", "Income", "Expenses", "Net", "Savings rate",
                        "Transactions", "Closing balance"])
    mo = ds["monthly"]
    first = 5
    tot = first + len(mo)
    for i, x in enumerate(mo, start=first):
        b.put(ws, i, 1, x["month"])
        b.put(ws, i, 2, x["label"])
        b.put(ws, i, 3, f"=SUMIFS({R['credit']},{R['month']},A{i})", fmt=CUR, cached=x["income"])
        b.put(ws, i, 4, f"=SUMIFS({R['debit']},{R['month']},A{i})", fmt=CUR, cached=x["expense"])
        b.put(ws, i, 5, f"=C{i}-D{i}", fmt=CUR, cached=x["net"])
        b.put(ws, i, 6, f"=IF(C{i}>0,E{i}/C{i},0)", fmt=PCT, cached=x["savings_rate"] / 100)
        b.put(ws, i, 7, f"=COUNTIFS({R['month']},A{i})", fmt=INT, cached=x["count"])
        b.put(ws, i, 8, x["closing_balance"], fmt=CUR)
    b.put(ws, tot, 1, "Total")
    b.put(ws, tot, 3, f"=SUM(C{first}:C{tot - 1})", fmt=CUR, cached=k["total_income"])
    b.put(ws, tot, 4, f"=SUM(D{first}:D{tot - 1})", fmt=CUR, cached=k["total_expense"])
    b.put(ws, tot, 5, f"=SUM(E{first}:E{tot - 1})", fmt=CUR, cached=k["net"])
    b.put(ws, tot, 6, f"=IF(C{tot}>0,E{tot}/C{tot},0)", fmt=PCT, cached=k["savings_rate"] / 100)
    b.put(ws, tot, 7, f"=SUM(G{first}:G{tot - 1})", fmt=INT, cached=k["transaction_count"])
    b.total_row(ws, tot, 1, 8)
    ws.freeze_panes = "A5"
    _widths(ws, {"A": 10, "B": 11, "C": 15, "D": 15, "E": 15, "F": 13, "G": 13, "H": 16})

    bc = BarChart()
    bc.type = "col"
    bc.title = "Income vs expenses by month"
    bc.add_data(Reference(ws, min_col=3, max_col=4, min_row=4, max_row=tot - 1),
                titles_from_data=True)
    bc.set_categories(Reference(ws, min_col=2, min_row=first, max_row=tot - 1))
    bc.y_axis.numFmt = '"₹"#,##0'
    bc.legend.position = "b"
    _color_series(bc, [SERIES_1, SERIES_2])
    bc.width, bc.height = 16, 8
    b.chart(ws, bc, "J4")


def _reconciliation(b: _Book, ds: dict, R: dict, refs: dict[str, str]) -> None:
    ws = b.sheet(SHEETS[6])
    b.title(ws, "Reconciliation and Audit Log", ds["meta"], span=7)
    b.put(ws, 3, 1, "Expected = figure from the analysis engine. Recomputed = live formula over "
                    "this workbook. Editing transactions will surface differences here.",
          font=MUTED_FONT)
    b.header(ws, 5, 1, ["#", "Check", "Expected (analysis)", "Recomputed (workbook)",
                        "Difference", "Status", "Detail"])
    live = {
        "Transaction count": (f"=COUNTA({R['date']})", INT),
        "Total income (credits)": (f"=SUM({R['credit']})", CUR),
        "Total expenses (debits)": (f"=SUM({R['debit']})", CUR),
        "Net savings": (f"=SUM({R['credit']})-SUM({R['debit']})", CUR),
        "Category totals = total expenses": (refs["cat_total"], CUR),
        "Daily totals = total expenses": (refs["daily_total"], CUR),
        "Monthly totals = total income": (refs["monthly_total"], CUR),
    }
    row = 6
    for n, c in enumerate(ds["reconciliation"], start=1):
        b.put(ws, row, 1, n)
        b.put(ws, row, 2, c["check"])
        if c["check"] in live:
            formula, fmt = live[c["check"]]
            b.put(ws, row, 3, c["expected"], fmt=fmt)
            b.put(ws, row, 4, formula, fmt=fmt, cached=c["actual"])
            b.put(ws, row, 5, f"=D{row}-C{row}", fmt=fmt, cached=c["difference"])
            b.put(ws, row, 6, f'=IF(ABS(E{row})<0.01,"PASS","FAIL")', cached=c["status"],
                  align="center")
        else:
            fmt = CUR if (c["numeric"] and isinstance(c["expected"], float)) else None
            b.put(ws, row, 3, c["expected"], fmt=fmt)
            b.put(ws, row, 4, c["actual"], fmt=fmt)
            b.put(ws, row, 5, c["difference"], fmt=fmt)
            b.put(ws, row, 6, c["status"], align="center")
        b.put(ws, row, 7, c["detail"], font=MUTED_FONT)
        row += 1
    status_rng = f"F6:F{row - 1}"
    for text, fill, color in (("PASS", "DCFCE7", "166534"), ("FAIL", "FEE2E2", "991B1B"),
                              ("WARN", "FEF3C7", "92400E"), ("INFO", "E5E7EB", "374151")):
        ws.conditional_formatting.add(status_rng, CellIsRule(
            operator="equal", formula=[f'"{text}"'],
            fill=PatternFill("solid", fgColor=fill), font=Font(bold=True, color=color)))

    row += 1
    b.put(ws, row, 1, f"Dataset fingerprint (SHA-256): {ds['meta']['fingerprint']}",
          font=MUTED_FONT)
    row += 2
    b.put(ws, row, 1, "Audit log", font=H2_FONT)
    row += 1
    b.header(ws, row, 1, ["#", "Timestamp", "Event", "Detail"])
    log_rows = list(ds["audit_log"]) + [{
        "timestamp": ds["meta"]["generated_display"], "event": "Workbook generated",
        "detail": f"{len(SHEETS)} sheets built from verified dataset "
                  f"{ds['meta']['fingerprint'][:16]}.",
    }]
    for n, e in enumerate(log_rows, start=1):
        row += 1
        b.put(ws, row, 1, n)
        b.put(ws, row, 2, e["timestamp"])
        b.put(ws, row, 3, e["event"])
        c = b.put(ws, row, 4, e["detail"], font=MUTED_FONT)
        c.alignment = Alignment(wrap_text=True, vertical="top")
    if ds["parse_warnings"]:
        row += 2
        b.put(ws, row, 1, "Rows skipped during parsing", font=H2_FONT)
        for w in ds["parse_warnings"]:
            row += 1
            b.put(ws, row, 2, w, font=MUTED_FONT)
    ws.freeze_panes = "A6"
    _widths(ws, {"A": 6, "B": 34, "C": 22, "D": 22, "E": 14, "F": 10, "G": 70})


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

def build_xlsx(ds: dict) -> tuple[bytes, dict]:
    """Render the verified dataset to an .xlsx; returns (bytes, build_info)."""
    b = _Book()
    b.sheet(SHEETS[0])                 # placeholder — filled once row refs are known
    R = _transactions(b, ds)
    _income_expenses(b, ds, R)
    cat_rows = _category(b, ds, R)
    _daily_weekly(b, ds, R)
    _monthly(b, ds, R)
    refs = {
        "cat_total": f"='{SHEETS[3]}'!C{5 + len(ds['categories'])}",
        "daily_total": f"='{SHEETS[4]}'!D{5 + len(ds['daily'])}",
        "monthly_total": f"='{SHEETS[5]}'!C{5 + len(ds['monthly'])}",
    }
    _reconciliation(b, ds, R, refs)
    _summary(b, ds, R, cat_rows)

    b.wb.calculation.fullCalcOnLoad = True
    b.wb.properties.title = f"Financial Analysis — {ds['meta']['period_label']}"
    b.wb.properties.creator = "AI Data Analysis Platform"
    b.wb.active = 0
    buf = io.BytesIO()
    b.wb.save(buf)
    # openpyxl writes formulas and fullCalcOnLoad=True so Excel/Google Sheets calculate them on open.
    # Optional offline formula pre-evaluation via 'formulas' package is enabled via ENABLE_FORMULAS_RECALC.
    recalc_enabled = os.getenv("ENABLE_FORMULAS_RECALC", "false").strip().lower() in ("true", "1")
    if recalc_enabled:
        try:
            from app.services.deliverables.recalculate_xlsx import recalculate_xlsx
            recalculated, engine_info = recalculate_xlsx(buf.getvalue())
            info = {"cache": b.cache, "charts": dict(b.charts),
                    "formula_count": len(b.cache), "calculation_engine": engine_info.get("engine", "formulas")}
            return recalculated, info
        except (ImportError, ModuleNotFoundError, Exception) as exc:
            logging.getLogger(__name__).warning("Formula recalculation engine unavailable (%s); exporting raw openpyxl workbook", exc)

    return buf.getvalue(), {"cache": b.cache, "charts": dict(b.charts),
                            "formula_count": len(b.cache), "calculation_engine": "openpyxl"}


def _display(value, fmt: str) -> str:
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.strftime("%d %b %Y")
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        if "%" in fmt:
            return f"{value * 100:.1f}%"
        if "₹" in fmt:
            return f"{'-' if value < 0 else ''}₹{abs(value):,.2f}"
        if isinstance(value, float) and not value.is_integer():
            return f"{value:,.2f}"
        return f"{int(value):,}"
    return str(value)


def build_preview(xlsx: bytes, info: dict, max_rows: int = 40) -> dict:
    """Re-open the saved workbook and render a value grid per sheet for the UI."""
    wb = load_workbook(io.BytesIO(xlsx))
    cache = info["cache"]
    sheets = []
    for ws in wb.worksheets:
        rows = []
        max_col = min(ws.max_column, 15)
        for r in range(1, min(ws.max_row, max_rows) + 1):
            row = []
            for col in range(1, max_col + 1):
                cell = ws.cell(row=r, column=col)
                v = cell.value
                formula = None
                if isinstance(v, str) and v.startswith("="):
                    formula = v
                    v = cache.get((ws.title, cell.coordinate))
                row.append({"v": _display(v, cell.number_format or ""), "f": formula,
                            "b": bool(cell.font and cell.font.b)})
            rows.append(row)
        sheets.append({
            "name": ws.title, "rows": rows, "total_rows": ws.max_row,
            "total_cols": ws.max_column, "truncated": ws.max_row > max_rows,
            "charts": info["charts"].get(ws.title, 0),
            "columns": [get_column_letter(i) for i in range(1, max_col + 1)],
        })
    return {"sheets": sheets, "formula_count": info["formula_count"]}
