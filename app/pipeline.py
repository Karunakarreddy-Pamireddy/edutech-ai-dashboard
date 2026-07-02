"""
Data Analytics Pipeline - Day 4
Cleaning, normalization, and transformation of raw student records.
Takes a raw DataFrame from data_access.py and returns a clean,
analysis-ready DataFrame for the Day 5 KPI calculations.
"""
import pandas as pd
import numpy as np


# ── Constants ────────────────────────────────────────────────────────────────
PASS_THRESHOLD = 50.0        # score >= 50 is a pass
SCORE_LOW_CLIP  = 0.0
SCORE_HIGH_CLIP = 100.0


# ── Step 1: Basic cleaning ────────────────────────────────────────────────────
def clean_raw_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean a raw DataFrame coming out of data_access.get_all_records_df().
    - Drop fully empty rows
    - Clip scores to 0-100
    - Normalize text fields (strip whitespace, title-case)
    - Parse dates
    - Fill optional nulls
    Returns a cleaned copy (does not mutate input).
    """
    if df.empty:
        return df.copy()

    df = df.copy()

    # Drop rows with no score or no student_id (should be rare after upload validation,
    # but defensive programming is good in a pipeline)
    df.dropna(subset=["score", "student_id"], inplace=True)

    # Clip scores
    df["score"] = df["score"].clip(lower=SCORE_LOW_CLIP, upper=SCORE_HIGH_CLIP)

    # Normalize text
    for col in ["student_id", "class_name", "subject"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    # Title-case subject and class_name for consistent grouping
    df["subject"]    = df["subject"].str.title()
    df["class_name"] = df["class_name"].str.title()

    # Parse record_date to datetime
    df["record_date"] = pd.to_datetime(df["record_date"], errors="coerce")
    df.dropna(subset=["record_date"], inplace=True)

    # Fill optional study_hours nulls with median
    if df["study_hours"].isnull().any():
        median_hours = df["study_hours"].median()
        df["study_hours"] = df["study_hours"].fillna(median_hours)

    # Ensure ai_tool_used is boolean
    df["ai_tool_used"] = df["ai_tool_used"].astype(bool)

    return df.reset_index(drop=True)


# ── Step 2: Feature engineering ───────────────────────────────────────────────
def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add derived columns useful for KPIs and charts:
      - pass_fail       : 'Pass' / 'Fail' based on PASS_THRESHOLD
      - score_band      : 'Excellent' / 'Good' / 'Average' / 'Below Average'
      - ai_group        : 'AI Users' / 'Non-AI Users' (readable label)
      - year_month      : e.g. '2025-01' for time-series grouping
      - study_hours_band: 'Low (<3h)' / 'Medium (3-6h)' / 'High (>6h)'
    """
    df = df.copy()

    # Pass / Fail
    df["pass_fail"] = df["score"].apply(
        lambda s: "Pass" if s >= PASS_THRESHOLD else "Fail"
    )

    # Score band
    df["score_band"] = pd.cut(
        df["score"],
        bins=[0, 49.9, 59.9, 74.9, 100],
        labels=["Below Average", "Average", "Good", "Excellent"],
        right=True,
    ).astype(str)

    # AI group label
    df["ai_group"] = df["ai_tool_used"].map({True: "AI Users", False: "Non-AI Users"})

    # Year-month for trend charts
    df["year_month"] = df["record_date"].dt.to_period("M").astype(str)

    # Study hours band
    df["study_hours_band"] = pd.cut(
        df["study_hours"],
        bins=[0, 3, 6, float("inf")],
        labels=["Low (<3h)", "Medium (3-6h)", "High (>6h)"],
        right=True,
    ).astype(str)

    return df


# ── Step 3: Outlier detection (flag only, don't drop) ─────────────────────────
def flag_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Flag score outliers using IQR method per subject.
    Adds boolean column 'score_outlier' — used for info, not filtering.
    """
    df = df.copy()
    df["score_outlier"] = False

    for subject, group in df.groupby("subject"):
        q1 = group["score"].quantile(0.25)
        q3 = group["score"].quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        mask = (df["subject"] == subject) & (
            (df["score"] < lower) | (df["score"] > upper)
        )
        df.loc[mask, "score_outlier"] = True

    return df


# ── Master pipeline function ───────────────────────────────────────────────────
def run_pipeline(raw_df: pd.DataFrame) -> pd.DataFrame:
    """
    Run the full cleaning + feature engineering pipeline.
    Input:  raw DataFrame from data_access.get_all_records_df()
    Output: clean, enriched DataFrame ready for KPI calculations (Day 5)
    """
    if raw_df.empty:
        return raw_df

    df = clean_raw_df(raw_df)
    df = engineer_features(df)
    df = flag_outliers(df)
    return df


# ── Pipeline summary (used by the API to show pipeline health) ─────────────────
def pipeline_summary(clean_df: pd.DataFrame) -> dict:
    """Return a quick summary of what the pipeline produced."""
    if clean_df.empty:
        return {"error": "No data available. Upload a file first."}

    return {
        "total_records": len(clean_df),
        "subjects": sorted(clean_df["subject"].unique().tolist()),
        "classes": sorted(clean_df["class_name"].unique().tolist()),
        "date_range": {
            "from": clean_df["record_date"].min().strftime("%Y-%m-%d"),
            "to":   clean_df["record_date"].max().strftime("%Y-%m-%d"),
        },
        "score_stats": {
            "mean":   round(clean_df["score"].mean(), 2),
            "median": round(clean_df["score"].median(), 2),
            "min":    round(clean_df["score"].min(), 2),
            "max":    round(clean_df["score"].max(), 2),
            "std":    round(clean_df["score"].std(), 2),
        },
        "ai_tool_usage": {
            "users":     int(clean_df["ai_tool_used"].sum()),
            "non_users": int((~clean_df["ai_tool_used"]).sum()),
            "adoption_pct": round(clean_df["ai_tool_used"].mean() * 100, 1),
        },
        "pass_rate_pct": round(
            (clean_df["pass_fail"] == "Pass").mean() * 100, 1
        ),
        "outliers_flagged": int(clean_df["score_outlier"].sum()),
    }
