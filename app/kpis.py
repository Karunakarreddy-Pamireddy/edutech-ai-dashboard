"""
KPI Calculations - Day 5
All analytics functions that power the dashboard charts and KPI cards.
Every function takes a clean DataFrame (output of pipeline.run_pipeline())
and returns a JSON-serializable dict or list.

KPIs implemented:
  1. overview_kpis()          - headline numbers for KPI cards
  2. ai_vs_nonai_scores()     - core insight: AI users vs non-AI users
  3. avg_score_by_subject()   - bar chart: average score per subject
  4. avg_score_by_class()     - bar chart: average score per class
  5. score_trend_over_time()  - line chart: monthly score trend
  6. pass_fail_distribution() - pie chart: pass vs fail counts
  7. score_distribution()     - histogram: score band breakdown
  8. study_hours_vs_score()   - scatter: study hours impact on score
  9. ai_adoption_by_class()   - bar: AI usage rate per class
  10. top_bottom_students()   - leaderboard: top 5 and bottom 5
"""
import pandas as pd


# ── 1. Overview KPI Cards ─────────────────────────────────────────────────────
def overview_kpis(df: pd.DataFrame) -> dict:
    """Headline numbers shown in the dashboard KPI cards."""
    if df.empty:
        return {}

    ai_users    = df[df["ai_tool_used"] == True]
    non_ai      = df[df["ai_tool_used"] == False]
    avg_ai      = round(ai_users["score"].mean(), 2) if not ai_users.empty else 0
    avg_non_ai  = round(non_ai["score"].mean(), 2)   if not non_ai.empty  else 0
    improvement = round(avg_ai - avg_non_ai, 2)

    return {
        "total_students":    int(df["student_id"].nunique()),
        "total_records":     int(len(df)),
        "avg_score":         round(df["score"].mean(), 2),
        "pass_rate_pct":     round((df["pass_fail"] == "Pass").mean() * 100, 1),
        "ai_adoption_pct":   round(df["ai_tool_used"].mean() * 100, 1),
        "avg_score_ai":      avg_ai,
        "avg_score_non_ai":  avg_non_ai,
        "ai_score_boost":    improvement,   # positive = AI users score higher
        "outliers_flagged":  int(df["score_outlier"].sum()),
    }


# ── 2. AI vs Non-AI Score Comparison ─────────────────────────────────────────
def ai_vs_nonai_scores(df: pd.DataFrame) -> dict:
    """
    Core insight: compare average scores between AI users and non-AI users,
    broken down overall and by subject.
    """
    if df.empty:
        return {}

    # Overall
    overall = (
        df.groupby("ai_group")["score"]
        .agg(avg_score="mean", count="count", std="std")
        .reset_index()
    )
    overall["avg_score"] = overall["avg_score"].round(2)
    overall["std"]       = overall["std"].round(2)

    # By subject
    by_subject = (
        df.groupby(["subject", "ai_group"])["score"]
        .mean()
        .round(2)
        .reset_index()
        .rename(columns={"score": "avg_score"})
    )

    subjects = sorted(df["subject"].unique().tolist())
    ai_scores     = []
    non_ai_scores = []
    for subj in subjects:
        subj_df = by_subject[by_subject["subject"] == subj]
        ai_row     = subj_df[subj_df["ai_group"] == "AI Users"]["avg_score"]
        non_ai_row = subj_df[subj_df["ai_group"] == "Non-AI Users"]["avg_score"]
        ai_scores.append(float(ai_row.values[0])     if not ai_row.empty     else 0)
        non_ai_scores.append(float(non_ai_row.values[0]) if not non_ai_row.empty else 0)

    return {
        "overall":      overall.to_dict(orient="records"),
        "by_subject": {
            "subjects":       subjects,
            "ai_scores":      ai_scores,
            "non_ai_scores":  non_ai_scores,
        },
    }


# ── 3. Average Score by Subject ───────────────────────────────────────────────
def avg_score_by_subject(df: pd.DataFrame) -> dict:
    """Bar chart data: average score and record count per subject."""
    if df.empty:
        return {}

    result = (
        df.groupby("subject")["score"]
        .agg(avg_score="mean", count="count")
        .reset_index()
        .sort_values("avg_score", ascending=False)
    )
    result["avg_score"] = result["avg_score"].round(2)

    return {
        "labels": result["subject"].tolist(),
        "scores": result["avg_score"].tolist(),
        "counts": result["count"].tolist(),
    }


# ── 4. Average Score by Class ─────────────────────────────────────────────────
def avg_score_by_class(df: pd.DataFrame) -> dict:
    """Bar chart data: average score per class."""
    if df.empty:
        return {}

    result = (
        df.groupby("class_name")["score"]
        .agg(avg_score="mean", count="count")
        .reset_index()
        .sort_values("avg_score", ascending=False)
    )
    result["avg_score"] = result["avg_score"].round(2)

    return {
        "labels": result["class_name"].tolist(),
        "scores": result["avg_score"].tolist(),
        "counts": result["count"].tolist(),
    }


