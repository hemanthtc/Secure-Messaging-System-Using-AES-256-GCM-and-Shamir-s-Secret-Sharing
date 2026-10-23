"""
Authentication Routes Module
Provides endpoints for user registration, login, logout, and auth status verification.
Enforces 3-credential login (Name, Public User ID, Password) with rate limiting.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from app.services.auth_service import AuthService
from app.security.session_security import login_user, logout_user, get_current_user
from app.security.rate_limiting import rate_limit

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/signup", methods=["GET", "POST"])
def signup_view():
    """User registration page and submission handler."""
    current_user = get_current_user()
    if current_user:
        return redirect(url_for("chat.chat_view"))

    if request.method == "POST":
        data = request.form if request.form else (request.get_json() or {})
        display_name = data.get("display_name", "")
        public_user_id = data.get("public_user_id", "")
        password = data.get("password", "")

        user, err = AuthService.register_user(
            display_name=display_name,
            public_user_id=public_user_id,
            password=password
        )

        if err:
            if request.is_json:
                return jsonify({"error": err, "success": False}), 400
            flash(err, "error")
            return render_template("signup.html", display_name=display_name, public_user_id=public_user_id)

        # Automatically log in the user upon successful registration
        login_user(user)
        if request.is_json:
            return jsonify({"success": True, "user": user.to_dict()}), 201
        return redirect(url_for("chat.chat_view"))

    return render_template("signup.html")

@auth_bp.route("/login", methods=["GET", "POST"])
@rate_limit(max_attempts=10, window_seconds=60)
def login_view():
    """User login page and submission handler requiring Name, Public User ID, and Password."""
    current_user = get_current_user()
    if current_user:
        return redirect(url_for("chat.chat_view"))

    if request.method == "POST":
        data = request.form if request.form else (request.get_json() or {})
        display_name = data.get("display_name", "")
        public_user_id = data.get("public_user_id", "")
        password = data.get("password", "")

        user, err = AuthService.authenticate_user(
            display_name=display_name,
            public_user_id=public_user_id,
            password=password
        )

        if err:
            if request.is_json:
                return jsonify({"error": err, "success": False}), 401
            flash(err, "error")
            return render_template("login.html", display_name=display_name, public_user_id=public_user_id)

        login_user(user)
        if request.is_json:
            return jsonify({"success": True, "user": user.to_dict()}), 200
        return redirect(url_for("chat.chat_view"))

    return render_template("login.html")

@auth_bp.route("/logout", methods=["GET", "POST"])
def logout_view():
    """Logout endpoint clearing the active session."""
    logout_user()
    if request.is_json:
        return jsonify({"success": True, "message": "Logged out successfully."})
    return redirect(url_for("auth.login_view"))

@auth_bp.route("/api/auth/me", methods=["GET"])
def current_user_api():
    """Check current authenticated session status."""
    current_user = get_current_user()
    if not current_user:
        return jsonify({"authenticated": False, "user": None}), 200
    return jsonify({"authenticated": True, "user": current_user.to_dict()}), 200
