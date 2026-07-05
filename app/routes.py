from flask import Blueprint, jsonify, render_template, request

from app import db
from app.models import UploadBatch, StudentRecord
from app.data_processing import read_uploaded_file, validate_and_clean

main_bp = Blueprint("main", __name__)

ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/api/health")
def health():
    """Sanity check route - confirms app + DB are wired up correctly."""
    return jsonify({"status": "ok", "message": "EduTech AI Dashboard backend is running"})


@main_bp.route("/api/upload", methods=["POST"])
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
def list_batches():
    """List upload history - useful for debugging and the future 'manage uploads' UI."""
    batches = UploadBatch.query.order_by(UploadBatch.uploaded_at.desc()).all()
    return jsonify([b.to_dict() for b in batches])


@main_bp.route("/api/batches/<int:batch_id>", methods=["DELETE"])
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
