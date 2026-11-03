"""
Business Analytics Engine — Universal analysis for any dataset

Supports:
  - Sales analytics: revenue, profit, orders, customer & product analysis
  - HR analytics: headcount, attendance, leave, workforce reports
  - Inventory analytics: stock levels, valuation, movements, reorder alerts
  - General analytics: configurable metrics for any business dataset

Auto-detects the dataset type based on column names and content.
"""

from __future__ import annotations

import re
import logging
from collections import defaultdict
from typing import Any, Optional

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dataset type detection
# ---------------------------------------------------------------------------

_SALES_INDICATORS = {
    "revenue", "sales", "order", "orders", "product", "price", "quantity",
    "total", "profit", "discount", "customer", "item", "sku", "unit_price",
    "amount", "cost", "margin", "invoice",
}

_HR_INDICATORS = {
    "employee", "emp", "department", "dept", "salary", "designation", "joining",
    "attendance", "leave", "headcount", "age", "gender", "position", "hire",
    "manager", "performance", "rating", "staff",
}

_INVENTORY_INDICATORS = {
    "stock", "inventory", "warehouse", "sku", "reorder", "quantity",
    "unit_cost", "valuation", "supplier", "bin", "location", "movement",
    "inbound", "outbound", "on_hand", "available",
}


def detect_dataset_type(df: pd.DataFrame) -> str:
    """
    Detect dataset type based on column names.
    Returns: 'financial' | 'sales' | 'hr' | 'inventory' | 'general'
    """
    cols_lower = {c.lower().replace("_", " ").replace("-", " ").strip() for c in df.columns}
    col_text = " ".join(cols_lower)

    # Check for bank statement indicators (existing financial pipeline)
    financial_keywords = {"narration", "debit", "credit", "balance", "txn", "transaction"}
    if len(cols_lower & financial_keywords) >= 2:
        return "financial"

    # Score each type
    scores = {
        "sales": sum(1 for kw in _SALES_INDICATORS if kw in col_text),
        "hr": sum(1 for kw in _HR_INDICATORS if kw in col_text),
        "inventory": sum(1 for kw in _INVENTORY_INDICATORS if kw in col_text),
    }

    best = max(scores, key=scores.get)
    if scores[best] >= 2:
        return best
    return "general"


# ---------------------------------------------------------------------------
# Sales Analytics
# ---------------------------------------------------------------------------

