"""
Insight generator — Phase 3

Generates exactly 5 personalised financial insights via the Groq LLM.
Falls back to rule-based insights if the LLM is unavailable or fails.

Retry strategy:
  - Up to MAX_RETRIES attempts with exponential back-off
  - On 429 (rate-limit): waits RETRY_SLEEP seconds before retry
  - On any other error: retries immediately up to MAX_RETRIES
  - If all retries are exhausted, falls back to rule-based insights
"""

from __future__ import annotations

import json
import logging
import re
import time

from app.models.result import Metrics
from app.models.transaction import RecurringItem

log = logging.getLogger(__name__)

_MAX_RETRIES = 3
_RETRY_SLEEP = 10.0   # seconds to wait after a 429


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def generate_insights(
    metrics: Metrics,
    category_summary: dict[str, float],
    recurring_summary: list[RecurringItem],
) -> tuple[list[str], str]:
    """
    Generate 5 financial insights via Groq LLM, with rule-based fallback.

    Returns:
        (insights, source)  where source is "llm", "rules", or "fallback"
    """
    from app.config import settings

    if settings.ai_enabled:
        try:
            insights = _llm_insights(metrics, category_summary, recurring_summary)
            return insights, "llm"
        except RuntimeError as exc:
            log.warning("LLM insights failed, falling back to rule-based: %s", exc)

    insights = _rule_based_insights(metrics, category_summary, recurring_summary)
    source = "rules" if settings.ai_enabled else "fallback"
    return insights, source


# ---------------------------------------------------------------------------
# LLM call with retry
# ---------------------------------------------------------------------------

def _llm_insights(
    metrics: Metrics,
    category_summary: dict[str, float],
    recurring_summary: list[RecurringItem],
) -> list[str]:
    from app.config import get_groq_client, settings

    client = get_groq_client()
    if client is None:
        raise RuntimeError(
            "Groq client is not initialised. "
            "Check that GROQ_API_KEY is set in your .env file."
        )

    # Build a compact, PII-free summary
    start, end = metrics.date_range
    summary = {
        "period": f"{start.strftime('%d %b %Y')} – {end.strftime('%d %b %Y')}",
        "income": round(metrics.total_income),
        "spend": round(metrics.total_spend),
        "savings": round(metrics.savings),
        "savings_pct": round(metrics.savings_rate, 1),
        "txn_count": metrics.transaction_count,
        "top_cats": {
            cat: round(amt)
            for cat, amt in list(category_summary.items())[:5]
        },
        "recurring": [
            {"name": r.merchant[:20], "amt": round(r.amount), "tag": r.tag}
            for r in recurring_summary[:3]
        ],
        "biggest_txn": (
            {
                "desc": (metrics.biggest_transactions[0].clean_description or "")[:30],
                "amt": round(abs(metrics.biggest_transactions[0].amount)),
            }
            if metrics.biggest_transactions else None
        ),
    }

    prompt = (
        "You are a personal finance advisor for Indian professionals. "
        "Analyse this bank statement summary and generate exactly 5 specific, "
        "actionable insights. Each insight must reference actual ₹ amounts from "
        "the data. Write 1-2 sentences per insight. "
        "Return ONLY a valid JSON array of exactly 5 strings — no markdown, "
        "no extra text, no explanation outside the array.\n\n"
        f"Statement data: {json.dumps(summary, ensure_ascii=False, separators=(',', ':'))}"
    )

    last_error: Exception | None = None

    for attempt in range(1, _MAX_RETRIES + 1):
        log.info("Groq insights call — attempt %d/%d", attempt, _MAX_RETRIES)
        try:
            response = client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=400,
            )
            raw = response.choices[0].message.content.strip()
            log.debug("Groq raw response: %s", raw[:300])

            insights = _parse_string_array(raw)

            if len(insights) >= 3:
                log.info("Groq returned %d insights (attempt %d)", len(insights), attempt)
                return insights[:5]

            # Got a response but too few items — log and retry
            log.warning(
                "Groq returned only %d insights on attempt %d — retrying",
                len(insights), attempt,
            )
            last_error = ValueError(f"Only {len(insights)} insights returned")

        except Exception as exc:
            last_error = exc
            err_str = str(exc).lower()

            if "429" in err_str or "rate" in err_str:
                log.warning(
                    "Groq rate-limited (attempt %d/%d) — sleeping %.0fs",
                    attempt, _MAX_RETRIES, _RETRY_SLEEP,
                )
                time.sleep(_RETRY_SLEEP)
            else:
                log.error(
                    "Groq insight call failed (attempt %d/%d): %s: %s",
                    attempt, _MAX_RETRIES, type(exc).__name__, exc,
                )

    raise RuntimeError(
        f"Groq insights call failed after {_MAX_RETRIES} attempts. "
        f"Last error: {last_error}"
    )


