"""
Authentication Blueprint - Day 11
Handles user registration, login, logout, and user management.
"""
from flask import Blueprint, jsonify, request, render_template, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User

auth_bp = Blueprint("auth", __name__)


# ── Pages ─────────────────────────────────────────────────────────────────────

@auth_bp.route("/login")
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    return render_template("login.html")


@auth_bp.route("/register")
def register_page():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    return render_template("register.html")


@auth_bp.route("/logout")
def logout_page():
    if current_user.is_authenticated:
        logout_user()
    return redirect(url_for("main.index"))


# ── API Auth endpoints ────────────────────────────────────────────────────────

@auth_bp.route("/api/login", methods=["POST"])
def api_login():
    """Login with username/email + password. Returns user info on success."""
    data     = request.get_json()
    login_id = data.get("username", "").strip()
    password = data.get("password", "")

    if not login_id or not password:
        return jsonify({"error": "Username and password are required."}), 400

    # Accept either username or email
    user = User.query.filter(
        (User.username == login_id) | (User.email == login_id)
    ).first()

    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid username or password."}), 401

    if not user.is_active:
        return jsonify({"error": "Account is deactivated. Contact admin."}), 403

    login_user(user, remember=data.get("remember", False))
    return jsonify({
        "message": f"Welcome back, {user.username}!",
        "user": user.to_dict(),
    }), 200


@auth_bp.route("/api/register", methods=["POST"])
def api_register():
    """Register a new teacher account."""
    data     = request.get_json()
    username = data.get("username", "").strip()
    email    = data.get("email", "").strip().lower()
    password = data.get("password", "")

    # Validation
    if not username or not email or not password:
        return jsonify({"error": "Username, email, and password are all required."}), 400
    if len(username) < 3:
        return jsonify({"error": "Username must be at least 3 characters."}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400
    if "@" not in email:
        return jsonify({"error": "Please enter a valid email address."}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already taken. Please choose another."}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "An account with this email already exists."}), 409

    user = User(username=username, email=email, role="teacher")
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    login_user(user)
    return jsonify({
        "message": f"Account created! Welcome, {username}.",
        "user": user.to_dict(),
    }), 201


@auth_bp.route("/api/logout", methods=["POST"])
@login_required
def api_logout():
    username = current_user.username
    logout_user()
    return jsonify({"message": f"Goodbye, {username}!"}), 200


@auth_bp.route("/api/me")
def api_me():
    """Return current user info (or guest status if not logged in)."""
    if current_user.is_authenticated:
        return jsonify({"authenticated": True, "user": current_user.to_dict()}), 200
    return jsonify({"authenticated": False, "user": None}), 200


@auth_bp.route("/api/users")
@login_required
def api_list_users():
    """Admin only — list all users."""
    if current_user.role != "admin":
        return jsonify({"error": "Admin access required."}), 403
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify([u.to_dict() for u in users]), 200


@auth_bp.route("/api/users/<int:user_id>/toggle", methods=["POST"])
@login_required
def api_toggle_user(user_id):
    """Admin only — activate/deactivate a user."""
    if current_user.role != "admin":
        return jsonify({"error": "Admin access required."}), 403
    if current_user.id == user_id:
        return jsonify({"error": "You cannot deactivate your own account."}), 400

    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    status = "activated" if user.is_active else "deactivated"
    return jsonify({"message": f"User {user.username} {status}.", "user": user.to_dict()}), 200


@auth_bp.route("/api/users/<int:user_id>/role", methods=["POST"])
@login_required
def api_change_role(user_id):
    """Admin only — change a user's role."""
    if current_user.role != "admin":
        return jsonify({"error": "Admin access required."}), 403

    user = User.query.get_or_404(user_id)
    data = request.get_json()
    new_role = data.get("role")

    if new_role not in ("admin", "teacher"):
        return jsonify({"error": "Role must be 'admin' or 'teacher'."}), 400
    if current_user.id == user_id and new_role != "admin":
        return jsonify({"error": "You cannot remove your own admin role."}), 400

    user.role = new_role
    db.session.commit()
    return jsonify({"message": f"{user.username} is now {new_role}.", "user": user.to_dict()}), 200


@auth_bp.route("/api/change-password", methods=["POST"])
@login_required
def api_change_password():
    """Change current user's password."""
    data         = request.get_json()
    old_password = data.get("old_password", "")
    new_password = data.get("new_password", "")

    if not current_user.check_password(old_password):
        return jsonify({"error": "Current password is incorrect."}), 401
    if len(new_password) < 6:
        return jsonify({"error": "New password must be at least 6 characters."}), 400

    current_user.set_password(new_password)
    db.session.commit()
    return jsonify({"message": "Password changed successfully."}), 200
