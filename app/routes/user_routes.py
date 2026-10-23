"""
User Lookup and Search Routes Module
Allows searching for other users by unique public user ID or name to start conversations.
"""

from flask import Blueprint, request, jsonify
from app.security.session_security import login_required, get_current_user
from app.services.user_service import UserService

user_bp = Blueprint("users", __name__)

@user_bp.route("/api/users/search", methods=["GET"])
@login_required
def search_users_api():
    """Search for users by public_user_id or display_name."""
    query = request.args.get("q", "")
    current_user = get_current_user()
    results = UserService.search_users(query, current_user)
    return jsonify({"success": True, "users": results})

@user_bp.route("/api/users/<public_user_id>", methods=["GET"])
@login_required
def get_user_by_public_id_api(public_user_id):
    """Retrieve public profile information by public ID."""
    user = UserService.get_by_public_id(public_user_id)
    if not user or not user.is_active:
        return jsonify({"success": False, "error": "User not found."}), 404
    return jsonify({"success": True, "user": user.to_dict()})