def analyze_sales(df: pd.DataFrame) -> dict:
    """Analyze a sales dataset and return comprehensive metrics."""
    result = {
        "type": "sales",
        "kpis": {},
        "charts": [],
        "tables": [],
        "insights": [],
    }

    # Find relevant columns (fuzzy match)
    cols = {c.lower().strip(): c for c in df.columns}
    revenue_col = _find_col_fuzzy(cols, ["revenue", "sales", "total", "amount", "price", "order_total"])
    qty_col = _find_col_fuzzy(cols, ["quantity", "qty", "units", "count", "items"])
    product_col = _find_col_fuzzy(cols, ["product", "item", "sku", "product_name", "item_name"])
    customer_col = _find_col_fuzzy(cols, ["customer", "client", "buyer", "customer_name"])
    date_col = _find_col_fuzzy(cols, ["date", "order_date", "transaction_date", "sale_date"])
    profit_col = _find_col_fuzzy(cols, ["profit", "margin", "net"])
    cost_col = _find_col_fuzzy(cols, ["cost", "cogs", "unit_cost", "expense"])
    category_col = _find_col_fuzzy(cols, ["category", "product_category", "type", "segment"])
    region_col = _find_col_fuzzy(cols, ["region", "city", "state", "country", "location", "area"])

    # ── KPIs ──────────────────────────────────────────────────────────────
    if revenue_col:
        rev_series = pd.to_numeric(df[revenue_col], errors="coerce").dropna()
        if not rev_series.empty:
            result["kpis"]["total_revenue"] = round(float(rev_series.sum()), 2)
            result["kpis"]["avg_order_value"] = round(float(rev_series.mean()), 2)
            result["kpis"]["min_order"] = round(float(rev_series.min()), 2)
            result["kpis"]["max_order"] = round(float(rev_series.max()), 2)

    result["kpis"]["total_orders"] = len(df)

    if qty_col:
        qty_series = pd.to_numeric(df[qty_col], errors="coerce").dropna()
        if not qty_series.empty:
            result["kpis"]["total_units_sold"] = int(qty_series.sum())

    if customer_col:
        result["kpis"]["unique_customers"] = int(df[customer_col].nunique())

    if product_col:
        result["kpis"]["unique_products"] = int(df[product_col].nunique())

    if profit_col:
        prof_series = pd.to_numeric(df[profit_col], errors="coerce").dropna()
        if not prof_series.empty:
            result["kpis"]["total_profit"] = round(float(prof_series.sum()), 2)
            result["kpis"]["profit_margin"] = round(
                float(prof_series.sum()) / max(result["kpis"].get("total_revenue", 1), 1) * 100, 1
            )

    # ── Charts data ───────────────────────────────────────────────────────
    # Revenue by product
    if product_col and revenue_col:
        product_rev = df.groupby(product_col)[revenue_col].apply(
            lambda x: pd.to_numeric(x, errors="coerce").sum()
        ).sort_values(ascending=False).head(10)
        result["charts"].append({
            "title": "Top Products by Revenue",
            "type": "bar",
            "data": [{"name": str(k), "value": round(float(v), 2)} for k, v in product_rev.items()],
        })

    # Revenue by category
    if category_col and revenue_col:
        cat_rev = df.groupby(category_col)[revenue_col].apply(
            lambda x: pd.to_numeric(x, errors="coerce").sum()
        ).sort_values(ascending=False)
        result["charts"].append({
            "title": "Revenue by Category",
            "type": "pie",
            "data": [{"name": str(k), "value": round(float(v), 2)} for k, v in cat_rev.items()],
        })

    # Revenue by region
    if region_col and revenue_col:
        reg_rev = df.groupby(region_col)[revenue_col].apply(
            lambda x: pd.to_numeric(x, errors="coerce").sum()
        ).sort_values(ascending=False).head(10)
        result["charts"].append({
            "title": "Revenue by Region",
            "type": "bar",
            "data": [{"name": str(k), "value": round(float(v), 2)} for k, v in reg_rev.items()],
        })

    # Monthly trend
    if date_col and revenue_col:
        date_series = pd.to_datetime(df[date_col], errors="coerce")
        rev_series = pd.to_numeric(df[revenue_col], errors="coerce")
        temp_df = pd.DataFrame({"date": date_series, "revenue": rev_series}).dropna()
        if not temp_df.empty:
            monthly = temp_df.set_index("date").resample("ME")["revenue"].sum()
            result["charts"].append({
                "title": "Monthly Revenue Trend",
                "type": "line",
                "data": [{"name": str(k.strftime("%b %Y")), "value": round(float(v), 2)} for k, v in monthly.items()],
            })

    # Top customers
    if customer_col and revenue_col:
        cust_rev = df.groupby(customer_col)[revenue_col].apply(
            lambda x: pd.to_numeric(x, errors="coerce").sum()
        ).sort_values(ascending=False).head(10)
        result["tables"].append({
            "title": "Top Customers",
            "columns": ["Customer", "Revenue"],
            "rows": [[str(k), round(float(v), 2)] for k, v in cust_rev.items()],
        })

    # ── Insights ──────────────────────────────────────────────────────────
    if result["kpis"].get("total_revenue"):
        result["insights"].append(
            f"Total revenue is {_format_number(result['kpis']['total_revenue'])} "
            f"across {result['kpis']['total_orders']} orders."
        )
    if result["kpis"].get("avg_order_value"):
        result["insights"].append(
            f"Average order value is {_format_number(result['kpis']['avg_order_value'])}."
        )
    if result["kpis"].get("total_profit") is not None:
        result["insights"].append(
            f"Total profit is {_format_number(result['kpis']['total_profit'])} "
            f"with a {result['kpis'].get('profit_margin', 0):.1f}% margin."
        )

    return result


# ---------------------------------------------------------------------------
# HR Analytics
# ---------------------------------------------------------------------------

