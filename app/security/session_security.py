"""
Session Security and Authentication Helpers
Manages secure authenticated sessions and enforces login requirements.
"""

from functools import wraps
from flask import session, redirect, url_for, request, jsonify
from app.models.user import User

def login_user(user: User):
    """Establish an authenticated session bound to the user's permanent internal ID."""
    session.clear()
    session["user_internal_id"] = user.internal_id
    session.permanent = True

def logout_user():
    """Clear session data and invalidate authenticated state."""
    session.clear()

def get_current_user():
    """Retrieve the currently authenticated User instance from the active session."""
    internal_id = session.get("user_internal_id")
    if not internal_id:
        return None
    return User.find_by_internal_id(internal_id)

def login_required(f):
    """Decorator requiring an authenticated user for route access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        current_user = get_current_user()
        if not current_user or not current_user.is_active:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required", "authenticated": False}), 401
            return redirect(url_for("auth.login_view"))
        return f(*args, **kwargs)
    return decorated_function
