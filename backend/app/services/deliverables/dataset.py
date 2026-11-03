"""
Verified report dataset — the single source of truth for every deliverable.

The PDF report, Excel workbook and standalone HTML dashboard are all rendered
from the dict returned by ``build_report_dataset``. Building it re-derives every
total from the raw transaction list and reconciles it against the analysis
engine's metrics; if a critical check fails, ``DatasetVerificationError`` is
raised and no deliverable is produced.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any

TOLERANCE = 0.01          # currency reconciliation tolerance (paise)
MAX_DAILY_ROWS = 400      # beyond this, the daily table lists active days only

_WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class DatasetVerificationError(Exception):
    """Raised when the transaction data does not reconcile with the analysis."""

    def __init__(self, failures: list[dict]):
        self.failures = failures
        names = ", ".join(f["check"] for f in failures)
        super().__init__(f"Dataset verification failed: {names}")


def _r(x: float) -> float:
    return round(float(x) + 0.0, 2)


def _parse_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()


def period_key(start: date, end: date) -> str:
    """'2023-06' for a single-month statement, '2023-04_to_2023-06' otherwise."""
    a, b = start.strftime("%Y-%m"), end.strftime("%Y-%m")
    return a if a == b else f"{a}_to_{b}"


def _period_label(start: date, end: date) -> str:
    if start.strftime("%Y-%m") == end.strftime("%Y-%m") and start.day == 1 and \
            (end + timedelta(days=1)).month != end.month:
        return start.strftime("%B %Y")
    return f"{start.strftime('%d %b %Y')} – {end.strftime('%d %b %Y')}"


def _fingerprint(txns: list[dict]) -> str:
    canon = [
        [t["id"], t["date"], f"{t['amount']:.2f}", t["category"], t["description"]]
        for t in txns
    ]
    raw = json.dumps(canon, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _check(name: str, expected: Any, actual: Any, *, critical: bool, detail: str = "",
           numeric: bool = True) -> dict:
    if numeric:
        diff = _r(actual - expected)
        ok = abs(diff) < TOLERANCE
    else:
        diff = None
        ok = expected == actual
    status = "PASS" if ok else ("FAIL" if critical else "WARN")
    return {
        "check": name, "expected": expected, "actual": actual, "difference": diff,
        "status": status, "critical": critical, "numeric": numeric, "detail": detail,
    }


def build_report_dataset(result: dict, generated_at: datetime | None = None) -> dict:
    """Build and verify the report dataset from a stored AnalysisResult dict."""
    generated_at = generated_at or datetime.now(timezone.utc)
    m = result["metrics"]
    raw_txns: list[dict] = list(result.get("transactions") or [])
    if not raw_txns:
        raise DatasetVerificationError([{
            "check": "Transactions present", "detail": "The analysis contains no transactions.",
        }])

    audit: list[dict] = []

    def log(event: str, detail: str) -> None:
        audit.append({
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "event": event, "detail": detail,
        })

    analysed_at = str(result.get("generated_at") or "")
    log("Analysis loaded", f"Analysis completed at {analysed_at or 'unknown time'}; "
                           f"{len(raw_txns)} transactions in result.")

    # ---- Normalise transactions (stable sort by date keeps statement order) ----
    original_order = raw_txns
    indexed = sorted(enumerate(raw_txns), key=lambda p: (_parse_date(p[1]["date"]), p[0]))
    txns: list[dict] = []
    for seq, (_, t) in enumerate(indexed, 1):
        d = _parse_date(t["date"])
        amount = _r(t.get("amount") or 0)
        week_start = d - timedelta(days=d.weekday())
        txns.append({
            "seq": seq,
            "id": str(t.get("id") or ""),
            "date": d.isoformat(),
            "weekday": _WEEKDAYS[d.weekday()],
            "week_start": week_start.isoformat(),
            "month": d.strftime("%Y-%m"),
            "description": str(t.get("description") or ""),
            "clean_description": str(t.get("clean_description") or t.get("description") or ""),
            "merchant": t.get("merchant") or "",
            "category": t.get("category") or "Other",
            "type": "Credit" if amount > 0 else "Debit",
            "debit": _r(-amount) if amount < 0 else 0.0,
            "credit": amount if amount > 0 else 0.0,
            "amount": amount,
            "balance": None if t.get("balance") is None else _r(t["balance"]),
            "is_recurring": bool(t.get("is_recurring")),
            "recurrence_tag": t.get("recurrence_tag") or "",
            "counterparty": t.get("counterparty") or t.get("merchant") or "",
            "payment_mode": t.get("payment_mode") or "OTHER",
            "confidence": t.get("confidence") or "High",
        })

    start = _parse_date(txns[0]["date"])
    end = _parse_date(txns[-1]["date"])
    days = (end - start).days + 1

    # ---- Core totals, recomputed from transactions ----
    total_income = _r(sum(t["credit"] for t in txns))
    total_expense = _r(sum(t["debit"] for t in txns))
    net = _r(total_income - total_expense)
    savings_rate = _r(net / total_income * 100) if total_income > 0 else 0.0
    credits = [t for t in txns if t["credit"] > 0]
    debits = [t for t in txns if t["debit"] > 0]

    # ---- Categories (expenses) and income sources ----
    cat_acc: dict[str, dict] = defaultdict(lambda: {"count": 0, "amount": 0.0, "largest": 0.0,
                                                    "recurring": 0})
    for t in debits:
        c = cat_acc[t["category"]]
        c["count"] += 1
        c["amount"] += t["debit"]
        c["largest"] = max(c["largest"], t["debit"])
        c["recurring"] += int(t["is_recurring"])
    categories = sorted((
        {
            "category": k, "count": v["count"], "amount": _r(v["amount"]),
            "pct": _r(v["amount"] / total_expense * 100) if total_expense else 0.0,
            "avg": _r(v["amount"] / v["count"]), "largest": _r(v["largest"]),
            "recurring": v["recurring"],
        } for k, v in cat_acc.items()
    ), key=lambda c: -c["amount"])

    inc_acc: dict[str, dict] = defaultdict(lambda: {"count": 0, "amount": 0.0})
    for t in credits:
        inc_acc[t["category"]]["count"] += 1
        inc_acc[t["category"]]["amount"] += t["credit"]
    income_sources = sorted((
        {
            "category": k, "count": v["count"], "amount": _r(v["amount"]),
            "pct": _r(v["amount"] / total_income * 100) if total_income else 0.0,
        } for k, v in inc_acc.items()
    ), key=lambda c: -c["amount"])

    # ---- Daily ----
    by_day: dict[str, list[dict]] = defaultdict(list)
    for t in txns:
        by_day[t["date"]].append(t)
    if days <= MAX_DAILY_ROWS:
        day_keys = [(start + timedelta(days=i)).isoformat() for i in range(days)]
    else:
        day_keys = sorted(by_day)
    daily = []
    last_balance = None
    for k in day_keys:
        rows = by_day.get(k, [])
        for t in rows:
            if t["balance"] is not None:
                last_balance = t["balance"]
        daily.append({
            "date": k, "weekday": _WEEKDAYS[_parse_date(k).weekday()],
            "credits": _r(sum(t["credit"] for t in rows)),
            "debits": _r(sum(t["debit"] for t in rows)),
            "net": _r(sum(t["amount"] for t in rows)),
            "count": len(rows),
            "closing_balance": last_balance,
        })

    # ---- Weekly ----
    wk_acc: dict[str, dict] = defaultdict(lambda: {"credits": 0.0, "debits": 0.0, "count": 0})
    for t in txns:
        w = wk_acc[t["week_start"]]
        w["credits"] += t["credit"]
        w["debits"] += t["debit"]
        w["count"] += 1
    weekly = []
    for k in sorted(wk_acc):
        v = wk_acc[k]
        weekly.append({
            "week_start": k,
            "week_end": (_parse_date(k) + timedelta(days=6)).isoformat(),
            "credits": _r(v["credits"]), "debits": _r(v["debits"]),
            "net": _r(v["credits"] - v["debits"]), "count": v["count"],
        })

    # ---- Weekday pattern ----
    wd_acc = {d: {"debits": 0.0, "count": 0} for d in _WEEKDAYS}
    for t in debits:
        wd_acc[t["weekday"]]["debits"] += t["debit"]
        wd_acc[t["weekday"]]["count"] += 1
    weekday = [{"weekday": d, "debits": _r(v["debits"]), "count": v["count"]}
               for d, v in wd_acc.items()]

    # ---- Monthly ----
    mo_acc: dict[str, dict] = defaultdict(lambda: {"income": 0.0, "expense": 0.0, "count": 0,
                                                   "closing_balance": None})
    for t in txns:
        mm = mo_acc[t["month"]]
        mm["income"] += t["credit"]
        mm["expense"] += t["debit"]
        mm["count"] += 1
        if t["balance"] is not None:
            mm["closing_balance"] = t["balance"]
    monthly = []
    for k in sorted(mo_acc):
        v = mo_acc[k]
        inc, exp = _r(v["income"]), _r(v["expense"])
        monthly.append({
            "month": k, "label": datetime.strptime(k, "%Y-%m").strftime("%b %Y"),
            "income": inc, "expense": exp, "net": _r(inc - exp),
            "savings_rate": _r((inc - exp) / inc * 100) if inc > 0 else 0.0,
            "count": v["count"], "closing_balance": v["closing_balance"],
        })

    # ---- Balances ----
    bal_idx = [i for i, t in enumerate(original_order) if t.get("balance") is not None]
    opening_balance = closing_balance = None
    if bal_idx:
        first, last = original_order[bal_idx[0]], original_order[bal_idx[-1]]
        opening_balance = _r(first["balance"] - (first.get("amount") or 0))
        closing_balance = _r(last["balance"])

    # ---- Reconciliation ----
    checks: list[dict] = [
        _check("Transaction count", int(m["transaction_count"]), len(txns), critical=True,
               detail="Rows in dataset vs. count reported by the analysis engine."),
        _check("Total income (credits)", _r(m["total_income"]), total_income, critical=True,
               detail="Sum of all credit transactions."),
        _check("Total expenses (debits)", _r(m["total_spend"]), total_expense, critical=True,
               detail="Sum of all debit transactions."),
        _check("Net savings", _r(m["savings"]), net, critical=True,
               detail="Income minus expenses."),
        _check("Category totals = total expenses", total_expense,
               _r(sum(c["amount"] for c in categories)), critical=True,
               detail="Sum of every expense category."),
    ]
    engine_cats = {k: _r(v) for k, v in (result.get("category_summary") or {}).items()}
    our_cats = {c["category"]: c["amount"] for c in categories}
    cat_mismatch = sorted(k for k in set(engine_cats) | set(our_cats)
                          if abs(engine_cats.get(k, 0) - our_cats.get(k, 0)) >= TOLERANCE)
    checks.append(_check(
        "Category breakdown matches analysis", "match",
        "match" if not cat_mismatch else "mismatch", critical=True, numeric=False,
        detail="All categories agree." if not cat_mismatch
        else f"Differences in: {', '.join(cat_mismatch)}",
    ))
    checks.append(_check("Daily totals = total expenses", total_expense,
                         _r(sum(d["debits"] for d in daily)), critical=True,
                         detail="Sum of daily debit totals."))
    checks.append(_check("Monthly totals = total income", total_income,
                         _r(sum(x["income"] for x in monthly)), critical=True,
                         detail="Sum of monthly credit totals."))
    ids = [t["id"] for t in txns]
    dup_ids = len(ids) - len(set(ids))
    checks.append(_check("Unique transaction IDs", 0, dup_ids, critical=True,
                         detail="Every transaction must have a distinct ID."))
    in_range = all(start.isoformat() <= t["date"] <= end.isoformat() for t in txns)
    engine_start, engine_end = (str(x)[:10] for x in m["date_range"])
    checks.append(_check(
        "Statement period", f"{engine_start} to {engine_end}",
        f"{start.isoformat()} to {end.isoformat()}", critical=True, numeric=False,
        detail="Earliest and latest transaction dates." if in_range else "Dates out of range.",
    ))

    if opening_balance is not None and closing_balance is not None:
        # Net movement across the first..last rows that carry a printed balance
        balance_net = _r(sum((t.get("amount") or 0)
                             for t in original_order[bal_idx[0]: bal_idx[-1] + 1]))
        checks.append(_check(
            "Balance roll-forward", closing_balance, _r(opening_balance + balance_net),
            critical=False,
            detail=f"Opening balance {opening_balance:,.2f} + net movement must equal the "
                   "closing balance printed on the statement.",
        ))
        breaks = 0
        prev = None
        for t in original_order:
            if t.get("balance") is None:
                prev = None
                continue
            if prev is not None and abs(prev + (t.get("amount") or 0) - t["balance"]) >= TOLERANCE:
                breaks += 1
            prev = t["balance"]
        checks.append(_check("Row-level balance continuity", 0, breaks, critical=False,
                             detail="Rows where previous balance + amount ≠ printed balance."))

    dup_keys: dict[tuple, int] = defaultdict(int)
    for t in txns:
        dup_keys[(t["date"], t["amount"], t["description"].strip().lower())] += 1
    possible_dups = sum(n - 1 for n in dup_keys.values() if n > 1)
    checks.append(_check("Possible duplicate entries", 0, possible_dups, critical=False,
                         detail="Same date, amount and description (may be legitimate)."))

    warnings = list(result.get("parse_warnings") or [])
    checks.append({
        "check": "Rows skipped during parsing", "expected": 0, "actual": len(warnings),
        "difference": len(warnings), "status": "INFO" if warnings else "PASS",
        "critical": False, "numeric": True,
        "detail": "Rows that could not be parsed and were excluded." if warnings
        else "No rows were skipped.",
    })

    failures = [c for c in checks if c["status"] == "FAIL"]
    for c in checks:
        log(f"Check: {c['check']}", f"{c['status']} — expected {c['expected']}, "
                                    f"actual {c['actual']}. {c['detail']}")
    if failures:
        raise DatasetVerificationError(failures)

    fingerprint = _fingerprint(txns)
    log("Dataset verified", f"All critical checks passed. Fingerprint SHA-256 {fingerprint}.")

    largest_expense = max(debits, key=lambda t: t["debit"]) if debits else None
    largest_income = max(credits, key=lambda t: t["credit"]) if credits else None

    source = result.get("insights_source", "rules")
    return {
        "meta": {
            "title": "Financial Analysis Report",
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "period_label": _period_label(start, end),
            "period_key": period_key(start, end),
            "days": days,
            "generated_at": generated_at.isoformat(timespec="seconds"),
            "generated_display": generated_at.strftime("%d %b %Y, %H:%M UTC"),
            "analysed_at": analysed_at,
            "currency": "INR",
            "insights_source": source,
            "insights_label": "AI-generated" if source == "llm" else "Rule-based",
            "fingerprint": fingerprint,
        },
        "kpis": {
            "total_income": total_income,
            "total_expense": total_expense,
            "net": net,
            "savings_rate": savings_rate,
            "transaction_count": len(txns),
            "credit_count": len(credits),
            "debit_count": len(debits),
            "avg_daily_spend": _r(total_expense / days) if days else 0.0,
            "largest_expense": largest_expense,
            "largest_income": largest_income,
            "opening_balance": opening_balance,
            "closing_balance": closing_balance,
            "recurring_count": len(result.get("recurring_summary") or []),
            "income_to_expense_ratio": _r(total_income / total_expense) if total_expense else 0.0,
            "avg_transaction": _r((total_income + total_expense) / len(txns)) if txns else 0.0,
            "avg_debit": _r(total_expense / len(debits)) if debits else 0.0,
            "avg_credit": _r(total_income / len(credits)) if credits else 0.0,
        },
        "transactions": txns,
        "categories": categories,
        "income_sources": income_sources,
        "top_payers": list(m.get("top_payers") or []),
        "top_payees": list(m.get("top_payees") or []),
        "intelligence": dict(m.get("intelligence") or {}),
        "daily": daily,
        "weekly": weekly,
        "weekday": weekday,
        "monthly": monthly,
        "recurring": list(result.get("recurring_summary") or []),
        "insights": list(result.get("insights") or []),
        "parse_warnings": warnings,
        "reconciliation": checks,
        "audit_log": audit,
    }