def analyze_hr(df: pd.DataFrame) -> dict:
    """Analyze an HR dataset."""
    result = {
        "type": "hr",
        "kpis": {},
        "charts": [],
        "tables": [],
        "insights": [],
    }

    cols = {c.lower().strip(): c for c in df.columns}
    dept_col = _find_col_fuzzy(cols, ["department", "dept", "division", "team"])
    salary_col = _find_col_fuzzy(cols, ["salary", "pay", "compensation", "ctc", "wage"])
    emp_col = _find_col_fuzzy(cols, ["employee", "emp", "name", "employee_name", "emp_name", "staff"])
    gender_col = _find_col_fuzzy(cols, ["gender", "sex"])
    age_col = _find_col_fuzzy(cols, ["age", "years"])
    join_col = _find_col_fuzzy(cols, ["joining", "hire", "start_date", "date_of_joining", "join_date"])
    designation_col = _find_col_fuzzy(cols, ["designation", "position", "title", "role", "job_title"])
    rating_col = _find_col_fuzzy(cols, ["rating", "performance", "score", "review"])
    leave_col = _find_col_fuzzy(cols, ["leave", "leaves", "days_off", "absent"])
    attendance_col = _find_col_fuzzy(cols, ["attendance", "present", "working_days"])

    # ── KPIs ──────────────────────────────────────────────────────────────
    result["kpis"]["total_employees"] = len(df)

    if dept_col:
        result["kpis"]["departments"] = int(df[dept_col].nunique())

    if salary_col:
        sal = pd.to_numeric(df[salary_col], errors="coerce").dropna()
        if not sal.empty:
            result["kpis"]["avg_salary"] = round(float(sal.mean()), 2)
            result["kpis"]["median_salary"] = round(float(sal.median()), 2)
            result["kpis"]["total_payroll"] = round(float(sal.sum()), 2)
            result["kpis"]["min_salary"] = round(float(sal.min()), 2)
            result["kpis"]["max_salary"] = round(float(sal.max()), 2)

    # ── Charts ────────────────────────────────────────────────────────────
    if dept_col:
        dept_counts = df[dept_col].value_counts().head(15)
        result["charts"].append({
            "title": "Headcount by Department",
            "type": "bar",
            "data": [{"name": str(k), "value": int(v)} for k, v in dept_counts.items()],
        })

    if dept_col and salary_col:
        dept_sal = df.groupby(dept_col)[salary_col].apply(
            lambda x: pd.to_numeric(x, errors="coerce").mean()
        ).sort_values(ascending=False)
        result["charts"].append({
            "title": "Avg Salary by Department",
            "type": "bar",
            "data": [{"name": str(k), "value": round(float(v), 2)} for k, v in dept_sal.items()],
        })

    if gender_col:
        gender_counts = df[gender_col].value_counts()
        result["charts"].append({
            "title": "Gender Distribution",
            "type": "pie",
            "data": [{"name": str(k), "value": int(v)} for k, v in gender_counts.items()],
        })

    if age_col:
        ages = pd.to_numeric(df[age_col], errors="coerce").dropna()
        if not ages.empty:
            bins = [0, 25, 30, 35, 40, 45, 50, 55, 60, 100]
            labels = ["<25", "25-30", "30-35", "35-40", "40-45", "45-50", "50-55", "55-60", "60+"]
            age_dist = pd.cut(ages, bins=bins, labels=labels).value_counts().sort_index()
            result["charts"].append({
                "title": "Age Distribution",
                "type": "bar",
                "data": [{"name": str(k), "value": int(v)} for k, v in age_dist.items() if v > 0],
            })

    # ── Insights ──────────────────────────────────────────────────────────
    result["insights"].append(
        f"Workforce consists of {result['kpis']['total_employees']} employees"
        + (f" across {result['kpis'].get('departments', 'N/A')} departments." if dept_col else ".")
    )
    if result["kpis"].get("avg_salary"):
        result["insights"].append(
            f"Average salary is {_format_number(result['kpis']['avg_salary'])} "
            f"(median: {_format_number(result['kpis']['median_salary'])})."
        )

    return result


# ---------------------------------------------------------------------------
# Inventory Analytics
# ---------------------------------------------------------------------------

