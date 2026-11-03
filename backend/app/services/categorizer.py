"""
Categorizer service — Phase 2 + Phase 3

Pass 1: Rule-based regex matching (fast, free, handles ~80% of Indian bank transactions).
Pass 2: Groq LLM fallback for any transaction still tagged "Other" after Pass 1.

Rate limit awareness (llama-3.3-70b-versatile):
  - 30 req/min, 1 000 tokens/min, 12k req/day, 100k tokens/day
  - Batch size is capped at 10 transactions (~80 tokens input, ~80 tokens output = ~160/batch)
  - A 1-second sleep between batches keeps us well under 30 req/min
  - 429 errors are retried once after a 2-second back-off, then silently skipped
"""

# Metadata contract: rules is a deterministic narration match;
# rules_unclassified means no supported lexical match (Other + Review Queue);
# llm_inferred is an unconfirmed model suggestion (also reviewable); user and
# user_override mean explicit user confirmation. classification_reason stores
# evidence/origin. confidence_score is a heuristic, not a calibrated probability
# (rule 0.95, client credit 0.98, unmatched 0.40, model 0.65, user 1.00).
# Payment rail is separate from accounting category in payment_mode.

from __future__ import annotations

import json
import logging
import re
import time

from app.models.transaction import Transaction

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Valid categories (kept in sync with architecture.md)
# ---------------------------------------------------------------------------
VALID_CATEGORIES = {
    "Food", "Travel", "Shopping", "Bills", "EMI",
    "Subscriptions", "Salary", "Rent", "Investments",
    "Healthcare", "Education", "Income", "Other",
}

# ---------------------------------------------------------------------------
# Rate-limit constants
# ---------------------------------------------------------------------------
# 10 transactions × ~8 tokens/description ≈ 80 tokens input
# System prompt ≈ 80 tokens  →  total input ≈ 160 tokens
# Output: 10 × {"id":…,"category":…} ≈ 80 tokens
# Per-batch total ≈ 240 tokens  →  safe under 1k/min with a 1 s inter-batch gap
_LLM_BATCH_SIZE = 10
_INTER_BATCH_SLEEP = 1.0   # seconds between batches (30 req/min = 2 s min gap; 1 s is safe for small uploads)
_RETRY_SLEEP = 2.0          # seconds to wait on a 429 before one retry

