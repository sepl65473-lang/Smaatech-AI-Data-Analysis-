"""
Metrics engine — Phase 2

Computes key financial metrics from a list of categorized transactions:
  - total_income, total_spend, savings, savings_rate
  - top_categories (by spend)
  - biggest_transactions (top 5 by abs amount)
  - transaction_count
  - date_range
"""

from __future__ import annotations

from datetime import date
from collections import defaultdict

from app.models.transaction import Transaction, CategoryStat
from app.models.result import Metrics


# Categories that represent money coming in (credits)
_INCOME_CATEGORIES = {"Salary", "Income"}


def compute_metrics(transactions: list[Transaction]) -> Metrics:
    """
    Compute financial metrics from a categorized transaction list.
    Returns a Metrics object.
    """
    if not transactions:
        today = date.today()
        return Metrics(
            total_income=0.0,
            total_spend=0.0,
            savings=0.0,
            savings_rate=0.0,
            top_categories=[],
            biggest_transactions=[],
            transaction_count=0,
            date_range=(today, today),
        )

    # ---- Income, spend, and counts ----
    credits_list = [t for t in transactions if t.amount > 0]
    debits_list = [t for t in transactions if t.amount < 0]

    credit_count = len(credits_list)
    debit_count = len(debits_list)

    total_income = round(sum(t.amount for t in credits_list), 2)
    total_spend = round(sum(abs(t.amount) for t in debits_list), 2)

    savings = round(total_income - total_spend, 2)
    savings_rate = round((savings / total_income * 100), 2) if total_income > 0 else 0.0

    # Averages & Extrema
    total_volume = total_income + total_spend
    avg_txn = round(total_volume / len(transactions), 2) if transactions else 0.0
    avg_debit = round(total_spend / debit_count, 2) if debit_count else 0.0
    avg_credit = round(total_income / credit_count, 2) if credit_count else 0.0

    largest_credit = max(credits_list, key=lambda t: t.amount, default=None)
    largest_debit = min(debits_list, key=lambda t: t.amount, default=None)

    # ---- Category breakdown (debits only) ----
    category_totals: dict[str, float] = defaultdict(float)
    for txn in debits_list:
        category_totals[txn.category] += abs(txn.amount)

    top_categories: list[CategoryStat] = []
    for cat, amount in sorted(category_totals.items(), key=lambda x: x[1], reverse=True):
        pct = round((amount / total_spend * 100), 1) if total_spend > 0 else 0.0
        top_categories.append(CategoryStat(
            category=cat,
            amount=round(amount, 2),
            percentage=pct,
        ))

    # ---- Biggest transactions (top 5 by absolute value) ----
    biggest = sorted(transactions, key=lambda t: abs(t.amount), reverse=True)[:5]

    # ---- Date range ----
    dates = [t.date for t in transactions]
    date_range = (min(dates), max(dates))

    # ---- Top Payers (Credits) & Top Payees (Debits) ----
    payer_acc: dict[str, dict] = defaultdict(lambda: {"count": 0, "amount": 0.0, "dates": []})
    for t in credits_list:
        name = t.merchant or t.clean_description or "Other Income"
        payer_acc[name]["count"] += 1
        payer_acc[name]["amount"] += t.amount
        payer_acc[name]["dates"].append(t.date)
    top_payers = sorted(
        [
            {
                "payer": k,
                "count": v["count"],
                "amount": round(v["amount"], 2),
                "pct": round(v["amount"] / total_income * 100, 1) if total_income else 0.0,
                "first_date": min(v["dates"]).isoformat() if v["dates"] else "",
                "last_date": max(v["dates"]).isoformat() if v["dates"] else "",
                "avg_amount": round(v["amount"] / v["count"], 2) if v["count"] else 0.0,
            }
            for k, v in payer_acc.items()
        ],
        key=lambda x: x["amount"],
        reverse=True,
    )[:10]

    payee_acc: dict[str, dict] = defaultdict(lambda: {"count": 0, "amount": 0.0, "dates": []})
    for t in debits_list:
        name = t.merchant or t.clean_description or "Other Expense"
        payee_acc[name]["count"] += 1
        payee_acc[name]["amount"] += abs(t.amount)
        payee_acc[name]["dates"].append(t.date)
    top_payees = sorted(
        [
            {
                "payee": k,
                "count": v["count"],
                "amount": round(v["amount"], 2),
                "pct": round(v["amount"] / total_spend * 100, 1) if total_spend else 0.0,
                "first_date": min(v["dates"]).isoformat() if v["dates"] else "",
                "last_date": max(v["dates"]).isoformat() if v["dates"] else "",
                "avg_amount": round(v["amount"] / v["count"], 2) if v["count"] else 0.0,
            }
            for k, v in payee_acc.items()
        ],
        key=lambda x: x["amount"],
        reverse=True,
    )[:10]

    # ---- Balances & Reconciliation ----
    # Sort chronological by date
    chrono = sorted(transactions, key=lambda t: t.date)
    bal_txns = [t for t in chrono if t.balance is not None]
    opening_balance = None
    closing_balance = None
    is_reconciled = True
    reconciliation_delta = 0.0

    if bal_txns:
        first_b = bal_txns[0]
        last_b = bal_txns[-1]
        # Opening balance = balance before first recorded balance transaction
        opening_balance = round(first_b.balance - first_b.amount, 2)
        closing_balance = round(last_b.balance, 2)
        expected_closing = round(opening_balance + total_income - total_spend, 2)
        reconciliation_delta = round(expected_closing - closing_balance, 2)
        is_reconciled = abs(reconciliation_delta) <= 1.0  # Within ₹1 tolerance

    # ---- Cash-Flow Analytics: Daily, Weekly, Monthly ----
    from datetime import timedelta
    daily_acc: dict[str, dict] = defaultdict(lambda: {"credits": 0.0, "debits": 0.0, "count": 0, "balance": None})
    for t in chrono:
        k = t.date.isoformat()
        if t.amount > 0:
            daily_acc[k]["credits"] += t.amount
        else:
            daily_acc[k]["debits"] += abs(t.amount)
        daily_acc[k]["count"] += 1
        if t.balance is not None:
            daily_acc[k]["balance"] = t.balance

    daily_cash_flow = []
    running_cumulative = 0.0
    for d_str in sorted(daily_acc):
        c = round(daily_acc[d_str]["credits"], 2)
        d = round(daily_acc[d_str]["debits"], 2)
        net_val = round(c - d, 2)
        running_cumulative = round(running_cumulative + net_val, 2)
        daily_cash_flow.append({
            "date": d_str,
            "credits": c,
            "debits": d,
            "net": net_val,
            "cumulative": running_cumulative,
            "balance": daily_acc[d_str]["balance"],
            "count": daily_acc[d_str]["count"],
        })

    weekly_acc: dict[str, dict] = defaultdict(lambda: {"credits": 0.0, "debits": 0.0, "count": 0})
    for t in chrono:
        w_start = (t.date - timedelta(days=t.date.weekday())).isoformat()
        if t.amount > 0:
            weekly_acc[w_start]["credits"] += t.amount
        else:
            weekly_acc[w_start]["debits"] += abs(t.amount)
        weekly_acc[w_start]["count"] += 1

    weekly_cash_flow = [
        {
            "week_start": w,
            "credits": round(weekly_acc[w]["credits"], 2),
            "debits": round(weekly_acc[w]["debits"], 2),
            "net": round(weekly_acc[w]["credits"] - weekly_acc[w]["debits"], 2),
            "count": weekly_acc[w]["count"],
        }
        for w in sorted(weekly_acc)
    ]

    monthly_acc: dict[str, dict] = defaultdict(lambda: {"income": 0.0, "expense": 0.0, "count": 0})
    for t in chrono:
        m_key = t.date.strftime("%Y-%m")
        if t.amount > 0:
            monthly_acc[m_key]["income"] += t.amount
        else:
            monthly_acc[m_key]["expense"] += abs(t.amount)
        monthly_acc[m_key]["count"] += 1

    monthly_cash_flow = [
        {
            "month": m,
            "income": round(monthly_acc[m]["income"], 2),
            "expense": round(monthly_acc[m]["expense"], 2),
            "net": round(monthly_acc[m]["income"] - monthly_acc[m]["expense"], 2),
            "savings_rate": round((monthly_acc[m]["income"] - monthly_acc[m]["expense"]) / monthly_acc[m]["income"] * 100, 1) if monthly_acc[m]["income"] > 0 else 0.0,
            "count": monthly_acc[m]["count"],
        }
        for m in sorted(monthly_acc)
    ]

    income_to_expense_ratio = round(total_income / total_spend, 2) if total_spend > 0 else 0.0

    # Income category breakdown
    inc_cat_acc: dict[str, float] = defaultdict(float)
    for t in credits_list:
        inc_cat_acc[t.category] += t.amount
    income_categories = [
        CategoryStat(
            category=c,
            amount=round(a, 2),
            percentage=round(a / total_income * 100, 1) if total_income else 0.0,
        )
        for c, a in sorted(inc_cat_acc.items(), key=lambda x: x[1], reverse=True)
    ]

    # Transaction Intelligence metrics
    weekend_txns = [t for t in transactions if t.date.weekday() in (5, 6)]
    weekend_spend = round(sum(abs(t.amount) for t in weekend_txns if t.amount < 0), 2)
    weekend_income = round(sum(t.amount for t in weekend_txns if t.amount > 0), 2)
    missing_ref_txns = [t for t in transactions if not t.reference_no]
    uncat_txns = [t for t in transactions if t.category.lower() in ("other", "uncategorized")]

    # Tier 1: Exact Duplicate UTR / Reference Detection
    utr_groups: dict[str, list] = defaultdict(list)
    for t in transactions:
        ref = (t.reference_no or "").strip()
        if ref:
            utr_groups[ref].append(t.id)
    exact_duplicate_utr_groups = [
        {"reference_no": k, "count": len(v), "ids": v}
        for k, v in utr_groups.items() if len(v) > 1
    ]

    # Tier 2: Potential Duplicate Payments (Suspected Double Payments)
    # Rule: Same date + same signed amount + same normalized counterparty (or narration similarity)
    # DOES NOT require matching UTRs: accidental double-payments receive distinct UTRs from the bank.
    pot_dup_groups: dict[tuple, list] = defaultdict(list)
    for t in transactions:
        cp = (t.counterparty or t.merchant or "").strip().lower()
        if cp:
            pot_dup_groups[(t.date.isoformat(), t.amount, cp)].append(t.id)
        else:
            clean_desc = (t.clean_description or t.description or "").strip().lower()
            if clean_desc:
                pot_dup_groups[(t.date.isoformat(), t.amount, clean_desc)].append(t.id)
    potential_duplicate_payments = [
        {"key": k, "count": len(v), "ids": v}
        for k, v in pot_dup_groups.items() if len(v) > 1
    ]

    # Tier 3: Same-Day Same-Amount Matches (Informational Batch Payments)
    # Rule: Same date + same signed amount across all counterparties
    same_day_groups: dict[tuple, list] = defaultdict(list)
    for t in transactions:
        same_day_groups[(t.date.isoformat(), t.amount)].append(t.id)
    same_day_matches = [
        {"date": k[0], "amount": k[1], "count": len(v), "ids": v}
        for k, v in same_day_groups.items() if len(v) > 1
    ]
    same_day_matches_spend = round(sum(abs(t.amount) for t in transactions if any(t.id in d["ids"] for d in same_day_matches) and t.amount < 0), 2)
    potential_dups = same_day_matches
    strict_dups = potential_duplicate_payments

    # Repeated payees (debits only — operational disbursements to repeat vendors/partners)
    debit_party_counts: dict[str, int] = defaultdict(int)
    for t in debits_list:
        p_name = t.counterparty or t.merchant or ""
        if p_name:
            debit_party_counts[p_name] += 1
    repeated_debits = [t for t in debits_list if debit_party_counts.get(t.counterparty or t.merchant or "", 0) > 1]
    repeated_debits_spend = round(sum(abs(t.amount) for t in repeated_debits), 2)
    recurring_debit_payees_count = sum(1 for c in debit_party_counts.values() if c > 1)
    repeated_debit_pct = round((repeated_debits_spend / total_spend * 100), 1) if total_spend > 0 else 0.0

    # Repeat remitters (credits only — incoming client deposits)
    credit_party_counts: dict[str, int] = defaultdict(int)
    for t in credits_list:
        p_name = t.counterparty or t.merchant or ""
        if p_name:
            credit_party_counts[p_name] += 1
    repeat_credits = [t for t in credits_list if credit_party_counts.get(t.counterparty or t.merchant or "", 0) > 1]
    repeat_credits_income = round(sum(t.amount for t in repeat_credits), 2)
    recurring_credit_remitters_count = sum(1 for c in credit_party_counts.values() if c > 1)
    repeat_credit_pct = round((repeat_credits_income / total_income * 100), 1) if total_income > 0 else 0.0

    # Category Review Queue Statistics (Classified vs Unclassified Spend)
    classified_debits = [t for t in debits_list if t.category.lower() not in ("other", "uncategorized")]
    unclassified_debits = [t for t in debits_list if t.category.lower() in ("other", "uncategorized")]
    classified_debit_spend = round(sum(abs(t.amount) for t in classified_debits), 2)
    unclassified_debit_spend = round(sum(abs(t.amount) for t in unclassified_debits), 2)
    classified_debit_pct = round((classified_debit_spend / total_spend * 100), 1) if total_spend > 0 else 0.0
    unclassified_debit_pct = round((unclassified_debit_spend / total_spend * 100), 1) if total_spend > 0 else 0.0

    intelligence = {
        "weekend_count": len(weekend_txns),
        "weekend_spend": weekend_spend,
        "weekend_income": weekend_income,
        "missing_ref_count": len(missing_ref_txns),
        "uncategorized_count": len(uncat_txns),
        # Tier 1: Exact Duplicate Reference / UTR Detection
        "exact_duplicate_utr_groups": len(exact_duplicate_utr_groups),
        "exact_duplicate_utr_count": sum(d["count"] for d in exact_duplicate_utr_groups),
        # Tier 2: Potential Duplicate Payments (Date + Signed Amount + Counterparty, regardless of UTR)
        "potential_duplicate_payment_groups": len(potential_duplicate_payments),
        "potential_duplicate_payment_count": sum(d["count"] for d in potential_duplicate_payments),
        "potential_duplicate_payment_spend": round(sum(abs(t.amount) for t in transactions if any(t.id in d["ids"] for d in potential_duplicate_payments) and t.amount < 0), 2),
        "duplicate_detection_status": "No potential duplicates detected under the applied matching rules." if len(potential_duplicate_payments) == 0 else f"{len(potential_duplicate_payments)} potential duplicate payment groups flagged for review.",
        # Tier 3: Same-Day Same-Amount Matches (Informational Batch Payments)
        "same_day_matches_groups": len(same_day_matches),
        "same_day_matches_count": sum(d["count"] for d in same_day_matches),
        "same_day_matches_spend": same_day_matches_spend,
        # Backward-compatibility aliases
        "potential_duplicate_groups": len(same_day_matches),
        "potential_duplicate_txns": sum(d["count"] for d in same_day_matches),
        "strict_duplicate_groups": len(potential_duplicate_payments),
        "strict_duplicate_count": sum(d["count"] for d in potential_duplicate_payments),
        "recurring_debit_payees_count": recurring_debit_payees_count,
        "repeated_debit_count": len(repeated_debits),
        "repeated_debit_spend": repeated_debits_spend,
        "repeated_debit_pct": repeated_debit_pct,
        "recurring_credit_remitters_count": recurring_credit_remitters_count,
        "repeat_credit_count": len(repeat_credits),
        "repeat_credit_income": repeat_credits_income,
        "repeat_credit_pct": repeat_credit_pct,
        "classified_debit_count": len(classified_debits),
        "classified_debit_spend": classified_debit_spend,
        "classified_debit_pct": classified_debit_pct,
        "unclassified_debit_count": len(unclassified_debits),
        "unclassified_debit_spend": unclassified_debit_spend,
        "unclassified_debit_pct": unclassified_debit_pct,
    }

    return Metrics(
        total_income=total_income,
        total_spend=total_spend,
        savings=savings,
        savings_rate=savings_rate,
        top_categories=top_categories,
        biggest_transactions=biggest,
        transaction_count=len(transactions),
        date_range=date_range,
        credit_count=credit_count,
        debit_count=debit_count,
        opening_balance=opening_balance,
        closing_balance=closing_balance,
        is_reconciled=is_reconciled,
        reconciliation_delta=reconciliation_delta,
        avg_transaction_amount=avg_txn,
        avg_debit_amount=avg_debit,
        avg_credit_amount=avg_credit,
        largest_credit=largest_credit,
        largest_debit=largest_debit,
        top_payers=top_payers,
        top_payees=top_payees,
        daily_cash_flow=daily_cash_flow,
        weekly_cash_flow=weekly_cash_flow,
        monthly_cash_flow=monthly_cash_flow,
        income_to_expense_ratio=income_to_expense_ratio,
        income_categories=income_categories,
        intelligence=intelligence,
    )


def build_category_summary(transactions: list[Transaction]) -> dict[str, float]:
    """
    Returns a flat dict of {category: total_spend} for debit transactions.
    Used for the category_summary field in AnalysisResult.
    """
    totals: dict[str, float] = defaultdict(float)
    for txn in transactions:
        if txn.amount < 0:
            totals[txn.category] += abs(txn.amount)
    return {k: round(v, 2) for k, v in sorted(totals.items(), key=lambda x: x[1], reverse=True)}
