from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


class UploadBatch(db.Model):
    """Tracks each file upload so records can be traced/deleted by batch."""
    __tablename__ = "upload_batches"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    row_count = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default="success")  # success | partial | failed

    records = db.relationship(
        "StudentRecord", backref="batch", cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "uploaded_at": self.uploaded_at.isoformat(),
            "row_count": self.row_count,
            "status": self.status,
        }


class StudentRecord(db.Model):
    """One row = one student's score in one subject on one date."""
    __tablename__ = "student_records"

    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey("upload_batches.id"), nullable=False)

    student_id = db.Column(db.String(50), nullable=False, index=True)
    class_name = db.Column(db.String(50), index=True)
    subject = db.Column(db.String(50), index=True)
    score = db.Column(db.Float, nullable=False)
    ai_tool_used = db.Column(db.Boolean, default=False, index=True)
    study_hours = db.Column(db.Float)
    record_date = db.Column(db.Date, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "class_name": self.class_name,
            "subject": self.subject,
            "score": self.score,
            "ai_tool_used": self.ai_tool_used,
            "study_hours": self.study_hours,
            "record_date": self.record_date.isoformat() if self.record_date else None,
        }


class User(UserMixin, db.Model):
    """User account for multi-user authentication."""
    __tablename__ = "users"

    id           = db.Column(db.Integer, primary_key=True)
    username     = db.Column(db.String(80),  unique=True, nullable=False, index=True)
    email        = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash= db.Column(db.String(255), nullable=False)
    role         = db.Column(db.String(20),  default="teacher")   # admin / teacher
    created_at   = db.Column(db.DateTime,    default=datetime.utcnow)
    is_active    = db.Column(db.Boolean,     default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id":         self.id,
            "username":   self.username,
            "email":      self.email,
            "role":       self.role,
            "created_at": self.created_at.isoformat(),
            "is_active":  self.is_active,
        }
