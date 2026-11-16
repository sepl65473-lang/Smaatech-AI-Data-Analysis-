"""
Cleaner service — Phase 2

Converts raw row dicts from ingestion into structured Transaction objects:
  - Parse date_str → datetime.date (multiple format attempts)
  - Parse amount_str → float (strip ₹, commas, handle Dr/Cr suffix)
  - Determine credit/debit sign
  - Strip noise from description, extract merchant name
  - Assign UUID to each transaction
"""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime
from typing import Optional

from app.models.transaction import Transaction


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

_DATE_FORMATS = [
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%Y-%m-%d",
    "%d %b %Y",       # 15 Jan 2024
    "%d %B %Y",       # 15 January 2024
    "%d/%m/%y",       # 15/01/24
    "%d-%m-%y",
    "%m/%d/%Y",
    "%d.%m.%Y",
    "%d.%m.%y",
    "%b %d, %Y",      # Jan 15, 2024
    "%B %d, %Y",
    "%Y/%m/%d",
    "%Y-%m-%d %H:%M:%S",
    "%d/%m/%Y %H:%M:%S",
    "%d-%m-%Y %H:%M:%S",
    "%m/%d/%Y %H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%d/%m/%Y %H:%M",
    "%d-%m-%Y %H:%M",
]


def _parse_date(date_str: str) -> Optional[date]:
    """Try multiple date formats, ISO formats, Excel serials, and robust fallbacks."""
    if not date_str:
        return None
    cleaned = str(date_str).strip()
    if not cleaned or cleaned.lower() in ("nan", "none", "null", "nat", ""):
        return None

    # Handle Excel float/integer serial dates (e.g. 45470)
    try:
        parts = cleaned.split(".")
        if cleaned.replace(".", "", 1).isdigit() and len(parts[0]) in (5, 6):
            serial = float(cleaned)
            if 30000 <= serial <= 60000:
                from datetime import timedelta
                return (datetime(1899, 12, 30) + timedelta(days=serial)).date()
    except (ValueError, OverflowError):
        pass

    # Normalise whitespace / remove 'T' ISO separator
    cleaned_iso = cleaned.replace("T", " ")
    first_part = cleaned_iso.split()[0] if " " in cleaned_iso else cleaned_iso

    for target in (cleaned, cleaned_iso, first_part):
        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(target, fmt).date()
            except ValueError:
                continue

    # Fallback to dateutil
    try:
        import dateutil.parser as dparser
        return dparser.parse(cleaned, fuzzy=True, dayfirst=True).date()
    except Exception:
        pass

    # Fallback to pandas
    try:
        import pandas as pd
        dt = pd.to_datetime(cleaned, errors="coerce", dayfirst=True)
        if pd.notna(dt):
            return dt.date()
    except Exception:
        pass

    return None


# ---------------------------------------------------------------------------
# Amount parsing
# ---------------------------------------------------------------------------

def _parse_amount(amount_str: str) -> Optional[float]:
    """
    Parse a raw amount string into a float with correct debit/credit sign.

    Rules:
    - If explicitly marked Dr/debit or has leading minus/parens -> negative (debit)
    - If explicitly marked Cr/credit and no minus -> positive (credit)
    - Prevents double-negative flipping if amount is both '-...' and '... Dr'
    """
    if not amount_str:
        return None

    raw = str(amount_str).strip()
    if not raw:
        return None

    is_debit = False
    is_credit = False

    # Check for Dr/Cr suffixes or prefixes
    if re.search(r"\b(dr|debit)\b", raw, re.IGNORECASE) or re.search(r"\s*(Dr|DR)$", raw):
        is_debit = True
    elif re.search(r"\b(cr|credit)\b", raw, re.IGNORECASE) or re.search(r"\s*(Cr|CR)$", raw):
        is_credit = True

    # Check for minus sign or parentheses e.g. (500.00) or 500.00-
    has_minus = False
    if raw.startswith("-") or raw.endswith("-") or (raw.startswith("(") and raw.endswith(")")):
        has_minus = True

    # Strip currency words, symbols, commas, spaces, parens, Dr/Cr suffixes, /-
    cleaned = re.sub(r"(?i)\b(rs\.?|inr|usd|eur|gbp)\b", "", raw)
    cleaned = re.sub(r"[₹$€£,\s()]", "", cleaned)
    cleaned = re.sub(r"(?i)\s*(dr|cr|debit|credit)$", "", cleaned)
    cleaned = re.sub(r"^-", "", cleaned)
    cleaned = re.sub(r"-$", "", cleaned)

    try:
        val = float(cleaned)
        if is_debit or has_minus:
            return -round(abs(val), 2)
        elif is_credit:
            return round(abs(val), 2)
        else:
            return round(val, 2)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Description cleaning & merchant extraction
