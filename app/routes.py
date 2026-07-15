from flask import Blueprint, jsonify, render_template, request
from flask_login import login_required, current_user

from app import db
from app.models import UploadBatch, StudentRecord
from app.data_processing import read_uploaded_file, validate_and_clean

main_bp = Blueprint("main", __name__)

ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


@main_bp.route("/")
def index():
    from flask_login import current_user
    if current_user.is_authenticated:
        return render_template("index.html")
    return render_template("landing.html")

@main_bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("index.html")


@main_bp.route("/api/health")
def health():
    """Sanity check route - confirms app + DB are wired up correctly."""
    return jsonify({"status": "ok", "message": "EduTech AI Dashboard backend is running"})


@main_bp.route("/api/upload", methods=["POST"])
@login_required
def upload_file():
    """
    Accepts a CSV/Excel file under form field 'file'.
    Parses, validates, stores good rows under a new UploadBatch.
    Bad rows are skipped and reported back - they never crash the upload.
    """
    if "file" not in request.files:
        return jsonify({"error": "No file part in request. Send as multipart/form-data with field name 'file'."}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected."}), 400

    filename = file.filename
    if not any(filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS):
        return jsonify({"error": f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"}), 400

    try:
        df = read_uploaded_file(file, filename)
        result = validate_and_clean(df)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Unexpected error parsing file: {e}"}), 500

    if result.valid_count == 0:
        return jsonify({
            "error": "No valid rows could be parsed from this file.",
            "summary": result.to_summary(),
        }), 400

    status = "success" if result.error_count == 0 else "partial"
    batch = UploadBatch(filename=filename, row_count=result.valid_count, status=status)
    db.session.add(batch)
    db.session.flush()  # get batch.id before inserting records

    for row in result.valid_rows:
        db.session.add(StudentRecord(batch_id=batch.id, **row))

    db.session.commit()

    return jsonify({
        "message": f"Upload processed: {result.valid_count} rows stored, {result.error_count} rows skipped.",
        "batch": batch.to_dict(),
        "summary": result.to_summary(),
    }), 201


@main_bp.route("/api/batches")
@login_required
def list_batches():
    """List upload history - useful for debugging and the future 'manage uploads' UI."""
    batches = UploadBatch.query.order_by(UploadBatch.uploaded_at.desc()).all()
    return jsonify([b.to_dict() for b in batches])


@main_bp.route("/api/batches/<int:batch_id>", methods=["DELETE"])
@login_required
def delete_batch(batch_id):
    """Delete a batch and all its records (cascade) - lets you clean up a bad upload."""
    batch = UploadBatch.query.get_or_404(batch_id)
    db.session.delete(batch)
    db.session.commit()
    return jsonify({"message": f"Batch {batch_id} and its records were deleted."})


# Day 6 will add:
#   GET  /api/kpis
#   GET  /api/charts/<type>
#   GET  /api/filters
# Day 9 (conditional) will add:
#   POST /api/predict


@main_bp.route("/api/records")
@login_required
def get_records():
    """
    Preview stored records with optional filters.
    Query params: subject, class_name, ai_tool_used, date_from, date_to, limit (default 50)
    """
    from app.data_access import get_all_records_df

    filters = {
        "subject": request.args.get("subject"),
        "class_name": request.args.get("class_name"),
        "ai_tool_used": (
            True if request.args.get("ai_tool_used") == "true"
            else False if request.args.get("ai_tool_used") == "false"
            else None
        ),
        "date_from": request.args.get("date_from"),
        "date_to": request.args.get("date_to"),
    }
    limit = int(request.args.get("limit", 50))
    df = get_all_records_df(filters)

    if df.empty:
        return jsonify({"total": 0, "records": []})

    if "record_date" in df.columns:
        df["record_date"] = df["record_date"].astype(str)

    return jsonify({
        "total": len(df),
        "showing": min(limit, len(df)),
        "records": df.head(limit).to_dict(orient="records"),
    })


@main_bp.route("/api/filter-options")
@login_required
def get_filter_options():
    """Return unique subjects and classes for dropdown filters."""
    from app.data_access import get_filter_options, get_record_count
    options = get_filter_options()
    options["total_records"] = get_record_count()
    return jsonify(options)


@main_bp.route("/api/batches/<int:batch_id>/detail")
def get_batch_detail(batch_id):
    """Return a batch plus a 10-row preview of its records."""
    from app.data_access import get_batch_with_preview
    batch, preview = get_batch_with_preview(batch_id)
    if not batch:
        return jsonify({"error": f"Batch {batch_id} not found"}), 404
    return jsonify({"batch": batch.to_dict(), "preview": preview})


# Day 6 will add:  GET /api/kpis,  GET /api/charts/<type>
# Day 9 (conditional) will add:  POST /api/predict


@main_bp.route("/api/pipeline/summary")
def pipeline_summary_route():
    """
    Run the full cleaning pipeline and return a summary.
    Shows data quality, score stats, AI adoption rate, pass rate.
    Used by the dashboard header cards (Day 7).
    """
    from app.data_access import get_all_records_df
    from app.pipeline import run_pipeline, pipeline_summary

    raw_df = get_all_records_df()
    clean_df = run_pipeline(raw_df)
    return jsonify(pipeline_summary(clean_df))


@main_bp.route("/api/pipeline/preview")
def pipeline_preview_route():
    """
    Return first 20 rows of the cleaned+enriched DataFrame.
    Useful for verifying the pipeline output during development.
    """
    from app.data_access import get_all_records_df
    from app.pipeline import run_pipeline

    raw_df = get_all_records_df()
    clean_df = run_pipeline(raw_df)

    if clean_df.empty:
        return jsonify({"error": "No data available. Upload a file first."})

    # Serialize dates for JSON
    preview = clean_df.head(20).copy()
    preview["record_date"] = preview["record_date"].astype(str)
    return jsonify({
        "columns": list(preview.columns),
        "rows": preview.to_dict(orient="records"),
    })


@main_bp.route("/api/kpis")
@login_required
def get_kpis():
    """
    Master KPI endpoint — runs the full pipeline and returns all
    chart data and KPI cards in one bundle. Called by the dashboard (Day 7).
    Supports same filters as /api/records:
      ?subject=Math&class_name=Class+5A&ai_tool_used=true&date_from=2025-01&date_to=2025-04
    """
    from app.data_access import get_all_records_df
    from app.pipeline import run_pipeline
    from app.kpis import compute_all_kpis

    filters = {
        "subject":      request.args.get("subject"),
        "class_name":   request.args.get("class_name"),
        "ai_tool_used": (
            True  if request.args.get("ai_tool_used") == "true"
            else False if request.args.get("ai_tool_used") == "false"
            else None
        ),
        "date_from": request.args.get("date_from"),
        "date_to":   request.args.get("date_to"),
    }

    raw_df   = get_all_records_df(filters)
    clean_df = run_pipeline(raw_df)

    if clean_df.empty:
        return jsonify({"error": "No data available. Upload a file first."}), 404

    return jsonify(compute_all_kpis(clean_df))


@main_bp.route("/api/export/csv")
@login_required
def export_csv():
    """Export filtered records as a downloadable CSV."""
    import io
    import csv
    from flask import Response
    from app.data_access import get_all_records_df
    from app.pipeline import run_pipeline

    filters = {
        "subject":      request.args.get("subject"),
        "class_name":   request.args.get("class_name"),
        "ai_tool_used": (
            True  if request.args.get("ai_tool_used") == "true"
            else False if request.args.get("ai_tool_used") == "false"
            else None
        ),
        "date_from": request.args.get("date_from"),
        "date_to":   request.args.get("date_to"),
    }

    raw_df   = get_all_records_df(filters)
    clean_df = run_pipeline(raw_df)

    if clean_df.empty:
        return jsonify({"error": "No data to export"}), 404

    clean_df["record_date"] = clean_df["record_date"].astype(str)
    export_cols = [
        "student_id","class_name","subject","score",
        "ai_tool_used","study_hours","record_date",
        "pass_fail","score_band","ai_group","year_month"
    ]
    export_df = clean_df[[c for c in export_cols if c in clean_df.columns]]

    output = io.StringIO()
    export_df.to_csv(output, index=False)
    output.seek(0)

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=edutech_export.csv"}
    )


@main_bp.route("/api/stats/summary")
def stats_summary():
    """
    Quick stats for the dashboard header — total records, batches,
    last upload time. Used by auto-refresh to detect new data.
    """
    from app.data_access import get_record_count
    last_batch = UploadBatch.query.order_by(UploadBatch.uploaded_at.desc()).first()
    return jsonify({
        "total_records": get_record_count(),
        "total_batches": UploadBatch.query.count(),
        "last_upload":   last_batch.uploaded_at.isoformat() if last_batch else None,
    })


# ── Day 9: AI Predictive Model endpoints ─────────────────────────────────────

@main_bp.route("/api/model/train", methods=["POST"])
@login_required
def train_model_route():
    """Train the predictive model on all current data in the DB."""
    from app.data_access import get_all_records_df
    from app.pipeline import run_pipeline
    from app.ml_model import train_model

    raw_df   = get_all_records_df()
    clean_df = run_pipeline(raw_df)

    if clean_df.empty:
        return jsonify({"error": "No data available. Upload a file first."}), 400

    result = train_model(clean_df)
    if "error" in result:
        return jsonify(result), 400

    return jsonify(result), 200


@main_bp.route("/api/model/status")
def model_status_route():
    """Return current model status and metrics."""
    from app.ml_model import model_status
    return jsonify(model_status())


@main_bp.route("/api/predict", methods=["POST"])
@login_required
def predict_route():
    """
    Predict a student's score.
    Expects JSON: { study_hours: float, ai_tool_used: bool, subject: str }
    Returns: { predicted_score, confidence_band, inputs, disclaimer }
    """
    from app.ml_model import predict_score

    data = request.get_json()
    if not data:
        return jsonify({"error": "Send JSON body: {study_hours, ai_tool_used, subject}"}), 400

    study_hours   = data.get("study_hours")
    ai_tool_used  = data.get("ai_tool_used")
    subject       = data.get("subject")

    if study_hours is None or ai_tool_used is None or not subject:
        return jsonify({"error": "Required fields: study_hours (number), ai_tool_used (bool), subject (string)"}), 400

    try:
        study_hours = float(study_hours)
    except (TypeError, ValueError):
        return jsonify({"error": "study_hours must be a number"}), 400

    if study_hours < 0 or study_hours > 24:
        return jsonify({"error": "study_hours must be between 0 and 24"}), 400

    result = predict_score(study_hours, bool(ai_tool_used), subject)
    if "error" in result:
        return jsonify(result), 400

    return jsonify(result), 200


# ── Feature additions ─────────────────────────────────────────────────────────

@main_bp.route("/api/student/<student_id>")
@login_required
def student_profile(student_id):
    """Look up individual student — all records, avg score, trend, AI usage."""
    from app.models import StudentRecord
    records = StudentRecord.query.filter_by(student_id=student_id)\
                .order_by(StudentRecord.record_date).all()
    if not records:
        return jsonify({"error": f"No records found for student '{student_id}'."}), 404

    scores     = [r.score for r in records]
    ai_count   = sum(1 for r in records if r.ai_tool_used)
    subjects   = list(set(r.subject for r in records))
    classes    = list(set(r.class_name for r in records))

    return jsonify({
        "student_id":    student_id,
        "total_records": len(records),
        "avg_score":     round(sum(scores)/len(scores), 2),
        "best_score":    round(max(scores), 1),
        "lowest_score":  round(min(scores), 1),
        "ai_usage_pct":  round(ai_count/len(records)*100, 1),
        "subjects":      subjects,
        "classes":       classes,
        "records": [
            {
                "date":         r.record_date.isoformat(),
                "subject":      r.subject,
                "class_name":   r.class_name,
                "score":        r.score,
                "ai_tool_used": r.ai_tool_used,
                "study_hours":  r.study_hours,
            } for r in records
        ]
    })


@main_bp.route("/api/student/search")
@login_required
def student_search():
    """Search students by ID prefix — for autocomplete."""
    q = request.args.get("q", "").strip().upper()
    if len(q) < 1:
        return jsonify([])
    from app.models import StudentRecord
    from sqlalchemy import distinct
    matches = (
        StudentRecord.query
        .with_entities(distinct(StudentRecord.student_id))
        .filter(StudentRecord.student_id.like(f"{q}%"))
        .limit(10).all()
    )
    return jsonify([m[0] for m in matches])


@main_bp.route("/api/compare")
@login_required
def compare():
    """
    Compare two groups side by side.
    ?group_by=class_name&a=Class 5A&b=Class 5B
    ?group_by=subject&a=Math&b=Science
    """
    from app.data_access import get_all_records_df
    from app.pipeline import run_pipeline

    group_by = request.args.get("group_by", "class_name")
    a        = request.args.get("a", "")
    b        = request.args.get("b", "")

    if not a or not b:
        return jsonify({"error": "Provide both ?a= and ?b= parameters"}), 400

    raw_df   = get_all_records_df()
    clean_df = run_pipeline(raw_df)

    if clean_df.empty:
        return jsonify({"error": "No data available"}), 404

    def group_stats(df, val):
        g = df[df[group_by] == val]
        if g.empty:
            return None
        ai  = g[g["ai_tool_used"]==True]
        nai = g[g["ai_tool_used"]==False]
        by_subj = g.groupby("subject")["score"].mean().round(2).to_dict() if group_by == "class_name" else {}
        return {
            "label":          val,
            "total_records":  len(g),
            "avg_score":      round(g["score"].mean(), 2),
            "ai_avg_score":   round(ai["score"].mean(), 2) if len(ai) else None,
            "non_ai_avg":     round(nai["score"].mean(), 2) if len(nai) else None,
            "ai_adoption_pct":round(g["ai_tool_used"].mean()*100, 1),
            "pass_rate_pct":  round((g["pass_fail"]=="Pass").mean()*100, 1),
            "score_std":      round(g["score"].std(), 2),
            "by_subject":     by_subj,
            "trend": (
                g.groupby("year_month")["score"].mean().round(2).to_dict()
            ),
        }

    return jsonify({
        "group_by": group_by,
        "a": group_stats(clean_df, a),
        "b": group_stats(clean_df, b),
        "available": sorted(clean_df[group_by].unique().tolist()),
    })


@main_bp.route("/api/notifications")
@login_required
def notifications():
    """Generate smart alerts based on current data patterns."""
    from app.data_access import get_all_records_df
    from app.pipeline import run_pipeline

    raw_df   = get_all_records_df()
    clean_df = run_pipeline(raw_df)

    alerts = []

    if clean_df.empty:
        return jsonify({"alerts": [], "count": 0})

    # 1. Low AI adoption classes
    adoption = clean_df.groupby("class_name")["ai_tool_used"].mean() * 100
    for cls, pct in adoption.items():
        if pct < 25:
            alerts.append({
                "type": "warning",
                "icon": "⚠️",
                "title": f"Low AI Adoption — {cls}",
                "message": f"Only {round(pct,1)}% of {cls} students use AI tools. Consider encouraging adoption.",
            })

    # 2. High failing classes
    fail_rate = clean_df.groupby("class_name").apply(
        lambda g: (g["pass_fail"]=="Fail").mean()*100
    )
    for cls, pct in fail_rate.items():
        if pct > 20:
            alerts.append({
                "type": "danger",
                "icon": "🚨",
                "title": f"High Fail Rate — {cls}",
                "message": f"{round(pct,1)}% of {cls} students are failing. Immediate attention needed.",
            })

    # 3. Subjects with big AI vs non-AI gap
    for subj in clean_df["subject"].unique():
        sg   = clean_df[clean_df["subject"]==subj]
        ai_s = sg[sg["ai_tool_used"]==True]["score"]
        nai  = sg[sg["ai_tool_used"]==False]["score"]
        if len(ai_s) > 5 and len(nai) > 5:
            gap = ai_s.mean() - nai.mean()
            if gap > 15:
                alerts.append({
                    "type": "info",
                    "icon": "🤖",
                    "title": f"Strong AI Impact — {subj}",
                    "message": f"AI users score {round(gap,1)} pts higher in {subj}. Great subject to promote AI tools.",
                })

    # 4. Outlier students
    out_count = int(clean_df["score_outlier"].sum())
    if out_count > 0:
        alerts.append({
            "type": "info",
            "icon": "📊",
            "title": f"{out_count} Score Outliers Detected",
            "message": "Some students have unusually high or low scores. Check the Records tab for details.",
        })

    # 5. Overall positive insight
    boost = round(
        clean_df[clean_df["ai_tool_used"]==True]["score"].mean() -
        clean_df[clean_df["ai_tool_used"]==False]["score"].mean(), 1
    )
    if boost > 0:
        alerts.append({
            "type": "success",
            "icon": "✅",
            "title": "AI Tools Are Working",
            "message": f"Across all classes, AI tool users score {boost} points higher on average.",
        })

    return jsonify({"alerts": alerts, "count": len(alerts)})


# ── Day 12: New Dashboard Feature Endpoints ───────────────────────────────────

@main_bp.route("/api/student/<student_id>")
@login_required
def get_student(student_id):
    """Return full history and stats for a single student."""
    from app.data_access import get_all_records_df
    from app.pipeline import run_pipeline

    df = get_all_records_df()
    if df.empty:
        return jsonify({"error": "No data available."}), 404

    clean = run_pipeline(df)
    sdf   = clean[clean["student_id"] == student_id.upper()]

    if sdf.empty:
        return jsonify({"error": f"Student '{student_id}' not found."}), 404

    sdf = sdf.copy()
    sdf["record_date"] = sdf["record_date"].astype(str)

    records = sdf.sort_values("record_date").to_dict(orient="records")
    scores  = sdf["score"].tolist()

    return jsonify({
        "student_id":   student_id.upper(),
        "total_records":len(sdf),
        "avg_score":    round(sdf["score"].mean(), 2),
        "best_score":   round(sdf["score"].max(), 2),
        "worst_score":  round(sdf["score"].min(), 2),
        "pass_rate":    round((sdf["pass_fail"] == "Pass").mean() * 100, 1),
        "ai_usage_pct": round(sdf["ai_tool_used"].mean() * 100, 1),
        "subjects":     sorted(sdf["subject"].unique().tolist()),
        "classes":      sorted(sdf["class_name"].unique().tolist()),
        "score_trend":  {
            "dates":  sdf.sort_values("record_date")["record_date"].tolist(),
            "scores": sdf.sort_values("record_date")["score"].tolist(),
        },
        "records": records,
    })


@main_bp.route("/api/notifications")
@login_required
def get_notifications():
    """Auto-generate alerts based on KPI thresholds."""
    from app.data_access import get_all_records_df, get_filter_options
    from app.pipeline import run_pipeline

    df    = get_all_records_df()
    if df.empty:
        return jsonify({"notifications": [], "count": 0})

    clean = run_pipeline(df)
    notes = []

    # Check each class
    for cls in clean["class_name"].unique():
        cdf = clean[clean["class_name"] == cls]
        avg    = cdf["score"].mean()
        ai_pct = cdf["ai_tool_used"].mean() * 100
        pass_r = (cdf["pass_fail"] == "Pass").mean() * 100

        if avg < 55:
            notes.append({"type":"danger","icon":"🚨",
                "title":f"{cls} — Low Average Score",
                "message":f"Average score is {round(avg,1)} — below the 55-point warning threshold.",
                "class":cls})
        elif avg < 65:
            notes.append({"type":"warning","icon":"⚠️",
                "title":f"{cls} — Below Target",
                "message":f"Average score is {round(avg,1)} — consider intervention strategies.",
                "class":cls})

        if ai_pct < 25:
            notes.append({"type":"info","icon":"📢",
                "title":f"{cls} — Low AI Adoption",
                "message":f"Only {round(ai_pct,1)}% of students in {cls} are using AI tools.",
                "class":cls})

        if pass_r < 80:
            notes.append({"type":"danger","icon":"🚨",
                "title":f"{cls} — High Failure Rate",
                "message":f"Pass rate is {round(pass_r,1)}% — {round(100-pass_r,1)}% of students are failing.",
                "class":cls})

    # Overall alerts
    overall_ai  = clean["ai_tool_used"].mean() * 100
    overall_avg = clean["score"].mean()
    if overall_ai < 40:
        notes.append({"type":"info","icon":"💡",
            "title":"Overall — AI Adoption Below 40%",
            "message":f"Platform-wide AI adoption is {round(overall_ai,1)}%. Encourage more AI tool usage.",
            "class":"All"})

    # Sort: danger first, then warning, then info
    order = {"danger":0,"warning":1,"info":2}
    notes.sort(key=lambda x: order.get(x["type"],3))

    return jsonify({"notifications": notes[:15], "count": len(notes)})


# ── Day 12: New dashboard features ───────────────────────────────────────────



@main_bp.route("/api/comparison")
@login_required
def get_comparison():
    """Compare two groups side by side. type=class|subject, group_a, group_b"""
    from app.data_access import get_all_records_df
    from app.pipeline import run_pipeline

    group_a  = request.args.get("group_a", "")
    group_b  = request.args.get("group_b", "")
    grp_type = request.args.get("type", "class")

    if not group_a or not group_b:
        return jsonify({"error": "Provide group_a and group_b params"}), 400

    raw_df = get_all_records_df()
    df     = run_pipeline(raw_df)
    field  = "class_name" if grp_type == "class" else "subject"

    def grp_stats(name):
        g = df[df[field] == name]
        if g.empty:
            return {"name": name, "error": "No data", "total_records":0,
                    "avg_score":0,"ai_adoption":0,"ai_avg":0,"non_ai_avg":0,"pass_rate":0,"score_dist":{},"trend":{}}
        ai_df    = g[g["ai_tool_used"] == True]
        nonai_df = g[g["ai_tool_used"] == False]
        return {
            "name":          name,
            "total_records": int(len(g)),
            "avg_score":     round(float(g["score"].mean()), 2),
            "ai_adoption":   round(float(g["ai_tool_used"].mean() * 100), 1),
            "ai_avg":        round(float(ai_df["score"].mean()), 2) if len(ai_df) else 0,
            "non_ai_avg":    round(float(nonai_df["score"].mean()), 2) if len(nonai_df) else 0,
            "pass_rate":     round(float((g["pass_fail"] == "Pass").mean() * 100), 1),
            "score_dist":    g["score_band"].value_counts().to_dict(),
            "trend":         g.groupby("year_month")["score"].mean().round(2).to_dict(),
        }

    return jsonify({
        "type":    grp_type,
        "group_a": grp_stats(group_a),
        "group_b": grp_stats(group_b),
    })




