"""
Ingestion service — Phase 2

Detects file type from extension + MIME, then extracts raw transaction rows
from PDF (pdfplumber), CSV (pandas), or XLSX (openpyxl/pandas).

Output: List[dict] with keys: date_str, description, amount_str, balance_str
"""

from __future__ import annotations

import csv
import io
import re
import os
import tempfile
from typing import Optional

import pandas as pd
import pdfplumber


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def extract_transactions(file_bytes: bytes, filename: str) -> list[dict]:
    """
    Extract raw transaction rows from an uploaded bank statement file.

    Returns a list of dicts with keys:
        date_str      — raw date string from the file
        description   — transaction narration / description
        amount_str    — raw amount string (may contain ₹, commas, Dr/Cr)
        balance_str   — raw balance string (may be empty)
    """
    ext = _get_extension(filename)

    if ext == "pdf":
        return _extract_pdf(file_bytes)
    elif ext == "csv":
        return _extract_csv(file_bytes)
    elif ext in ("xlsx", "xls"):
        return _extract_xlsx(file_bytes)
    elif ext == "json":
        return _extract_json(file_bytes)
    else:
        raise ValueError(f"Unsupported file type: '{ext}'. Please upload a PDF, CSV, XLSX, or JSON file.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_extension(filename: str) -> str:
    _, ext = os.path.splitext(filename.lower())
    return ext.lstrip(".")


# ---------------------------------------------------------------------------
# CSV extraction
# ---------------------------------------------------------------------------

# Maps of common bank CSV column name variants → canonical key
_DATE_COLS = [
    "date", "txn date", "transaction date", "tran date", "trans date",
    "posting date", "value date", "val date", "post date", "booking date",
    "payment date", "date time", "datetime", "timestamp", "time", "dt",
]
_DESC_COLS = [
    "description", "narration", "particulars", "particular", "remarks",
    "txn remarks", "transaction remarks", "details", "transaction details",
    "chq/ref number", "ref no", "narration/chq no", "narrative", "memo",
    "comment", "payee", "beneficiary", "party", "party name", "account",
    "title", "notes", "transaction description",
]
_DEBIT_COLS = [
    "debit", "debit amount", "withdrawal", "withdrawal amount", "withdrawals",
    "withdrawal amt", "dr", "dr amount", "amount(dr)", "debit(inr)", "debit (inr)",
    "debit rs", "debit(rs)", "dr amt", "money out", "paid out", "expense", "payment",
]
_CREDIT_COLS = [
    "credit", "credit amount", "deposit", "deposit amount", "deposits",
    "deposit amt", "cr", "cr amount", "amount(cr)", "credit(inr)", "credit (inr)",
    "credit rs", "credit(rs)", "cr amt", "money in", "received", "income", "receipt",
]
_AMOUNT_COLS = [
    "amount", "transaction amount", "txn amount", "tran amount", "trans amount",
    "net amount", "total amount", "total", "amt", "inr", "value", "sum",
]
_BALANCE_COLS = [
    "balance", "closing balance", "available balance", "running balance",
    "closing bal", "available bal", "net balance", "bal",
]
# Single column saying whether the amount is a debit or a credit (e.g. Axis Bank)
_DRCR_COLS = [
    "dr/cr", "cr/dr", "debit/credit", "credit/debit",
    "type", "txn type", "transaction type",
]


def _normalise_col(col: str) -> str:
    """Lowercase + strip all non-alphanumeric for fuzzy matching."""
    return re.sub(r"[^a-z0-9]", "", str(col).lower().strip())


def _find_col(df_cols: list[str], candidates: list[str]) -> Optional[str]:
    """
    Return the df column matching a candidate: exact normalised match first,
    then a column that contains a (5+ char) candidate, e.g. "Amount(INR)" or
    "Transaction Particulars".
    """
    norm_map = {_normalise_col(c): c for c in df_cols}
    for cand in candidates:
        key = _normalise_col(cand)
        if key in norm_map:
            return norm_map[key]
    for cand in candidates:
        key = _normalise_col(cand)
        if len(key) < 5:
            continue
        for norm, col in norm_map.items():
            if key in norm:
                return col
    return None


def _map_columns(cols: list[str]) -> dict[str, Optional[str]]:
    """Locate the transaction columns in a header row."""
    drcr = _find_col(cols, _DRCR_COLS)
    rest = [c for c in cols if c != drcr]
    return {
        "date": _find_col(rest, _DATE_COLS),
        "desc": _find_col(rest, _DESC_COLS),
        "debit": _find_col(rest, _DEBIT_COLS),
        "credit": _find_col(rest, _CREDIT_COLS),
        "amount": _find_col(rest, _AMOUNT_COLS),
        "balance": _find_col(rest, _BALANCE_COLS),
        "drcr": drcr,
    }


def _signed_amount(amount: str, indicator: str) -> str:
    """Apply a DR/CR indicator to an unsigned amount (debit → negative)."""
    ind = indicator.strip().lower()
    is_debit = ind == "d" or ind.startswith(("dr", "debit", "withdraw"))
    if is_debit and not amount.startswith("-"):
        return f"-{amount}"
    return amount


def _decode_csv_bytes(file_bytes: bytes) -> str:
    """Decode CSV bytes, honouring a UTF-16 BOM and falling back to latin-1."""
    if file_bytes.startswith((b"\xff\xfe", b"\xfe\xff")):
        return file_bytes.decode("utf-16")
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return file_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    return file_bytes.decode("latin-1")  # never fails


def _read_csv_robust(file_bytes: bytes) -> pd.DataFrame:
    """
    Read a CSV into a string DataFrame.

    Handles exports that have a metadata preamble (title, key/value lines)
    before the real table: if a plain parse fails, the header is taken to be
    the first line whose field count matches the most common field count,
    and malformed rows are skipped.
    """
    text = _decode_csv_bytes(file_bytes)

    try:
        df = pd.read_csv(io.StringIO(text), dtype=str, skip_blank_lines=True)
        if not _looks_like_preamble(df):
            return df
    except pd.errors.EmptyDataError as exc:
        raise ValueError("The CSV file is empty.") from exc
    except pd.errors.ParserError:
        pass

    return _table_from_rows(list(csv.reader(io.StringIO(text))))


def _read_excel_robust(file_bytes: bytes) -> pd.DataFrame:
    """Read an Excel file, intelligently selecting the best sheet and skipping title rows."""
    try:
        sheets = pd.read_excel(io.BytesIO(file_bytes), dtype=str, sheet_name=None)
        if not sheets:
            raise ValueError("Excel file contains no sheets.")
        
        # Pick the sheet with the most non-empty rows
        best_sheet_name = None
        best_df = None
        max_rows = -1
        for sname, sdf in sheets.items():
            clean_s = sdf.dropna(how="all").dropna(axis=1, how="all")
            if len(clean_s) > max_rows:
                max_rows = len(clean_s)
                best_sheet_name = sname
                best_df = sdf
                
        df = best_df if best_df is not None else next(iter(sheets.values()))
        if not _looks_like_preamble(df):
            return df
        
        raw = pd.read_excel(io.BytesIO(file_bytes), dtype=str, header=None, sheet_name=best_sheet_name)
        return _table_from_rows(raw.where(raw.notna(), "").values.tolist())
    except Exception as exc:
        try:
            df = pd.read_excel(io.BytesIO(file_bytes), dtype=str)
            if not _looks_like_preamble(df):
                return df
            raw = pd.read_excel(io.BytesIO(file_bytes), dtype=str, header=None)
            return _table_from_rows(raw.where(raw.notna(), "").values.tolist())
        except Exception:
            raise ValueError(f"Could not parse XLSX: {exc}") from exc


def _looks_like_preamble(df: pd.DataFrame) -> bool:
    """True if pandas used a title line as the header (mostly 'Unnamed: n' columns)."""
    cols = [str(c) for c in df.columns]
    unnamed = sum(c.startswith("Unnamed:") for c in cols)
    return len(cols) == 1 or unnamed > len(cols) / 2


def _table_from_rows(rows: list[list]) -> pd.DataFrame:
    """
    Build a DataFrame from raw rows that may start with a metadata preamble.

    The header is the first row with at least 3/4 as many filled cells as
    the widest row. Data rows wider than the header (e.g. an unquoted comma
    in a timestamp) get extra generic column names.
    """
    rows = [[str(c).strip() for c in r] for r in rows]
    filled = [sum(1 for c in r if c) for r in rows]
    max_filled = max(filled, default=0)
    if max_filled < 2:
        raise ValueError("No tabular data found in the file.")

    threshold = max(2, -(-max_filled * 3 // 4))
    header_idx = next(i for i, n in enumerate(filled) if n >= threshold)

    data = [r for r in rows[header_idx + 1:] if any(r)]
    width = max([len(rows[header_idx])] + [len(r) for r in data])

    header: list[str] = []
    for j in range(width):
        name = rows[header_idx][j] if j < len(rows[header_idx]) else ""
        name = name or f"Column {j + 1}"
        while name in header:
            name += "_"
        header.append(name)

    data = [(r + [""] * width)[:width] for r in data]
    df = pd.DataFrame(data, columns=header).replace("", None)
    return df.dropna(axis=1, how="all")


def _extract_csv(file_bytes: bytes) -> list[dict]:
    """Parse a CSV bank statement into raw rows."""
    return _dataframe_to_rows(_read_csv_robust(file_bytes))


def _extract_xlsx(file_bytes: bytes) -> list[dict]:
    """Parse an XLSX/XLS bank statement into raw rows."""
    return _dataframe_to_rows(_read_excel_robust(file_bytes))


def _dataframe_to_rows(df: pd.DataFrame) -> list[dict]:
    """
    Map a DataFrame with unknown column names to canonical raw row dicts.
    Handles both split debit/credit columns and a single signed amount column.
    """
    df.columns = [str(c) for c in df.columns]
    cols = list(df.columns)

    m = _map_columns(cols)
    date_col, desc_col, drcr_col = m["date"], m["desc"], m["drcr"]
    debit_col, credit_col = m["debit"], m["credit"]
    amount_col, balance_col = m["amount"], m["balance"]

    if date_col is None:
        raise ValueError("No date column found. Please check the file format.")
    if desc_col is None:
        # Fall back to second column if present
        desc_col = cols[1] if len(cols) > 1 else None
    if desc_col is None:
        raise ValueError("No description column found.")

    # Need at least one amount source
    if debit_col is None and credit_col is None and amount_col is None:
        raise ValueError("No amount/debit/credit column found. Cannot extract transactions.")

    rows: list[dict] = []

    for _, row in df.iterrows():
        date_str = _safe_str(row.get(date_col))
        description = _safe_str(row.get(desc_col))
        balance_str = _safe_str(row.get(balance_col)) if balance_col else ""

        if not date_str or not description:
            continue

        # Resolve amount
        if debit_col is not None or credit_col is not None:
            # Bank format with separate debit/credit columns
            debit_val = _safe_str(row.get(debit_col)) if debit_col else ""
            credit_val = _safe_str(row.get(credit_col)) if credit_col else ""

            if debit_val and _is_numeric(debit_val):
                amount_str = f"-{debit_val}"  # debit → negative
            elif credit_val and _is_numeric(credit_val):
                amount_str = credit_val       # credit → positive
            else:
                continue  # skip rows with no amount
        else:
            # Single amount column (may be signed already)
            amount_str = _safe_str(row.get(amount_col))
            if not amount_str or not _is_numeric(amount_str):
                continue
            if drcr_col is not None:
                amount_str = _signed_amount(amount_str, _safe_str(row.get(drcr_col)))

        rows.append({
            "date_str": date_str,
            "description": description,
            "amount_str": amount_str,
            "balance_str": balance_str,
        })

    if not rows:
        raise ValueError("No valid transaction rows could be extracted from the file.")

    return rows


# ---------------------------------------------------------------------------
# PDF extraction
# ---------------------------------------------------------------------------

# Regex patterns used to identify table rows in bank PDFs
# A row is assumed to have: date, description, amounts
_DATE_PATTERN = re.compile(
    r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{2}[/-]\d{2}|\d{1,2}\s+\w{3}\s+\d{4})"
)
_AMOUNT_PATTERN = re.compile(
    r"[\d,]+\.\d{2}"
)


def _extract_pdf(file_bytes: bytes) -> list[dict]:
    """
    Extract transactions from a bank statement PDF using pdfplumber.
    Tries table extraction first; falls back to line-by-line regex parsing.
    """
    rows: list[dict] = []
    header: Optional[list[str]] = None

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            # Attempt structured table extraction
            page_rows: list[dict] = []
            for table in page.extract_tables():
                extracted, header = _parse_pdf_table(table, header)
                page_rows.extend(extracted)
            if not page_rows:
                # Fall back to text-line heuristics
                page_rows = _parse_pdf_text_lines(page.extract_text() or "")
            rows.extend(page_rows)

    if not rows:
        raise ValueError(
            "Could not extract any transactions from the PDF. "
            "The file may be scanned/image-based or in an unsupported format."
        )

    return rows


def _extract_pdf_tables(file_bytes: bytes) -> pd.DataFrame:
    """Return the widest table layout in a PDF (all tables of that width stacked) as a DataFrame."""
    tables: list[list[list]] = []
    has_text = False
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            tables.extend(t for t in page.extract_tables() if t)
            has_text = has_text or bool((page.extract_text() or "").strip())

    if not tables:
        if not has_text:
            raise ValueError(
                "This PDF appears to be scanned/image-based and has no readable text. "
                "Please upload a text-based PDF, CSV, or Excel file."
            )
        raise ValueError("No tables found in the PDF. Please upload a PDF that contains a data table.")

    # Tables split across pages share a column count — merge those with the most rows
    by_width: dict[int, list[list]] = {}
    for t in tables:
        by_width.setdefault(len(t[0]), []).extend(t)
    rows = max(by_width.values(), key=len)
    return _table_from_rows([[c if c is not None else "" for c in r] for r in rows])


def _parse_pdf_table(
    table: list[list], prev_header: Optional[list[str]] = None
) -> tuple[list[dict], Optional[list[str]]]:
    """
    Parse a pdfplumber table (list of rows, each row a list of cell strings).
    Tries to identify header row and map columns. Statement tables that
    continue onto later pages have no header row, so ``prev_header`` (the
    header of the previous table) is reused when the column count matches.

    Returns (rows, header used).
    """
    if not table:
        return [], prev_header

    # Find header row: the first row (before any dated data row) whose cells
    # map to a date column and an amount source. Checking the mapping rather
    # than keywords stops a transaction mentioning "credit" being taken as a header.
    header_idx = -1
    header_row = None
    for i, row in enumerate(table):
        cells = [str(c or "").strip() for c in row]
        if any(_DATE_PATTERN.fullmatch(c) for c in cells):
            break
        m = _map_columns(cells)
        if m["date"] and (m["amount"] or m["debit"] or m["credit"]):
            header_idx = i
            header_row = cells
            break

    if header_row is None:
        if prev_header is None or len(table[0]) != len(prev_header):
            return [], prev_header
        header_row = prev_header

    cols = header_row
    m = _map_columns(cols)
    date_col, desc_col, drcr_col = m["date"], m["desc"], m["drcr"]
    debit_col, credit_col = m["debit"], m["credit"]
    amount_col, balance_col = m["amount"], m["balance"]

    if date_col is None or (debit_col is None and credit_col is None and amount_col is None):
        return [], prev_header

    col_indices = {name: i for i, name in enumerate(cols)}

    rows: list[dict] = []
    for row in table[header_idx + 1:]:
        if not row or all(c is None or str(c).strip() == "" for c in row):
            continue

        def cell(col_name: Optional[str]) -> str:
            if col_name is None:
                return ""
            idx = col_indices.get(col_name)
            if idx is None or idx >= len(row):
                return ""
            return _safe_str(row[idx])

        date_str = cell(date_col)
        description = cell(desc_col) if desc_col else ""
        balance_str = cell(balance_col)

        if not date_str or not _DATE_PATTERN.search(date_str):
            continue

        if debit_col is not None or credit_col is not None:
            debit_val = cell(debit_col)
            credit_val = cell(credit_col)
            if debit_val and _is_numeric(debit_val):
                amount_str = f"-{debit_val}"
            elif credit_val and _is_numeric(credit_val):
                amount_str = credit_val
            else:
                continue
        else:
            amount_str = cell(amount_col)
            if not _is_numeric(amount_str):
                continue
            if drcr_col is not None:
                amount_str = _signed_amount(amount_str, cell(drcr_col))

        if not description:
            continue

        rows.append({
            "date_str": date_str,
            "description": description,
            "amount_str": amount_str,
            "balance_str": balance_str,
        })

    return rows, header_row


def _parse_pdf_text_lines(text: str) -> list[dict]:
    """
    Heuristic fallback: scan text lines for rows that start with a date
    and contain at least one amount.
    """
    rows: list[dict] = []
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    for line in lines:
        date_match = _DATE_PATTERN.match(line)
        if not date_match:
            continue

        amounts = _AMOUNT_PATTERN.findall(line)
        if len(amounts) < 1:
            continue

        date_str = date_match.group(0)
        remainder = line[date_match.end():].strip()

        # Heuristically: last 1–2 numeric tokens are balance/amount
        # First meaningful text chunk is the description
        # This is a best-effort parse for varied PDF layouts
        if len(amounts) >= 2:
            # Assume: ..., debit_or_credit, balance
            amount_str = amounts[-2]
            balance_str = amounts[-1]
        else:
            amount_str = amounts[-1]
            balance_str = ""

        # Description: everything between date and the first amount
        first_amount_pos = remainder.find(amounts[0])
        description = remainder[:first_amount_pos].strip() if first_amount_pos > 0 else remainder

        if not description:
            continue

        rows.append({
            "date_str": date_str,
            "description": description,
            "amount_str": amount_str,
            "balance_str": balance_str,
        })

    return rows


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _safe_str(value) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    # pandas NaN → empty
    if s.lower() in ("nan", "none", "nat", "-"):
        return ""
    return s


def _is_numeric(value: str) -> bool:
    """Return True if the string looks like a number (may contain ₹, commas, Dr/Cr, Rs, etc.)."""
    if not value:
        return False
    val_str = str(value).strip()
    cleaned = re.sub(r"(?i)\b(rs\.?|inr|usd|eur|gbp)\b", "", val_str)
    cleaned = re.sub(r"[₹$€£,\s()]", "", cleaned)
    cleaned = re.sub(r"/-\s*$", "", cleaned)
    cleaned = re.sub(r"\s*(dr|cr)$", "", cleaned, flags=re.IGNORECASE)
    try:
        float(cleaned)
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# JSON extraction
# ---------------------------------------------------------------------------

def _extract_json(file_bytes: bytes) -> list[dict]:
    """Parse a JSON file into raw transaction rows."""
    import json as _json

    try:
        text = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = file_bytes.decode("latin-1")

    try:
        data = _json.loads(text)
    except _json.JSONDecodeError as exc:
        raise ValueError(f"Could not parse JSON: {exc}") from exc

    # Handle JSON array of objects
    if isinstance(data, list) and data and isinstance(data[0], dict):
        df = pd.DataFrame(data)
        return _dataframe_to_rows(df)

    # Handle JSON object with a data key
    if isinstance(data, dict):
        for key in ("data", "rows", "records", "transactions", "items", "results"):
            if key in data and isinstance(data[key], list):
                df = pd.DataFrame(data[key])
                return _dataframe_to_rows(df)
        # Single-level dict → single row
        df = pd.DataFrame([data])
        return _dataframe_to_rows(df)

    raise ValueError("Unsupported JSON structure. Expected an array of objects or an object with a data array.")


# ---------------------------------------------------------------------------
# Generic DataFrame extraction (for universal data analysis)
# ---------------------------------------------------------------------------

def extract_dataframe(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """
    Extract a DataFrame from any supported file type.
    Used by the universal data analysis pipeline (not just bank statements).
    """
    ext = _get_extension(filename)

    if ext == "csv":
        return _read_csv_robust(file_bytes)

    elif ext in ("xlsx", "xls"):
        return _read_excel_robust(file_bytes)

    elif ext == "json":
        import json as _json
        try:
            text = file_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = file_bytes.decode("latin-1")
        try:
            data = _json.loads(text)
        except _json.JSONDecodeError as exc:
            raise ValueError(f"Could not parse JSON: {exc}") from exc
        if isinstance(data, list):
            return pd.DataFrame(data)
        elif isinstance(data, dict):
            for key in ("data", "rows", "records", "transactions", "items", "results"):
                if key in data and isinstance(data[key], list):
                    return pd.DataFrame(data[key])
            return pd.DataFrame([data])
        raise ValueError("Unsupported JSON structure.")

    elif ext == "pdf":
        try:
            return pd.DataFrame(_extract_pdf(file_bytes))
        except ValueError:
            pass  # not a bank statement — fall back to generic tables
        return _extract_pdf_tables(file_bytes)

    else:
        raise ValueError(f"Unsupported file type: '{ext}'.")


def extract_dataframe_multi_sheet(file_bytes: bytes, filename: str) -> dict[str, pd.DataFrame]:
    """
    Extract all sheets from an Excel file as separate DataFrames.
    Returns a dict of {sheet_name: DataFrame}.
    For non-Excel files, returns {"Sheet1": DataFrame}.
    """
    ext = _get_extension(filename)

    if ext in ("xlsx", "xls"):
        try:
            sheets = pd.read_excel(io.BytesIO(file_bytes), dtype=str, sheet_name=None)
            return sheets
        except Exception as exc:
            raise ValueError(f"Could not parse XLSX: {exc}") from exc
    else:
        # Single sheet for non-Excel files
        df = extract_dataframe(file_bytes, filename)
        return {"Sheet1": df}