def analyze_inventory(df: pd.DataFrame) -> dict:
    """Analyze an inventory dataset."""
    result = {
        "type": "inventory",
        "kpis": {},
        "charts": [],
        "tables": [],
        "insights": [],
        "alerts": [],
    }

    cols = {c.lower().strip(): c for c in df.columns}
    product_col = _find_col_fuzzy(cols, ["product", "item", "sku", "name", "product_name", "item_name"])
    qty_col = _find_col_fuzzy(cols, ["quantity", "qty", "stock", "on_hand", "available", "units"])
    price_col = _find_col_fuzzy(cols, ["price", "unit_price", "unit_cost", "cost", "rate"])
    category_col = _find_col_fuzzy(cols, ["category", "type", "group", "product_category"])
    warehouse_col = _find_col_fuzzy(cols, ["warehouse", "location", "store", "bin"])
    reorder_col = _find_col_fuzzy(cols, ["reorder", "reorder_level", "reorder_point", "min_stock", "safety_stock"])
    supplier_col = _find_col_fuzzy(cols, ["supplier", "vendor", "manufacturer"])

    # ── KPIs ──────────────────────────────────────────────────────────────
    if product_col:
        result["kpis"]["total_products"] = int(df[product_col].nunique())
    else:
        result["kpis"]["total_products"] = len(df)

    if qty_col:
        qty = pd.to_numeric(df[qty_col], errors="coerce").dropna()
        if not qty.empty:
            result["kpis"]["total_stock_units"] = int(qty.sum())
            result["kpis"]["avg_stock_level"] = round(float(qty.mean()), 1)

    if qty_col and price_col:
        qty_s = pd.to_numeric(df[qty_col], errors="coerce")
        price_s = pd.to_numeric(df[price_col], errors="coerce")
        valuation = (qty_s * price_s).dropna()
        if not valuation.empty:
            result["kpis"]["total_inventory_value"] = round(float(valuation.sum()), 2)

    if warehouse_col:
        result["kpis"]["warehouses"] = int(df[warehouse_col].nunique())

    # ── Charts ────────────────────────────────────────────────────────────
    if category_col and qty_col:
        cat_stock = df.groupby(category_col)[qty_col].apply(
            lambda x: pd.to_numeric(x, errors="coerce").sum()
        ).sort_values(ascending=False)
        result["charts"].append({
            "title": "Stock by Category",
            "type": "bar",
            "data": [{"name": str(k), "value": int(v)} for k, v in cat_stock.items()],
        })

    if category_col and qty_col and price_col:
        val_df = df.copy()
        val_df["_val"] = pd.to_numeric(val_df[qty_col], errors="coerce") * pd.to_numeric(val_df[price_col], errors="coerce")
        cat_val = val_df.groupby(category_col)["_val"].sum().sort_values(ascending=False)
        result["charts"].append({
            "title": "Inventory Value by Category",
            "type": "pie",
            "data": [{"name": str(k), "value": round(float(v), 2)} for k, v in cat_val.items()],
        })

    # ── Reorder alerts ────────────────────────────────────────────────────
    if reorder_col and qty_col:
        qty_s = pd.to_numeric(df[qty_col], errors="coerce")
        reorder_s = pd.to_numeric(df[reorder_col], errors="coerce")
        below_reorder = df[qty_s < reorder_s].copy()
        if not below_reorder.empty:
            name_col = product_col or df.columns[0]
            for _, row in below_reorder.head(20).iterrows():
                result["alerts"].append({
                    "product": str(row.get(name_col, "Unknown")),
                    "current_stock": _safe_int(row.get(qty_col)),
                    "reorder_level": _safe_int(row.get(reorder_col)),
                    "severity": "critical" if _safe_int(row.get(qty_col)) == 0 else "warning",
                })

    # Zero stock items
    if qty_col:
        qty_s = pd.to_numeric(df[qty_col], errors="coerce")
        zero_stock = int((qty_s == 0).sum())
        if zero_stock > 0:
            result["kpis"]["out_of_stock_items"] = zero_stock
            result["insights"].append(f"{zero_stock} item(s) are out of stock.")

    # ── Insights ──────────────────────────────────────────────────────────
    if result["kpis"].get("total_inventory_value"):
        result["insights"].append(
            f"Total inventory value is {_format_number(result['kpis']['total_inventory_value'])}."
        )
    if result["alerts"]:
        result["insights"].append(
            f"{len(result['alerts'])} product(s) are below reorder level and need restocking."
        )

    return result


# ---------------------------------------------------------------------------
# General Analytics (any dataset)
# ---------------------------------------------------------------------------

