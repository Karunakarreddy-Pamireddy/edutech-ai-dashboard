"""
Data access layer (Day 3).
Single place to query StudentRecords from the DB and return clean DataFrames.
Day 4-5 pipeline imports from here — keeps SQLAlchemy out of the pipeline logic.
"""
import pandas as pd
from app.models import StudentRecord, UploadBatch


def get_all_records_df(filters=None):
    """
    Return all StudentRecords as a clean Pandas DataFrame.
    Optional filters dict supports: subject, class_name, ai_tool_used,
    date_from (YYYY-MM-DD str), date_to (YYYY-MM-DD str).
    """
    query = StudentRecord.query

    if filters:
        if filters.get("subject"):
            query = query.filter(StudentRecord.subject == filters["subject"])
        if filters.get("class_name"):
            query = query.filter(StudentRecord.class_name == filters["class_name"])
        if filters.get("ai_tool_used") is not None:
            query = query.filter(StudentRecord.ai_tool_used == filters["ai_tool_used"])
        if filters.get("date_from"):
            query = query.filter(StudentRecord.record_date >= filters["date_from"])
        if filters.get("date_to"):
            query = query.filter(StudentRecord.record_date <= filters["date_to"])

    records = query.all()

    if not records:
        return pd.DataFrame(columns=[
            "id", "student_id", "class_name", "subject",
            "score", "ai_tool_used", "study_hours", "record_date"
        ])

    return pd.DataFrame([r.to_dict() for r in records])


def get_filter_options():
    """Return all unique values for filter dropdowns (subjects, classes)."""
    from sqlalchemy import distinct
    from app import db

    subjects = [r[0] for r in db.session.query(distinct(StudentRecord.subject)).all() if r[0]]
    classes = [r[0] for r in db.session.query(distinct(StudentRecord.class_name)).all() if r[0]]

    return {
        "subjects": sorted(subjects),
        "classes": sorted(classes),
    }


def get_batch_with_preview(batch_id, limit=10):
    """Return a batch and a preview of its first N records."""
    batch = UploadBatch.query.get(batch_id)
    if not batch:
        return None, []
    preview = (
        StudentRecord.query
        .filter_by(batch_id=batch_id)
        .limit(limit)
        .all()
    )
    return batch, [r.to_dict() for r in preview]


def get_record_count():
    """Total records currently in the DB."""
    return StudentRecord.query.count()
