"""
Data Quality Analyzer — Universal data cleaning & quality scoring

Analyzes uploaded datasets for:
  - Duplicate rows
  - Missing values
  - Invalid values / data type mismatches
  - Inconsistent date formats
  - Suspicious outliers (flagged, NOT auto-removed)
  - Data quality score (0-100)

Preserves the original dataset and supports preview before cleaning.
"""

from __future__ import annotations

import re
import logging
from datetime import datetime
from typing import Any, Optional

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def analyze_data_quality(df: pd.DataFrame) -> dict:
    """
    Analyze a DataFrame for quality issues and return a comprehensive report.

    Returns dict with:
        quality_score    — overall score 0-100
        total_rows       — number of rows
        total_columns    — number of columns
        issues           — list of issue dicts
        column_stats     — per-column statistics
        duplicate_count  — number of duplicate rows
        missing_summary  — summary of missing values
        type_issues      — columns with mixed/wrong types
        outliers         — suspicious outlier rows (NOT auto-removed)
    """
    if df.empty:
        return {
            "quality_score": 0,
            "total_rows": 0,
            "total_columns": 0,
            "issues": [{"type": "error", "message": "Dataset is empty."}],
            "column_stats": [],
            "duplicate_count": 0,
            "missing_summary": {},
            "type_issues": [],
            "outliers": [],
        }

    issues: list[dict] = []
    total_rows = len(df)
    total_cols = len(df.columns)

    # ── Duplicates ────────────────────────────────────────────────────────
    duplicate_mask = df.duplicated(keep="first")
    duplicate_count = int(duplicate_mask.sum())
    if duplicate_count > 0:
        issues.append({
            "type": "duplicates",
            "severity": "warning",
            "message": f"{duplicate_count} duplicate row(s) detected.",
            "count": duplicate_count,
            "row_indices": [int(i) for i in duplicate_mask[duplicate_mask].index[:20]],
        })

    # ── Missing values ────────────────────────────────────────────────────
    missing_summary: dict[str, int] = {}
    for col in df.columns:
        missing = int(df[col].isna().sum() + (df[col].astype(str).str.strip() == "").sum())
        if missing > 0:
            missing_summary[col] = missing

    if missing_summary:
        total_missing = sum(missing_summary.values())
        issues.append({
            "type": "missing_values",
            "severity": "warning",
            "message": f"{total_missing} missing value(s) across {len(missing_summary)} column(s).",
            "columns": missing_summary,
        })

    # ── Type detection & issues ───────────────────────────────────────────
    type_issues: list[dict] = []
    column_stats: list[dict] = []

    for col in df.columns:
        series = df[col].dropna()
        if series.empty:
            column_stats.append({
                "column": col,
                "dtype": "empty",
                "unique_count": 0,
                "missing_count": int(df[col].isna().sum()),
                "sample_values": [],
            })
            continue

        inferred_type = _infer_column_type(series)
        unique_count = int(series.nunique())
        missing_count = int(df[col].isna().sum())

        stat = {
            "column": col,
            "dtype": inferred_type,
            "unique_count": unique_count,
            "missing_count": missing_count,
            "sample_values": [str(v) for v in series.head(3).tolist()],
        }

        # Add numeric stats
        if inferred_type == "numeric":
            numeric_series = pd.to_numeric(series, errors="coerce").dropna()
            if not numeric_series.empty:
                stat.update({
                    "mean": round(float(numeric_series.mean()), 2),
                    "median": round(float(numeric_series.median()), 2),
                    "std": round(float(numeric_series.std()), 2),
                    "min": round(float(numeric_series.min()), 2),
                    "max": round(float(numeric_series.max()), 2),
                })

        # Check for mixed types
        if inferred_type == "mixed":
            type_issues.append({
                "column": col,
                "message": f"Column '{col}' contains mixed data types.",
                "sample": [str(v) for v in series.head(5).tolist()],
            })

        column_stats.append(stat)

    if type_issues:
        issues.append({
            "type": "type_mismatch",
            "severity": "info",
            "message": f"{len(type_issues)} column(s) have mixed data types.",
            "columns": type_issues,
        })

    # ── Outlier detection (numeric columns) ───────────────────────────────
    outliers: list[dict] = []
    for col in df.columns:
        numeric_series = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(numeric_series) < 10:
            continue

        q1 = float(numeric_series.quantile(0.25))
        q3 = float(numeric_series.quantile(0.75))
        iqr = q3 - q1
        if iqr == 0:
            continue

        lower = q1 - 3.0 * iqr  # Using 3x IQR to be conservative
        upper = q3 + 3.0 * iqr
        outlier_mask = (numeric_series < lower) | (numeric_series > upper)
        outlier_indices = numeric_series[outlier_mask].index.tolist()

        if outlier_indices:
            outliers.append({
                "column": col,
                "count": len(outlier_indices),
                "range": {"lower_bound": round(lower, 2), "upper_bound": round(upper, 2)},
                "values": [round(float(numeric_series.loc[i]), 2) for i in outlier_indices[:10]],
                "note": "These values are statistically unusual but may be valid data points. Review before removing.",
            })

    if outliers:
        total_outlier_count = sum(o["count"] for o in outliers)
        issues.append({
            "type": "outliers",
            "severity": "info",
            "message": f"{total_outlier_count} potential outlier(s) detected across {len(outliers)} column(s). Review before removing.",
            "details": outliers,
        })

    # ── Date format inconsistency ─────────────────────────────────────────
    for col in df.columns:
        if _infer_column_type(df[col].dropna()) == "date":
            formats_found = _detect_date_formats(df[col].dropna())
            if len(formats_found) > 1:
                issues.append({
                    "type": "inconsistent_dates",
                    "severity": "warning",
                    "column": col,
                    "message": f"Column '{col}' has {len(formats_found)} different date format(s).",
                    "formats": list(formats_found),
                })

    # ── Quality score calculation ─────────────────────────────────────────
    quality_score = _calculate_quality_score(
        total_rows=total_rows,
        total_cols=total_cols,
        duplicate_count=duplicate_count,
        missing_summary=missing_summary,
        type_issues=type_issues,
        outliers=outliers,
    )

    return {
        "quality_score": quality_score,
        "total_rows": total_rows,
        "total_columns": total_cols,
        "issues": issues,
        "column_stats": column_stats,
        "duplicate_count": duplicate_count,
        "missing_summary": missing_summary,
        "type_issues": type_issues,
        "outliers": outliers,
    }


