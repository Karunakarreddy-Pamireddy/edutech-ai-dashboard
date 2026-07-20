import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_login import LoginManager

db           = SQLAlchemy()
login_manager = LoginManager()


def create_app():
    app = Flask(__name__)

    # ── CORS ─────────────────────────────────────────────────────────────────
    CORS(app, resources={r"/api/*": {"origins": "*"}},
         supports_credentials=True)

    # ── Database ──────────────────────────────────────────────────────────────
    basedir      = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    is_production= os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RENDER")
    db_path      = "/tmp/edutech.db" if is_production else os.path.join(basedir, "data", "edutech.db")

    app.config["SQLALCHEMY_DATABASE_URI"]    = "sqlite:///" + db_path
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"]                 = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
    app.config["MAX_CONTENT_LENGTH"]         = 10 * 1024 * 1024

    # ── Extensions ────────────────────────────────────────────────────────────
    db.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = "auth.login_page"

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))

    # ── Blueprints ────────────────────────────────────────────────────────────
    from app.routes import main_bp
    from app.auth  import auth_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")

    # ── DB init ───────────────────────────────────────────────────────────────
    with app.app_context():
        db.create_all()
        _create_default_admin()
        if is_production:
            _seed_if_empty(basedir)

    return app


def _create_default_admin():
    """Create a default admin account on first run."""
    from app.models import User
    if User.query.count() == 0:
        default_pass = os.environ.get("ADMIN_DEFAULT_PASSWORD", "AdminPass2026!")
        admin = User(
            username="admin",
            email="admin@edutech.com",
            role="admin"
        )
        admin.set_password(default_pass)
        db.session.add(admin)
        db.session.commit()


def _seed_if_empty(basedir):
    """Auto-load sample data on first production deploy."""
    from app.models import StudentRecord
    if StudentRecord.query.count() == 0:
        sample_path = os.path.join(basedir, "data", "sample_student_data_1000.csv")
        if os.path.exists(sample_path):
            try:
                import pandas as pd
                from app.data_processing import validate_and_clean
                from app.models import UploadBatch
                df     = pd.read_csv(sample_path)
                result = validate_and_clean(df)
                if result.valid_count > 0:
                    batch = UploadBatch(filename="sample_student_data_1000.csv",
                                        row_count=result.valid_count, status="success")
                    db.session.add(batch)
                    db.session.flush()
                    for row in result.valid_rows:
                        db.session.add(StudentRecord(batch_id=batch.id, **row))
                    db.session.commit()
                    print(f"[SEED] Loaded {result.valid_count} sample records.")
            except Exception as e:
                print(f"[SEED] Error: {e}")