# ---------------------------------------------------------------------------

_REF_PATTERN = re.compile(
    r"\b(?:UPI|IMPS|NEFT|RTGS|Ref(?:erence)?|Txn|Chq|Cheque|UTR)[/:\s#-]*(?:NO[.:\s]*|UTR[/:\s#-]*)?([a-zA-Z0-9]{6,25})\b|"
    r"\b([0-9]{8,22})\b",
    re.IGNORECASE,
)

# Patterns to strip from description (UPI ref IDs, NEFT codes, etc.)
_NOISE_PATTERNS = [
    r"\b(UPI|IMPS|NEFT|RTGS|NACH|ACH|BBPS|UTR|CHQ|CHEQUE)\b",
    r"\bRef(?:erence)?[\s#:]*\w+",
    r"\bTxn[\s#:]*\w+",
    r"\bRef\s*No[.\s:]*[\w/-]+",
    r"\bNo[.\s:]*\d+",
    r"\b\d{6,}\b",                          # long numeric ref IDs
    r"@[a-z0-9]+",                           # UPI VPA suffix (@okaxis, @ybl)
    r"\b(ok|ybl|paytm|icici|sbi|upi|neft|imps|axis|hdfc|kotak|rbl)\b",
    r"[/|-]{1,}",                            # repeated delimiters & slashes
    r"\s{2,}",                               # multiple spaces → single
]

_NOISE_RE = re.compile("|".join(_NOISE_PATTERNS), flags=re.IGNORECASE)

# Prefixes to remove for merchant name extraction
_PREFIX_STRIP = re.compile(
    r"^(UPI[-/\s]CR[-/\s]|UPI[-/\s]DR[-/\s]|UPI-|NEFT[-/\s]CR[-/\s]|NEFT[-/\s]DR[-/\s]|"
    r"NEFT[-/\s]|IMPS[-/\s]|RTGS[-/\s]|ACH[-/\s]|NACH[-/\s]|INB[-/\s]|"
    r"POS[-/\s]|ATM[-/\s]|BILL[-/\s]PAY[-/\s]|BILLPAY[-/\s]|"
    r"CLG[-/\s]|ECS[-/\s]|MMT[-/\s]|TRANSFER[-/\s])",
    flags=re.IGNORECASE,
)