# ---------------------------------------------------------------------------
# Cleaning operations (preview & apply)
# ---------------------------------------------------------------------------

def preview_cleaning(df: pd.DataFrame, operations: list[dict]) -> dict:
    """
    Preview the effect of cleaning operations without modifying the original.

    Each operation is a dict with 'action' and optional params:
      - {"action": "remove_duplicates"}
      - {"action": "fill_missing", "column": "...", "strategy": "mean|median|mode|drop|value", "value": ...}
      - {"action": "remove_outliers", "column": "...", "method": "iqr"}
      - {"action": "standardize_dates", "column": "...", "target_format": "%Y-%m-%d"}
      - {"action": "fix_types", "column": "...", "target_type": "numeric|text|date"}
    """
    preview_df = df.copy()
    changes: list[dict] = []

    for op in operations:
        action = op.get("action", "")
        before_rows = len(preview_df)

        if action == "remove_duplicates":
            preview_df = preview_df.drop_duplicates()
            removed = before_rows - len(preview_df)
            changes.append({"action": action, "rows_removed": removed})

        elif action == "fill_missing":
            col = op.get("column", "")
            strategy = op.get("strategy", "drop")
            if col and col in preview_df.columns:
                count = int(preview_df[col].isna().sum())
                if strategy == "drop":
                    preview_df = preview_df.dropna(subset=[col])
                elif strategy == "mean":
                    preview_df[col] = pd.to_numeric(preview_df[col], errors="coerce")
                    preview_df[col] = preview_df[col].fillna(preview_df[col].mean())
                elif strategy == "median":
                    preview_df[col] = pd.to_numeric(preview_df[col], errors="coerce")
                    preview_df[col] = preview_df[col].fillna(preview_df[col].median())
                elif strategy == "mode":
                    mode_val = preview_df[col].mode()
                    if not mode_val.empty:
                        preview_df[col] = preview_df[col].fillna(mode_val.iloc[0])
                elif strategy == "value":
                    preview_df[col] = preview_df[col].fillna(op.get("value", ""))
                changes.append({"action": action, "column": col, "strategy": strategy, "affected": count})

        elif action == "remove_outliers":
            col = op.get("column", "")
            if col and col in preview_df.columns:
                numeric = pd.to_numeric(preview_df[col], errors="coerce")
                q1, q3 = numeric.quantile(0.25), numeric.quantile(0.75)
                iqr = q3 - q1
                mask = (numeric >= q1 - 1.5 * iqr) & (numeric <= q3 + 1.5 * iqr)
                preview_df = preview_df[mask | numeric.isna()]
                removed = before_rows - len(preview_df)
                changes.append({"action": action, "column": col, "rows_removed": removed})

        elif action == "standardize_dates":
            col = op.get("column", "")
            fmt = op.get("target_format", "%Y-%m-%d")
            if col and col in preview_df.columns:
                converted = pd.to_datetime(preview_df[col], errors="coerce", dayfirst=True)
                success = int(converted.notna().sum())
                preview_df[col] = converted.dt.strftime(fmt).fillna(preview_df[col])
                changes.append({"action": action, "column": col, "converted": success})

        elif action == "fix_types":
            col = op.get("column", "")
            target = op.get("target_type", "text")
            if col and col in preview_df.columns:
                if target == "numeric":
                    preview_df[col] = pd.to_numeric(preview_df[col], errors="coerce")
                elif target == "text":
                    preview_df[col] = preview_df[col].astype(str)
                changes.append({"action": action, "column": col, "target_type": target})

    return {
        "original_rows": len(df),
        "cleaned_rows": len(preview_df),
        "changes": changes,
        "preview_data": preview_df.head(20).to_dict(orient="records"),
    }