# ── 5. Score Trend Over Time ──────────────────────────────────────────────────
def score_trend_over_time(df: pd.DataFrame) -> dict:
    """
    Line chart: monthly average score trend.
    Returns overall trend + separate lines for AI users vs non-AI users.
    """
    if df.empty:
        return {}

    overall = (
        df.groupby("year_month")["score"]
        .mean().round(2)
        .reset_index()
        .sort_values("year_month")
    )

    ai_trend = (
        df[df["ai_tool_used"] == True]
        .groupby("year_month")["score"]
        .mean().round(2)
        .reset_index()
        .sort_values("year_month")
    )

    non_ai_trend = (
        df[df["ai_tool_used"] == False]
        .groupby("year_month")["score"]
        .mean().round(2)
        .reset_index()
        .sort_values("year_month")
    )

    months = overall["year_month"].tolist()

    def align(trend_df):
        mapping = dict(zip(trend_df["year_month"], trend_df["score"]))
        return [round(mapping.get(m, 0), 2) for m in months]

    return {
        "months":         months,
        "overall":        overall["score"].tolist(),
        "ai_users":       align(ai_trend),
        "non_ai_users":   align(non_ai_trend),
    }


# ── 6. Pass/Fail Distribution ─────────────────────────────────────────────────
def pass_fail_distribution(df: pd.DataFrame) -> dict:
    """Pie chart: pass vs fail counts and percentages."""
    if df.empty:
        return {}

    counts = df["pass_fail"].value_counts()
    total  = len(df)

    return {
        "labels":       counts.index.tolist(),
        "counts":       counts.values.tolist(),
        "percentages":  [round(v / total * 100, 1) for v in counts.values],
    }


# ── 7. Score Distribution (Histogram) ────────────────────────────────────────
def score_distribution(df: pd.DataFrame) -> dict:
    """Bar chart: count of students in each score band."""
    if df.empty:
        return {}

    order  = ["Below Average", "Average", "Good", "Excellent"]
    counts = df["score_band"].value_counts()

    return {
        "labels": order,
        "counts": [int(counts.get(band, 0)) for band in order],
    }


# ── 8. Study Hours vs Score ───────────────────────────────────────────────────
def study_hours_vs_score(df: pd.DataFrame) -> dict:
    """
    Scatter plot data: study hours vs score.
    Returns sampled points (max 200) to keep chart responsive.
    """
    if df.empty:
        return {}

    sample = df[["study_hours", "score", "ai_group", "subject"]].dropna()
    if len(sample) > 200:
        sample = sample.sample(200, random_state=42)

    return {
        "points": sample.rename(columns={
            "study_hours": "x",
            "score":       "y",
        }).to_dict(orient="records"),
    }


# ── 9. AI Adoption by Class ───────────────────────────────────────────────────
def ai_adoption_by_class(df: pd.DataFrame) -> dict:
    """Bar chart: AI tool adoption rate (%) per class."""
    if df.empty:
        return {}

    result = (
        df.groupby("class_name")["ai_tool_used"]
        .mean()
        .mul(100)
        .round(1)
        .reset_index()
        .sort_values("ai_tool_used", ascending=False)
    )

    return {
        "labels": result["class_name"].tolist(),
        "rates":  result["ai_tool_used"].tolist(),
    }


# ── 10. Top/Bottom Students ───────────────────────────────────────────────────
def top_bottom_students(df: pd.DataFrame, n: int = 5) -> dict:
    """Leaderboard: top N and bottom N students by average score."""
    if df.empty:
        return {}

    avg_by_student = (
        df.groupby("student_id")
        .agg(
            avg_score=("score", "mean"),
            records=("score", "count"),
            ai_used=("ai_tool_used", "any"),
        )
        .reset_index()
    )
    avg_by_student["avg_score"] = avg_by_student["avg_score"].round(2)
    avg_by_student = avg_by_student.sort_values("avg_score", ascending=False)

    return {
        "top":    avg_by_student.head(n).to_dict(orient="records"),
        "bottom": avg_by_student.tail(n).sort_values("avg_score").to_dict(orient="records"),
    }


# ── Master KPI bundle ─────────────────────────────────────────────────────────
def compute_all_kpis(df: pd.DataFrame) -> dict:
    """
    Run all KPI functions and return a single bundle.
    Called by GET /api/kpis (Day 6) to serve the full dashboard in one request.
    """
    return {
        "overview":           overview_kpis(df),
        "ai_vs_nonai":        ai_vs_nonai_scores(df),
        "by_subject":         avg_score_by_subject(df),
        "by_class":           avg_score_by_class(df),
        "trend":              score_trend_over_time(df),
        "pass_fail":          pass_fail_distribution(df),
        "score_distribution": score_distribution(df),
        "study_vs_score":     study_hours_vs_score(df),
        "ai_adoption":        ai_adoption_by_class(df),
        "leaderboard":        top_bottom_students(df),
    }
