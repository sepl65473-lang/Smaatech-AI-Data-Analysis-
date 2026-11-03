# Phase 2 — Transaction and related Pydantic models
# Full implementation in Phase 2.

from __future__ import annotations
from datetime import date
from typing import Optional
from pydantic import BaseModel


class Transaction(BaseModel):
    id: str                             # UUID
    date: date
    description: str                    # Raw description from bank statement
    clean_description: str              # Normalized / human-readable description
    amount: float                       # Positive = credit, Negative = debit
    balance: Optional[float] = None
    category: str = "Other"             # Assigned spending category
    is_recurring: bool = False
    recurrence_tag: Optional[str] = None  # SUBSCRIPTION | EMI | RENT | SIP | INSURANCE
    merchant: Optional[str] = None      # Extracted merchant name
    reference_no: Optional[str] = None  # Extracted UTR / reference number
    counterparty: Optional[str] = None  # Normalized counterparty / beneficiary name
    payment_mode: Optional[str] = "OTHER" # NEFT, RTGS, IMPS, UPI, CHEQUE, IFT, ACH, CARD, OTHER
    confidence: str = "High"            # High | Medium | Review
    confidence_score: float = 0.95      # 0.0 - 1.0 confidence rating
    classification_source: str = "rules" # rules | user | llm
    classification_reason: Optional[str] = None # Detailed explanation of why classified


class RecurringItem(BaseModel):
    merchant: str
    amount: float
    tag: str          # SUBSCRIPTION | EMI | RENT | SIP | INSURANCE
    frequency: str    # "monthly" | "weekly" | "irregular"
    occurrences: int


class CategoryStat(BaseModel):
    category: str
    amount: float
    percentage: float
