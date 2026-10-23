"""
Profile Routes Module
Handles viewing and updating user profiles.
Ensures editing public user ID preserves permanent internal relationships.
"""

from flask import Blueprint, render_template, request, jsonify
from app.security.session_security import login_required, get_current_user
from app.services.profile_service import ProfileService

profile_bp = Blueprint("profile", __name__)

@profile_bp.route("/profile", methods=["GET"])
@login_required
def profile_view():
    """Render profile management page."""
    current_user = get_current_user()
    return render_template("profile.html", user=current_user)

@profile_bp.route("/api/profile", methods=["GET"])
@login_required
def get_profile_api():
    """Get current user's profile details."""
    current_user = get_current_user()
    return jsonify({"success": True, "user": current_user.to_dict()})

@profile_bp.route("/api/profile", methods=["PUT", "POST"])
@login_required
def update_profile_api():
    """Update display name and/or public user ID."""
    current_user = get_current_user()
    data = request.get_json() or {}
    display_name = data.get("display_name")
    public_user_id = data.get("public_user_id")

    success, err = ProfileService.update_profile(
        user=current_user,
        display_name=display_name,
        public_user_id=public_user_id
    )

    if not success:
        return jsonify({"success": False, "error": err}), 400

    return jsonify({"success": True, "user": current_user.to_dict()})
