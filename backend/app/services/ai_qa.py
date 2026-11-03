"""
AI Q&A Module — Natural language questions about uploaded data

Allows users to ask questions about their data and get evidence-based answers.
Uses Groq LLM with a data summary (never sends raw data to the LLM).
Falls back to statistical analysis when LLM is unavailable.
"""

from __future__ import annotations

import json
import logging
import time

import pandas as pd
import numpy as np

log = logging.getLogger(__name__)


def answer_question(
    question: str,
    df: pd.DataFrame,
    analysis_result: dict,
) -> dict:
    """
    Answer a natural-language question about the uploaded data.

    Args:
        question: User's question in natural language
        df: The uploaded DataFrame
        analysis_result: The analysis result dict (metrics, charts, etc.)

    Returns:
        dict with 'answer', 'evidence', 'chart_suggestion'
    """
    question_lower = question.lower().strip()

    # Try deterministic answer first
    deterministic = _try_deterministic_answer(question_lower, df, analysis_result)
    if deterministic:
        return deterministic

    # Try LLM answer
    llm_answer = _try_llm_answer(question, df, analysis_result)
    if llm_answer:
        return llm_answer

    # Fallback: statistical summary
    return _statistical_fallback(question_lower, df)


# ---------------------------------------------------------------------------
# Deterministic answers for common questions
# ---------------------------------------------------------------------------

def _try_deterministic_answer(question: str, df: pd.DataFrame, result: dict) -> dict | None:
    """Answer common questions deterministically using actual calculations."""

    # Total/sum questions
    if any(kw in question for kw in ["total", "sum", "how much"]):
        for col in df.columns:
            if col.lower() in question or col.lower().replace("_", " ") in question:
                numeric = pd.to_numeric(df[col], errors="coerce").dropna()
                if not numeric.empty:
                    total = round(float(numeric.sum()), 2)
                    return {
                        "answer": f"The total {col} is {total:,.2f}.",
                        "evidence": {
                            "column": col,
                            "calculation": "SUM",
                            "value": total,
                            "count": int(len(numeric)),
                        },
                        "chart_suggestion": None,
                    }

    # Average questions
    if any(kw in question for kw in ["average", "avg", "mean"]):
        for col in df.columns:
            if col.lower() in question or col.lower().replace("_", " ") in question:
                numeric = pd.to_numeric(df[col], errors="coerce").dropna()
                if not numeric.empty:
                    avg = round(float(numeric.mean()), 2)
                    return {
                        "answer": f"The average {col} is {avg:,.2f}.",
                        "evidence": {
                            "column": col,
                            "calculation": "MEAN",
                            "value": avg,
                            "count": int(len(numeric)),
                        },
                        "chart_suggestion": None,
                    }

    # Count questions
    if any(kw in question for kw in ["how many", "count", "number of"]):
        if "row" in question or "record" in question or "total" in question:
            return {
                "answer": f"There are {len(df)} rows in the dataset.",
                "evidence": {"calculation": "COUNT", "value": len(df)},
                "chart_suggestion": None,
            }
        for col in df.columns:
            if col.lower() in question or col.lower().replace("_", " ") in question:
                unique = int(df[col].nunique())
                return {
                    "answer": f"There are {unique} unique values in {col}.",
                    "evidence": {"column": col, "calculation": "DISTINCT COUNT", "value": unique},
                    "chart_suggestion": None,
                }

    # Max/min questions
    if any(kw in question for kw in ["highest", "maximum", "max", "largest", "biggest", "top"]):
        for col in df.columns:
            if col.lower() in question or col.lower().replace("_", " ") in question:
                numeric = pd.to_numeric(df[col], errors="coerce").dropna()
                if not numeric.empty:
                    max_val = round(float(numeric.max()), 2)
                    max_idx = numeric.idxmax()
                    row_info = df.loc[max_idx].to_dict() if max_idx in df.index else {}
                    return {
                        "answer": f"The maximum {col} is {max_val:,.2f}.",
                        "evidence": {
                            "column": col,
                            "calculation": "MAX",
                            "value": max_val,
                            "row": {k: str(v) for k, v in list(row_info.items())[:5]},
                        },
                        "chart_suggestion": "bar",
                    }

    if any(kw in question for kw in ["lowest", "minimum", "min", "smallest"]):
        for col in df.columns:
            if col.lower() in question or col.lower().replace("_", " ") in question:
                numeric = pd.to_numeric(df[col], errors="coerce").dropna()
                if not numeric.empty:
                    min_val = round(float(numeric.min()), 2)
                    return {
                        "answer": f"The minimum {col} is {min_val:,.2f}.",
                        "evidence": {"column": col, "calculation": "MIN", "value": min_val},
                        "chart_suggestion": None,
                    }

    # Column listing
    if any(kw in question for kw in ["columns", "fields", "what data", "what columns"]):
        cols = list(df.columns)
        return {
            "answer": f"The dataset has {len(cols)} columns: {', '.join(cols)}.",
            "evidence": {"columns": cols},
            "chart_suggestion": None,
        }

    return None