def _clean_description(raw: str) -> tuple[str, Optional[str], Optional[str]]:
    """
    Returns (clean_description, merchant_name, reference_no).
    Extracts UTR/reference number, strips UPI/NEFT noise, and extracts merchant.
    """
    text = raw.strip()

    # Extract reference number before stripping
    reference_no = None
    ref_match = _REF_PATTERN.search(text)
    if ref_match:
        reference_no = ref_match.group(1) or ref_match.group(2)

    # Strip known prefixes
    text = _PREFIX_STRIP.sub("", text).strip()

    # Remove noise tokens
    text = _NOISE_RE.sub(" ", text).strip()

    # Collapse whitespace and strip dangling punctuation
    text = re.sub(r"^[/\s,-]+|[/\s,-]+$", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    # Extract merchant: first 1-3 meaningful words (capitalised)
    tokens = [t for t in text.split() if len(t) > 1 and t.lower() not in ("to", "from", "by", "at", "on")]
    merchant = " ".join(tokens[:3]).title() if tokens else None

    clean_desc = text.title() if text else raw.strip().title()
    return clean_desc, merchant, reference_no


def _detect_payment_mode(raw: str) -> str:
    """Classify transaction rails into UPI, NEFT, RTGS, IMPS, CHEQUE, IFT, ACH, CARD, OTHER."""
    t = raw.upper()
    if "UPI" in t or "@" in t:
        return "UPI"
    if "RTGS" in t or re.search(r"\bR42\d+", t):
        return "RTGS"
    if "NEFT" in t or re.search(r"\bAXIC\d+", t) or re.search(r"\bN\d{10,}", t):
        return "NEFT"
    if "IMPS" in t or "P2A" in t:
        return "IMPS"
    if "IFT" in t or "INTERNAL" in t or "TPARTY" in t:
        return "IFT"
    if "CHQ" in t or "CHEQUE" in t or "CLG" in t:
        return "CHEQUE"
    if "ACH" in t or "NACH" in t or "ECS" in t:
        return "ACH"
    if "POS" in t or "E-COM" in t or "CARD" in t:
        return "CARD"
    return "OTHER"


def _extract_counterparty(raw: str, clean_desc: str, merchant: Optional[str]) -> Optional[str]:
    """Extract and normalize counterparty name by removing bank transaction prefixes and routing codes."""
    # Remove routing codes like AXIC... or N... at the beginning
    words = clean_desc.split()
    if words and (re.match(r"^[A-Za-z]{2,5}\d{6,}", words[0], re.IGNORECASE) or re.match(r"^N\d{8,}", words[0], re.IGNORECASE)):
        meaningful = words[1:]
        if meaningful:
            return " ".join(meaningful[:3]).title()

    return merchant or (clean_desc[:30] if clean_desc else None)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def clean_transactions(raw_rows: list[dict]) -> tuple[list[Transaction], list[str]]:
    """
    Convert raw row dicts from ingestion into a list of Transaction objects.

    Returns:
        transactions — List[Transaction] with parsed fields
        warnings     — List[str] of non-fatal parse issues (e.g. unparseable dates)
    """
    transactions: list[Transaction] = []
    warnings: list[str] = []

    for idx, row in enumerate(raw_rows):
        date_str = (row.get("date_str") or "").strip()
        description = (row.get("description") or "").strip()
        amount_str = (row.get("amount_str") or "").strip()
        balance_str = (row.get("balance_str") or "").strip()

        # --- Date ---
        parsed_date = _parse_date(date_str)
        if parsed_date is None:
            warnings.append(f"Row {idx + 1}: Could not parse date '{date_str}' — row skipped.")
            continue

        # --- Amount ---
        amount = _parse_amount(amount_str)
        if amount is None:
            warnings.append(f"Row {idx + 1}: Could not parse amount '{amount_str}' — row skipped.")
            continue

        # --- Balance ---
        balance: Optional[float] = None
        if balance_str:
            balance = _parse_amount(balance_str)
            if balance is not None:
                balance = abs(balance)  # Running balance is a non-negative ledger balance

        # --- Description & Reference ---
        clean_desc, merchant, reference_no = _clean_description(description)
        payment_mode = _detect_payment_mode(description)
        counterparty = _extract_counterparty(description, clean_desc, merchant)

        txn = Transaction(
            id=str(uuid.uuid4()),
            date=parsed_date,
            description=description,
            clean_description=clean_desc,
            amount=amount,
            balance=balance,
            category="Other",        # assigned by categorizer
            is_recurring=False,      # assigned by recurring_detector
            recurrence_tag=None,
            merchant=counterparty or merchant,
            reference_no=reference_no,
            counterparty=counterparty or merchant,
            payment_mode=payment_mode,
            confidence="High",
            classification_source="rules",
        )
        transactions.append(txn)

    return transactions, warnings