def apply_cleaning(df: pd.DataFrame, operations: list[dict]) -> pd.DataFrame:
    """Apply cleaning operations and return the cleaned DataFrame."""
    result = preview_cleaning(df, operations)
    # Re-run to get actual cleaned df
    cleaned = df.copy()
    for op in operations:
        action = op.get("action", "")
        if action == "remove_duplicates":
            cleaned = cleaned.drop_duplicates()
        elif action == "fill_missing":
            col = op.get("column", "")
            strategy = op.get("strategy", "drop")
            if col and col in cleaned.columns:
                if strategy == "drop":
                    cleaned = cleaned.dropna(subset=[col])
                elif strategy == "mean":
                    cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce")
                    cleaned[col] = cleaned[col].fillna(cleaned[col].mean())
                elif strategy == "median":
                    cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce")
                    cleaned[col] = cleaned[col].fillna(cleaned[col].median())
                elif strategy == "mode":
                    mode_val = cleaned[col].mode()
                    if not mode_val.empty:
                        cleaned[col] = cleaned[col].fillna(mode_val.iloc[0])
                elif strategy == "value":
                    cleaned[col] = cleaned[col].fillna(op.get("value", ""))
        elif action == "remove_outliers":
            col = op.get("column", "")
            if col and col in cleaned.columns:
                numeric = pd.to_numeric(cleaned[col], errors="coerce")
                q1, q3 = numeric.quantile(0.25), numeric.quantile(0.75)
                iqr = q3 - q1
                mask = (numeric >= q1 - 1.5 * iqr) & (numeric <= q3 + 1.5 * iqr)
                cleaned = cleaned[mask | numeric.isna()]
        elif action == "standardize_dates":
            col = op.get("column", "")
            fmt = op.get("target_format", "%Y-%m-%d")
            if col and col in cleaned.columns:
                converted = pd.to_datetime(cleaned[col], errors="coerce", dayfirst=True)
                cleaned[col] = converted.dt.strftime(fmt).fillna(cleaned[col])
        elif action == "fix_types":
            col = op.get("column", "")
            target = op.get("target_type", "text")
            if col and col in cleaned.columns:
                if target == "numeric":
                    cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce")
                elif target == "text":
                    cleaned[col] = cleaned[col].astype(str)
    return cleaned


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _infer_column_type(series: pd.Series) -> str:
    """Infer the predominant data type of a series."""
    if series.empty:
        return "empty"

    sample = series.astype(str).head(100)

    # Check numeric
    numeric = pd.to_numeric(sample, errors="coerce")
    numeric_ratio = numeric.notna().sum() / len(sample)
    if numeric_ratio > 0.8:
        return "numeric"

    # Check date
    date_count = 0
    for val in sample.head(20):
        if _is_date_string(str(val)):
            date_count += 1
    if date_count / min(len(sample), 20) > 0.6:
        return "date"

    # Check boolean
    bool_vals = {"true", "false", "yes", "no", "1", "0", "t", "f", "y", "n"}
    bool_ratio = sample.str.lower().str.strip().isin(bool_vals).sum() / len(sample)
    if bool_ratio > 0.8:
        return "boolean"

    # Check if mostly text
    return "text"