# ---------------------------------------------------------------------------
# LLM-powered answer
# ---------------------------------------------------------------------------

def _try_llm_answer(question: str, df: pd.DataFrame, result: dict) -> dict | None:
    """Use Groq LLM to answer the question with a data summary context."""
    from app.config import get_groq_client, settings

    client = get_groq_client()
    if client is None:
        return None

    # Build compact summary (never send raw data)
    summary = _build_data_summary(df, result)

    prompt = (
        "You are a data analyst assistant. A user has uploaded a dataset and is asking a question about it. "
        "Answer based ONLY on the data summary provided. "
        "If the answer cannot be determined from the summary, say so. "
        "Never invent data. Be specific with numbers.\n\n"
        f"Data summary:\n{json.dumps(summary, ensure_ascii=False, default=str)}\n\n"
        f"Question: {question}\n\n"
        "Respond with a JSON object: {\"answer\": \"...\", \"chart_suggestion\": \"bar|line|pie|null\"}"
    )

    try:
        response = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=300,
        )
        raw = response.choices[0].message.content.strip()
        # Parse JSON response
        import re
        cleaned = re.sub(r"```(?:json)?", "", raw).strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end >= 0:
            parsed = json.loads(cleaned[start:end + 1])
            return {
                "answer": parsed.get("answer", raw),
                "evidence": {"source": "ai", "model": settings.GROQ_MODEL},
                "chart_suggestion": parsed.get("chart_suggestion"),
            }
        return {
            "answer": raw,
            "evidence": {"source": "ai", "model": settings.GROQ_MODEL},
            "chart_suggestion": None,
        }
    except Exception as exc:
        log.warning("LLM Q&A failed: %s", exc)
        return None


def _build_data_summary(df: pd.DataFrame, result: dict) -> dict:
    """Build a compact, PII-free summary for the LLM."""
    summary = {
        "rows": len(df),
        "columns": list(df.columns),
        "column_types": {},
        "numeric_stats": {},
        "categorical_top_values": {},
    }

    for col in df.columns:
        series = df[col].dropna()
        numeric = pd.to_numeric(series, errors="coerce")
        if numeric.notna().sum() / max(len(series), 1) > 0.7:
            numeric = numeric.dropna()
            summary["column_types"][col] = "numeric"
            summary["numeric_stats"][col] = {
                "mean": round(float(numeric.mean()), 2),
                "median": round(float(numeric.median()), 2),
                "min": round(float(numeric.min()), 2),
                "max": round(float(numeric.max()), 2),
                "sum": round(float(numeric.sum()), 2),
            }
        else:
            summary["column_types"][col] = "text"
            top = series.value_counts().head(5)
            summary["categorical_top_values"][col] = {
                str(k): int(v) for k, v in top.items()
            }

    # Include KPIs from analysis
    if "kpis" in result:
        summary["kpis"] = result["kpis"]

    return summary


# ---------------------------------------------------------------------------
# Statistical fallback
# ---------------------------------------------------------------------------

def _statistical_fallback(question: str, df: pd.DataFrame) -> dict:
    """Provide a statistical summary as a fallback answer."""
    stats = []
    for col in df.columns:
        numeric = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(numeric) > 0:
            stats.append(
                f"{col}: count={len(numeric)}, mean={numeric.mean():.2f}, "
                f"min={numeric.min():.2f}, max={numeric.max():.2f}"
            )

    if stats:
        answer = (
            "I couldn't find a specific answer, but here's a statistical summary:\n"
            + "\n".join(stats[:5])
        )
    else:
        answer = "I couldn't determine an answer from the available data. Try asking about specific columns or values."

    return {
        "answer": answer,
        "evidence": {"source": "statistical_fallback"},
        "chart_suggestion": None,
    }