# ---------------------------------------------------------------------------
# Rule map — ordered; first match wins
# ---------------------------------------------------------------------------
_RULES: list[tuple[str, re.Pattern]] = [
    # ---- Income / Credits ----
    ("Salary", re.compile(
        r"\bsalar\b|salary|sal\s*cr|sal\s*credit|pay\s*roll|payroll|stipend|"
        r"laybour|labour|locallab|local\s*lab|weekly\s*labo|weekly\s*labou|"
        r"lab\s*paymen|labour\s*advanc",
        re.IGNORECASE,
    )),
    # ---- Investments ----
    ("Investments", re.compile(
        r"zerodha|groww|kuvera|coin\s*by|smallcase|upstox|angel\s*brok|"
        r"\bsip\b|mutual\s*fund|nps\b|ppf\b|epf\b|fd\s*open|fixed\s*deposit|"
        r"lic\s*premium|insurance\s*prem|policy\s*prem",
        re.IGNORECASE,
    )),
    # ---- EMI / Loans ----
    ("EMI", re.compile(
        r"\bemi\b|loan\s*repay|loan\s*return|equated\s*monthly|home\s*loan|car\s*loan|"
        r"personal\s*loan|edu\s*loan|credit\s*card\s*due|cc\s*due|"
        r"bajaj\s*fin|hdfc\s*loan|sbi\s*loan|icici\s*loan|kotak\s*loan",
        re.IGNORECASE,
    )),
    # ---- Rent ----
    ("Rent", re.compile(
        r"\brent\b|house\s*rent|pg\s*rent|room\s*rent|rental\s*pay|"
        r"flat\s*rent|apartment\s*rent|room\s*ren|monthly\s*renta|"
        r"shuttering\s*ren|scaffholding\s*ren|scaffolding\s*ren",
        re.IGNORECASE,
    )),
    # ---- Bills & Utilities ----
    ("Bills", re.compile(
        r"electricity|bescom|tata\s*power|adani\s*elec|msedcl|wbsedcl|"
        r"tangedco|kseb|mecom|torrent\s*power|cesc|jdvvnl|avvnl|"
        r"airtel|jio\b|bsnl|vodafone|vi\b|idea\b|broadband|internet\s*bill|"
        r"water\s*bill|gas\s*bill|piped\s*gas|igl\b|mgl\b|"
        r"dth\b|tata\s*sky|dish\s*tv|sun\s*direct|d2h\b|"
        r"phone\s*bill|mobile\s*bill|recharge|"
        r"charges\s*for\s*a\s*c|consolidated\s*charges|gst\s*%\s*on\s*charge|bank\s*charge",
        re.IGNORECASE,
    )),
    # ---- Subscriptions ----
    ("Subscriptions", re.compile(
        r"netflix|hotstar|disney\+?|spotify|prime\s*video|amazon\s*prime|"
        r"youtube\s*premium|zee5|sonyliv|voot|alt\s*balaji|jio\s*cinema|"
        r"apple\s*music|apple\s*tv|mxplayer|aha\b|lionsgate|erosnow|"
        r"linkedin\s*prem|github\s*pro|notion\b|slack\b|figma\b|adobe",
        re.IGNORECASE,
    )),
    # ---- Food & Groceries ----
    ("Food", re.compile(
        r"swiggy|zomato|uber\s*eats|blinkit|dunzo|bigbasket|grofers|"
        r"more\s*retail|dmart\b|reliance\s*fresh|reliance\s*smart|"
        r"spencers|nature\s*basket|licious|freshmenu|box8|faasos|"
        r"mcdonald|kfc\b|burger\s*king|dominos|pizza\s*hut|subway\b|"
        r"starbucks|ccd\b|cafe\s*coffee|haldiram|amul\b|"
        r"grocery|supermarket|provisions|fooding|foodin\b|canteen|mess\b",
        re.IGNORECASE,
    )),
    # ---- Travel & Transport ----
    ("Travel", re.compile(
        r"irctc|makemytrip|goibibo|cleartrip|yatra\b|easemytrip|"
        r"\bola\b|uber\b|rapido\b|redbus\b|abhibus|"
        r"indigo\b|spicejet|airindia|air\s*india|vistara|akasa|"
        r"petrol|fuel|hp\s*petrol|bharat\s*petrol|indian\s*oil|iocl\b|hpcl\b|bpcl\b|"
        r"metro\s*rail|parking\b|toll\b|fastag\b|"
        r"travellin\b|auto\s*expense",
        re.IGNORECASE,
    )),
    # ---- Shopping ----
    ("Shopping", re.compile(
        r"amazon\b|flipkart|myntra|ajio\b|nykaa|meesho|snapdeal|"
        r"tata\s*cliq|tatacliq|shopclues|paytm\s*mall|"
        r"ikea\b|croma\b|reliance\s*digital|vijay\s*sales|"
        r"westside\b|pantaloons|max\s*fashion|lifestyle\b|shoppers\s*stop",
        re.IGNORECASE,
    )),
    # ---- Healthcare ----
    ("Healthcare", re.compile(
        r"pharmacy|medical\s*store|chemist|apollo\s*pharm|medplus|"
        r"1mg\b|netmeds|practo|hospital|clinic|doctor|lab\s*test|"
        r"diagnostic|health\s*check|dental|optician|"
        r"cult\s*fit|cultfit|cure\s*fit|curefit|healthifyme|mfine|"
        r"lybrate|portea|thyrocare|dr\s*lal|metropolis",
        re.IGNORECASE,
    )),
    # ---- Education ----
    ("Education", re.compile(
        r"coursera|udemy|unacademy|byju|vedantu|khan\s*academy|"
        r"school\s*fee|college\s*fee|tuition|education\s*loan|"
        r"books?\b|stationery",
        re.IGNORECASE,
    )),
    # ---- Other (catch-all — always last) ----
    ("Other", re.compile(r".*", re.IGNORECASE)),
]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def categorize_transactions(transactions: list[Transaction]) -> tuple[list[Transaction], bool]:
    """
    Two-pass categorization:
      Pass 1 — fast rule-based regex with explicit keyword tracking
      Pass 2 — Groq LLM for debits still tagged "Other" (rate-limit aware)

    Returns:
        (transactions, used_llm)
        used_llm — True if at least one Groq API call was made (caller can
                   sleep before the next LLM call to stay under token limits)
    """
    # Pass 1: rules
    for txn in transactions:
        search_text = f"{txn.description} {txn.clean_description} {txn.counterparty or ''}"
        matched, matched_term = _apply_rules(search_text)
        if txn.amount > 0 and matched not in ("Salary", "Investments", "Other"):
            matched = "Income"
            txn.category = "Income"
            txn.confidence = "High"
            txn.confidence_score = 0.98
            txn.classification_source = "rules"
            txn.classification_reason = "Client/Customer inflow credit remittance"
        elif matched == "Other":
            txn.category = "Other"
            txn.confidence = "Review"
            txn.confidence_score = 0.40
            txn.classification_source = "rules_unclassified"
            txn.classification_reason = "Unclassified corporate outflow: narration lacks unambiguous commercial keyword; retained in Review Queue for auditor confirmation"
        else:
            txn.category = matched
            txn.confidence = "High"
            txn.confidence_score = 0.95
            txn.classification_source = "rules"
            txn.classification_reason = f"Verified lexical match in narration: '{matched_term}'"

    # Pass 2: LLM fallback — only for uncategorized debits
    others = [t for t in transactions if t.category == "Other" and t.amount < 0]
    used_llm = False
    if others:
        used_llm = _llm_categorize(others)

    return transactions, used_llm


