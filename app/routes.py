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