def analyze_general(df: pd.DataFrame) -> dict:
    """Analyze any dataset with configurable metrics."""
    result = {
        "type": "general",
        "kpis": {
            "total_rows": len(df),
            "total_columns": len(df.columns),
        },
        "charts": [],
        "tables": [],
        "insights": [],
        "column_analysis": [],
    }

    numeric_cols = []
    categorical_cols = []
    date_cols = []

    for col in df.columns:
        series = df[col].dropna()
        if series.empty:
            continue

        numeric = pd.to_numeric(series, errors="coerce")
        if numeric.notna().sum() / max(len(series), 1) > 0.7:
            numeric_cols.append(col)
            numeric = numeric.dropna()
            analysis = {
                "column": col,
                "type": "numeric",
                "count": int(numeric.count()),
                "mean": round(float(numeric.mean()), 2),
                "median": round(float(numeric.median()), 2),
                "std": round(float(numeric.std()), 2),
                "min": round(float(numeric.min()), 2),
                "max": round(float(numeric.max()), 2),
            }
            result["column_analysis"].append(analysis)
        elif series.nunique() < min(20, len(series) * 0.5):
            categorical_cols.append(col)
            result["column_analysis"].append({
                "column": col,
                "type": "categorical",
                "unique_values": int(series.nunique()),
                "top_values": series.value_counts().head(5).to_dict(),
            })
        else:
            result["column_analysis"].append({
                "column": col,
                "type": "text",
                "unique_values": int(series.nunique()),
            })

    # Auto-generate charts for the first few numeric columns
    for col in numeric_cols[:3]:
        numeric = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(numeric) > 0:
            # Distribution chart
            result["charts"].append({
                "title": f"Distribution: {col}",
                "type": "bar",
                "data": _create_histogram_data(numeric),
            })

    # Category charts for first few categorical columns
    for col in categorical_cols[:3]:
        counts = df[col].value_counts().head(10)
        result["charts"].append({
            "title": f"{col} Distribution",
            "type": "pie" if len(counts) <= 6 else "bar",
            "data": [{"name": str(k), "value": int(v)} for k, v in counts.items()],
        })

    # Cross-analysis: if we have a numeric and categorical column
    if numeric_cols and categorical_cols:
        num_col = numeric_cols[0]
        cat_col = categorical_cols[0]
        grouped = df.groupby(cat_col)[num_col].apply(
            lambda x: pd.to_numeric(x, errors="coerce").mean()
        ).sort_values(ascending=False).head(10)
        if not grouped.empty:
            result["charts"].append({
                "title": f"Avg {num_col} by {cat_col}",
                "type": "bar",
                "data": [{"name": str(k), "value": round(float(v), 2)} for k, v in grouped.items()],
            })

    # Insights
    result["insights"].append(
        f"Dataset contains {len(df)} rows and {len(df.columns)} columns "
        f"({len(numeric_cols)} numeric, {len(categorical_cols)} categorical)."
    )
    if numeric_cols:
        for col in numeric_cols[:2]:
            numeric = pd.to_numeric(df[col], errors="coerce").dropna()
            if not numeric.empty:
                result["insights"].append(
                    f"{col}: mean={_format_number(float(numeric.mean()))}, "
                    f"median={_format_number(float(numeric.median()))}, "
                    f"range=[{_format_number(float(numeric.min()))} – {_format_number(float(numeric.max()))}]."
                )

    return result


# ---------------------------------------------------------------------------
# Master analysis function
# ---------------------------------------------------------------------------

def run_business_analysis(df: pd.DataFrame, dataset_type: Optional[str] = None) -> dict:
    """
    Run the appropriate analysis based on detected or specified dataset type.
    """
    if dataset_type is None:
        dataset_type = detect_dataset_type(df)

    log.info("Detected dataset type: %s", dataset_type)

    if dataset_type == "sales":
        return analyze_sales(df)
    elif dataset_type == "hr":
        return analyze_hr(df)
    elif dataset_type == "inventory":
        return analyze_inventory(df)
    elif dataset_type == "financial":
        # Fall through to the existing financial pipeline
        return {"type": "financial", "use_financial_pipeline": True}
    else:
        return analyze_general(df)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_col_fuzzy(cols_map: dict[str, str], candidates: list[str]) -> Optional[str]:
    """Find the original column name using fuzzy matching."""
    for cand in candidates:
        cand_norm = cand.lower().replace("_", " ").strip()
        for col_norm, col_orig in cols_map.items():
            if cand_norm == col_norm or cand_norm in col_norm or col_norm in cand_norm:
                return col_orig
    return None


def _format_number(n: float) -> str:
    """Format a number with commas."""
    if abs(n) >= 1_000_000:
        return f"{n:,.0f}"
    elif abs(n) >= 1_000:
        return f"{n:,.0f}"
    else:
        return f"{n:,.2f}"


def _safe_int(val) -> int:
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return 0


def _create_histogram_data(series: pd.Series, bins: int = 10) -> list[dict]:
    """Create histogram bin data for charting."""
    try:
        counts, edges = np.histogram(series.dropna(), bins=bins)
        data = []
        for i, count in enumerate(counts):
            label = f"{edges[i]:.0f}-{edges[i+1]:.0f}"
            data.append({"name": label, "value": int(count)})
        return data
    except Exception:
        return []