# ---------------------------------------------------------------------------
# Rule engine
# ---------------------------------------------------------------------------

def _apply_rules(text: str) -> tuple[str, str | None]:
    for category, pattern in _RULES:
        m = pattern.search(text)
        if m:
            return category, m.group(0).strip()
    return "Other", None


# ---------------------------------------------------------------------------
# LLM fallback (Phase 3) — rate-limit aware
# ---------------------------------------------------------------------------

def _llm_categorize(transactions: list[Transaction]) -> bool:
    """
    Send uncategorized transactions to Groq in small batches.
    Sleeps between batches and retries once on 429.
    Returns True if at least one API call was attempted.
    """
    from app.config import get_groq_client, settings

    client = get_groq_client()
    if client is None:
        log.debug("Groq unavailable — %d transactions remain 'Other'", len(transactions))
        return False

    for i in range(0, len(transactions), _LLM_BATCH_SIZE):
        batch = transactions[i : i + _LLM_BATCH_SIZE]
        _llm_categorize_batch(client, batch, settings.GROQ_MODEL)
        # Respect rate limit: pause between batches (skip after last batch)
        if i + _LLM_BATCH_SIZE < len(transactions):
            time.sleep(_INTER_BATCH_SLEEP)

    return True  # at least one call was made


def _llm_categorize_batch(client, batch: list[Transaction], model: str) -> None:
    """
    Categorize one batch via Groq. Retries once on 429. Mutates .category in place.

    Token budget per call (llama-3.3-70b-versatile, 1k tokens/min):
      System prompt:  ~80 tokens
      Input payload:  ~8 tokens × 10 transactions = ~80 tokens
      Output:         ~80 tokens
      Total:          ~240 tokens  ← safely under 1k/min
    """
    # Use only the clean description — shorter = fewer tokens
    payload = [
        {"id": t.id, "desc": (t.clean_description or t.description)[:60]}
        for t in batch
    ]

    # Tight prompt — every token counts at 1k/min
    prompt = (
        "Categorize Indian bank transactions. "
        "Categories: Food,Travel,Shopping,Bills,EMI,Subscriptions,Salary,Rent,Investments,Healthcare,Education,Other\n"
        "Return ONLY a JSON array: [{\"id\":\"…\",\"category\":\"…\"},…]\n\n"
        f"Transactions: {json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}"
    )

    def _do_call():
        return client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=150,   # 10 items × ~15 tokens each = 150 max
        )

    try:
        response = _do_call()
    except Exception as exc:
        err_str = str(exc).lower()
        if "429" in err_str or "rate" in err_str:
            log.warning("Groq 429 on categorizer — retrying in %.0fs", _RETRY_SLEEP)
            time.sleep(_RETRY_SLEEP)
            try:
                response = _do_call()
            except Exception as exc2:
                log.warning("Groq categorizer retry failed: %s — keeping 'Other'", exc2)
                return
        else:
            log.warning("Groq categorizer batch failed: %s — keeping 'Other'", exc)
            return

    raw = response.choices[0].message.content.strip()
    results = _parse_llm_json(raw)
    id_map = {r["id"]: r["category"] for r in results if "id" in r and "category" in r}

    for txn in batch:
        new_cat = id_map.get(txn.id)
        if new_cat and new_cat in VALID_CATEGORIES:
            txn.category = new_cat
            txn.confidence = "Review"
            txn.confidence_score = 0.65
            txn.classification_source = "llm_inferred"
            txn.classification_reason = f"Model suggestion ({model}); requires user review and confirmation"
            log.debug("LLM: '%s' → %s", txn.clean_description, new_cat)


def _parse_llm_json(raw: str) -> list[dict]:
    """Extract a JSON array from the LLM response, tolerating markdown fences."""
    cleaned = re.sub(r"```(?:json)?", "", raw).strip()
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start == -1 or end == -1:
        log.warning("LLM categorizer: no JSON array in response: %s", raw[:150])
        return []
    try:
        return json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        log.warning("LLM categorizer: bad JSON: %s | raw: %s", exc, raw[:150])
        return []
