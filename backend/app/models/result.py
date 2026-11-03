# Phase 2 — AnalysisResult and Metrics Pydantic models
# Full implementation in Phase 2.

from __future__ import annotations
from datetime import date, datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field

from app.models.transaction import Transaction, RecurringItem, CategoryStat


class Metrics(BaseModel):
    total_income: float
    total_spend: float
    savings: float
    savings_rate: float                         # percentage (0–100)
    top_categories: list[CategoryStat]
    biggest_transactions: list[Transaction]     # top 5 by abs(amount)
    transaction_count: int
    date_range: tuple[date, date]
    credit_count: int = 0
    debit_count: int = 0
    opening_balance: Optional[float] = None
    closing_balance: Optional[float] = None
    is_reconciled: bool = True
    reconciliation_delta: float = 0.0
    avg_transaction_amount: float = 0.0
    avg_debit_amount: float = 0.0
    avg_credit_amount: float = 0.0
    largest_credit: Optional[Transaction] = None
    largest_debit: Optional[Transaction] = None
    top_payers: list[dict] = Field(default_factory=list)
    top_payees: list[dict] = Field(default_factory=list)
    daily_cash_flow: list[dict] = Field(default_factory=list)
    weekly_cash_flow: list[dict] = Field(default_factory=list)
    monthly_cash_flow: list[dict] = Field(default_factory=list)
    income_to_expense_ratio: float = 0.0
    income_categories: list[CategoryStat] = Field(default_factory=list)
    intelligence: dict = Field(default_factory=dict)


class AnalysisResult(BaseModel):
    session_id: str
    transactions: list[Transaction]
    metrics: Metrics
    insights: list[str]                         # 3–5 insight strings
    category_summary: dict[str, float]          # category → total spend
    recurring_summary: list[RecurringItem]
    ai_enabled: bool = False                    # whether LLM was used
    insights_source: str = "rules"              # "llm" | "rules" | "fallback"
    parse_warnings: list[str] = []              # non-fatal parse issues
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
