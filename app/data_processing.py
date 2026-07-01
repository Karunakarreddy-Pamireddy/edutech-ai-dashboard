"""
Data ingestion layer for Day 2.
Handles parsing uploaded CSV/Excel files into validated StudentRecord rows.
Keeps parsing/validation logic separate from Flask routes so it's
independently testable and reusable by the Day 4-5 pipeline.
"""
from datetime import datetime
import pandas as pd

REQUIRED_COLUMNS = [
    "student_id", "class_name", "subject", "score",
    "ai_tool_used", "study_hours", "record_date",
]

VALID_SUBJECTS_HINT = "any text value is accepted, but keep subject names consistent (e.g. 'Math' not 'math'/'MATH')"

TRUE_STRINGS = {"true", "1", "yes", "y"}
FALSE_STRINGS = {"false", "0", "no", "n"}


class ParseResult:
    def __init__(self):
        self.valid_rows = []      # list[dict] ready to insert
        self.errors = []          # list[dict]: {row, reason}
        self.total_rows = 0

    @property
    def valid_count(self):
        return len(self.valid_rows)

    @property
    def error_count(self):
        return len(self.errors)

    def to_summary(self):
        return {
            "total_rows": self.total_rows,
            "valid_rows": self.valid_count,
            "error_rows": self.error_count,
            "errors": self.errors[:50],  # cap so a giant bad file doesn't flood the response
        }


def read_uploaded_file(file_stream, filename):
    """Read CSV or Excel into a DataFrame. Raises ValueError on unsupported type / unreadable file."""
    lower = filename.lower()
    try:
        if lower.endswith(".csv"):
            df = pd.read_csv(file_stream)
        elif lower.endswith((".xlsx", ".xls")):
            df = pd.read_excel(file_stream)
        else:
            raise ValueError(f"Unsupported file type: '{filename}'. Please upload .csv or .xlsx")
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Could not read file '{filename}': {e}")

    if df.empty:
        raise ValueError("Uploaded file is empty (no rows found).")

    return df


def _parse_bool(value, row_num, errors):
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    if s in TRUE_STRINGS:
        return True
    if s in FALSE_STRINGS:
        return False
    errors.append({"row": row_num, "reason": f"ai_tool_used value '{value}' is not a recognizable true/false"})
    return None


def _parse_date(value, row_num, errors):
    if pd.isna(value):
        errors.append({"row": row_num, "reason": "record_date is missing"})
        return None
    try:
        return pd.to_datetime(value).date()
    except Exception:
        errors.append({"row": row_num, "reason": f"record_date value '{value}' is not a valid date"})
        return None


def _parse_score(value, row_num, errors):
    try:
        score = float(value)
    except (TypeError, ValueError):
        errors.append({"row": row_num, "reason": f"score value '{value}' is not numeric"})
        return None
    if score < 0 or score > 100:
        errors.append({"row": row_num, "reason": f"score value {score} is out of expected 0-100 range"})
        return None
    return score


def _parse_study_hours(value, row_num, errors):
    if pd.isna(value):
        return None  # optional field
    try:
        hours = float(value)
    except (TypeError, ValueError):
        errors.append({"row": row_num, "reason": f"study_hours value '{value}' is not numeric"})
        return None
    if hours < 0:
        errors.append({"row": row_num, "reason": f"study_hours value {hours} cannot be negative"})
        return None
    return hours


def validate_and_clean(df: pd.DataFrame) -> ParseResult:
    """
    Validates structure (required columns) then validates/cleans row by row.
    Bad rows are skipped and logged, not allowed to crash the whole upload.
    """
    result = ParseResult()

    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        raise ValueError(
            f"Missing required column(s): {', '.join(missing_cols)}. "
            f"Expected columns: {', '.join(REQUIRED_COLUMNS)}"
        )

    result.total_rows = len(df)

    for idx, raw in df.iterrows():
        row_num = idx + 2  # +1 for header row, +1 for 1-indexing -> matches spreadsheet row numbers
        row_errors_before = len(result.errors)

        student_id = str(raw["student_id"]).strip() if pd.notna(raw["student_id"]) else None
        if not student_id or student_id.lower() == "nan":
            result.errors.append({"row": row_num, "reason": "student_id is missing"})
            continue

        class_name = str(raw["class_name"]).strip() if pd.notna(raw["class_name"]) else None
        subject = str(raw["subject"]).strip() if pd.notna(raw["subject"]) else None
        if not subject:
            result.errors.append({"row": row_num, "reason": "subject is missing"})
            continue

        score = _parse_score(raw["score"], row_num, result.errors)
        ai_used = _parse_bool(raw["ai_tool_used"], row_num, result.errors)
        study_hours = _parse_study_hours(raw["study_hours"], row_num, result.errors)
        record_date = _parse_date(raw["record_date"], row_num, result.errors)

        # if any required field failed parsing, skip the row (errors already logged above)
        if len(result.errors) > row_errors_before:
            continue
        if score is None or ai_used is None or record_date is None:
            continue

        result.valid_rows.append({
            "student_id": student_id,
            "class_name": class_name,
            "subject": subject,
            "score": score,
            "ai_tool_used": ai_used,
            "study_hours": study_hours,
            "record_date": record_date,
        })

    return result