_DATE_PATTERNS = [
    re.compile(r"^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$"),
    re.compile(r"^\d{4}[/-]\d{1,2}[/-]\d{1,2}$"),
    re.compile(r"^\d{1,2}\s+\w{3,}\s+\d{4}$"),
    re.compile(r"^\w{3,}\s+\d{1,2},?\s+\d{4}$"),
]


def _is_date_string(s: str) -> bool:
    s = s.strip()
    for pat in _DATE_PATTERNS:
        if pat.match(s):
            return True
    return False


def _detect_date_formats(series: pd.Series) -> set[str]:
    """Detect which date formats are present in a series."""
    formats_found: set[str] = set()
    for val in series.head(50):
        s = str(val).strip()
        if re.match(r"^\d{1,2}/\d{1,2}/\d{4}$", s):
            formats_found.add("DD/MM/YYYY")
        elif re.match(r"^\d{4}-\d{2}-\d{2}$", s):
            formats_found.add("YYYY-MM-DD")
        elif re.match(r"^\d{1,2}-\d{1,2}-\d{4}$", s):
            formats_found.add("DD-MM-YYYY")
        elif re.match(r"^\d{1,2}\s+\w{3}\s+\d{4}$", s):
            formats_found.add("DD Mon YYYY")
        elif re.match(r"^\w{3}\s+\d{1,2},?\s+\d{4}$", s):
            formats_found.add("Mon DD, YYYY")
    return formats_found


def _calculate_quality_score(
    total_rows: int,
    total_cols: int,
    duplicate_count: int,
    missing_summary: dict,
    type_issues: list,
    outliers: list,
) -> int:
    """Calculate a data quality score from 0-100."""
    if total_rows == 0:
        return 0

    score = 100.0
    total_cells = total_rows * total_cols if total_cols > 0 else 1

    # Penalize duplicates (up to 20 points)
    dup_ratio = duplicate_count / total_rows
    score -= min(20, dup_ratio * 100)

    # Penalize missing values (up to 30 points)
    total_missing = sum(missing_summary.values())
    missing_ratio = total_missing / total_cells
    score -= min(30, missing_ratio * 100)

    # Penalize type issues (up to 15 points)
    if total_cols > 0:
        type_ratio = len(type_issues) / total_cols
        score -= min(15, type_ratio * 50)

    # Penalize outliers (up to 10 points) - lighter penalty
    total_outliers = sum(o["count"] for o in outliers)
    outlier_ratio = total_outliers / total_rows
    score -= min(10, outlier_ratio * 30)

    return max(0, min(100, round(score)))
