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
