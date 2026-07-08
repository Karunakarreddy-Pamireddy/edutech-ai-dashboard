import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app():
    app = Flask(__name__)

    basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    elif os.environ.get("VERCEL") == "1":
        import shutil
        src_db = os.path.join(basedir, "data", "edutech.db")
        dest_db = "/tmp/edutech.db"
        os.makedirs(os.path.dirname(dest_db), exist_ok=True)
        if not os.path.exists(dest_db) and os.path.exists(src_db):
            shutil.copy(src_db, dest_db)
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + dest_db
    else:
        app.config["SQLALCHEMY_DATABASE_URI"] = (
            "sqlite:///" + os.path.join(basedir, "data", "edutech.db")
        )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10MB upload limit

    db.init_app(app)

    from app.routes import main_bp
    app.register_blueprint(main_bp)

    with app.app_context():
        db.create_all()

    return app