# ---------------------------------------------------------------------------
# Rule-based fallback insights
# ---------------------------------------------------------------------------

def _rule_based_insights(
    metrics: Metrics,
    category_summary: dict[str, float],
    recurring_summary: list[RecurringItem],
) -> list[str]:
    """Generate simple but useful insights from the metrics without LLM."""
    insights: list[str] = []

    # 1. Savings rate
    if metrics.savings_rate >= 20:
        insights.append(
            f"Great job! You saved ₹{metrics.savings:,.0f} ({metrics.savings_rate:.1f}% of income) "
            f"this period — well above the recommended 20% benchmark."
        )
    elif metrics.savings_rate > 0:
        insights.append(
            f"You saved ₹{metrics.savings:,.0f} ({metrics.savings_rate:.1f}% of income) this period. "
            f"Try to increase savings to at least 20% by trimming discretionary spend."
        )
    else:
        insights.append(
            f"Your spending (₹{abs(metrics.total_spend):,.0f}) exceeded income (₹{metrics.total_income:,.0f}) "
            f"this period. Review your largest expense categories to identify cuts."
        )

    # 2. Top spending category
    if category_summary:
        top_cat, top_amt = max(category_summary.items(), key=lambda x: x[1])
        pct = (top_amt / metrics.total_spend * 100) if metrics.total_spend else 0
        insights.append(
            f"Your biggest expense category is {top_cat} at ₹{top_amt:,.0f} "
            f"({pct:.1f}% of total spend). Consider setting a monthly budget for this category."
        )

    # 3. Recurring charges
    if recurring_summary:
        total_recurring = sum(r.amount for r in recurring_summary)
        insights.append(
            f"You have {len(recurring_summary)} recurring subscription(s) totalling "
            f"₹{total_recurring:,.0f}/month. Review them periodically for services you no longer use."
        )
    else:
        insights.append(
            "No recurring subscriptions were detected this period. "
            "Keep an eye out for auto-renewals that may appear next month."
        )

    # 4. Transaction volume
    insights.append(
        f"You made {metrics.transaction_count} transactions between "
        f"{metrics.date_range[0].strftime('%d %b')} and {metrics.date_range[1].strftime('%d %b %Y')}."
        f" That's roughly {metrics.transaction_count // max((metrics.date_range[1] - metrics.date_range[0]).days, 1) or 1} transactions per day."
    )

    # 5. Biggest single transaction
    if metrics.biggest_transactions:
        t = metrics.biggest_transactions[0]
        insights.append(
            f"Your largest single transaction was ₹{abs(t.amount):,.0f} "
            f"({t.clean_description or t.description}). Large one-off expenses can significantly "
            f"impact your monthly budget."
        )
    else:
        insights.append(
            "Tip: Export your transactions as CSV to track spending trends in a spreadsheet "
            "or budgeting app for a longer-term view."
        )

    return insights[:5]


def _parse_string_array(raw: str) -> list[str]:
    """Parse a JSON array of strings from LLM output, tolerating markdown fences."""
    cleaned = re.sub(r"```(?:json)?", "", raw).strip()
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start == -1 or end == -1:
        log.warning("LLM response missing JSON array brackets: %s", raw[:200])
        return []
    try:
        result = json.loads(cleaned[start: end + 1])
        return [str(s) for s in result if isinstance(s, str) and s.strip()]
    except json.JSONDecodeError as exc:
        log.warning("JSON parse failed: %s | raw: %s", exc, raw[:200])
        return []
