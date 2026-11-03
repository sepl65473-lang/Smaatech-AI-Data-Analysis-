"""
Recurring detector service — Phase 2

Algorithm:
1. Normalise merchant names (lowercase, strip UPI/NEFT suffixes, remove specials)
2. Group transactions by (normalised_merchant, amount_bucket)
3. Flag as recurring if group size ≥ 2 AND date range spans ≥ 25 days
4. Assign recurrence_tag based on merchant keywords

Returns:
    (updated_transactions, recurring_summary_list)
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Optional

from app.models.transaction import Transaction, RecurringItem


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

# Suffixes and tokens to strip from merchant names
_STRIP_PATTERNS = re.compile(
    r"@\w+|"                                     # UPI VPA suffixes: @okaxis, @ybl
    r"\b(upi|neft|imps|rtgs|nach|ach|clg)\b|"  # payment mode prefixes
    r"\b(paytm|phonepe|googlepay|gpay|bhim)\b|"  # payment apps
    r"\b(india|pvt|ltd|llp|inc|corp|co)\b|"     # company suffixes
    r"[^a-z0-9\s]",                              # non-alphanumeric (except spaces)
    flags=re.IGNORECASE,
)


def _normalise_merchant(merchant: Optional[str], description: str) -> str:
    """
    Produce a normalised key for grouping recurring transactions.
    Uses merchant if available, otherwise falls back to description.
    """
    text = (merchant or description or "").lower()
    text = _STRIP_PATTERNS.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    # Take first 3 words to stay stable across description variations
    words = text.split()
    return " ".join(words[:3]) if words else text


def _amount_bucket(amount: float) -> int:
    """Round amount to nearest ₹10 bucket to handle small fluctuations."""
    return round(abs(amount) / 10) * 10


# ---------------------------------------------------------------------------
# Recurrence tag classification
# ---------------------------------------------------------------------------

_TAG_RULES: list[tuple[str, re.Pattern]] = [
    ("EMI",          re.compile(r"\bemi\b|loan|equated", re.IGNORECASE)),
    ("SIP",          re.compile(r"\bsip\b|mutual\s*fund|nps\b|ppf\b", re.IGNORECASE)),
    ("RENT",         re.compile(r"\brent\b|house\s*rent|pg\s*rent", re.IGNORECASE)),
    ("INSURANCE",    re.compile(r"insurance|lic\b|policy\s*prem", re.IGNORECASE)),
    ("SUBSCRIPTION", re.compile(r".*", re.IGNORECASE)),  # catch-all
]


def _classify_tag(merchant: str, description: str) -> str:
    text = f"{merchant} {description}"
    for tag, pattern in _TAG_RULES:
        if pattern.search(text):
            return tag
    return "SUBSCRIPTION"


# ---------------------------------------------------------------------------
# Frequency estimation
# ---------------------------------------------------------------------------

def _estimate_frequency(dates: list) -> str:
    """Estimate payment frequency from a list of dates."""
    if len(dates) < 2:
        return "irregular"
    sorted_dates = sorted(dates)
    gaps = [(sorted_dates[i + 1] - sorted_dates[i]).days for i in range(len(sorted_dates) - 1)]
    avg_gap = sum(gaps) / len(gaps)
    if avg_gap <= 10:
        return "weekly"
    elif avg_gap <= 45:
        return "monthly"
    elif avg_gap <= 100:
        return "quarterly"
    else:
        return "irregular"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def detect_recurring(transactions: list[Transaction]) -> tuple[list[Transaction], list[RecurringItem]]:
    """
    Identify recurring transactions and return:
        - Updated transaction list (is_recurring and recurrence_tag set)
        - List[RecurringItem] for the result summary
    """
    # Only examine debits (negative amounts) — recurring payments go out
    # But also check SIPs/investments which are debits
    candidates = [t for t in transactions if t.amount < 0]

    # Group by (normalised_merchant, amount_bucket)
    groups: dict[tuple[str, int], list[Transaction]] = defaultdict(list)
    for txn in candidates:
        key = (_normalise_merchant(txn.merchant, txn.description), _amount_bucket(txn.amount))
        groups[key].append(txn)

    # Determine which groups are genuinely recurring
    recurring_ids: set[str] = set()
    recurring_summary: list[RecurringItem] = []

    for (norm_merchant, _bucket), group in groups.items():
        if len(group) < 2:
            continue

        dates = [t.date for t in group]
        date_span = (max(dates) - min(dates)).days

        if date_span < 25:
            # All transactions within a short window — probably not truly recurring
            continue

        # Mark transactions as recurring
        for txn in group:
            recurring_ids.add(txn.id)

        # Use the representative transaction for display
        rep = group[0]
        tag = _classify_tag(norm_merchant, rep.description)
        freq = _estimate_frequency(dates)

        # Use median amount for display
        amounts = sorted([abs(t.amount) for t in group])
        median_amount = amounts[len(amounts) // 2]

        recurring_summary.append(RecurringItem(
            merchant=norm_merchant.title(),
            amount=round(median_amount, 2),
            tag=tag,
            frequency=freq,
            occurrences=len(group),
        ))

    # Update transactions
    for txn in transactions:
        if txn.id in recurring_ids:
            txn.is_recurring = True
            txn.recurrence_tag = _classify_tag(
                txn.merchant or "", txn.description
            )

    # Sort recurring summary by amount descending
    recurring_summary.sort(key=lambda r: r.amount, reverse=True)

    return transactions, recurring_summary
