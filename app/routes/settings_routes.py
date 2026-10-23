"""
Settings and Account Management Routes Module
Provides views and API endpoints for profile edits, appearance themes,
password changes, and explicit permanent account deletion.
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from app.security.session_security import login_required, get_current_user, logout_user
from app.services.account_service import AccountService
from app.services.profile_service import ProfileService

from app.validators.fragment_validator import validate_fragment_count
from app.validators.share_validator import validate_sss_parameters

settings_bp = Blueprint("settings", __name__)

@settings_bp.route("/settings", methods=["GET"])
@login_required
def settings_view():
    """Render settings and account preferences page."""
    current_user = get_current_user()
    return render_template("settings.html", user=current_user)

@settings_bp.route("/api/settings/protocols", methods=["GET"])
@login_required
def get_protocol_settings_api():
    """Retrieve current user's secure protocol settings."""
    current_user = get_current_user()
    return jsonify({"success": True, "protocols": current_user.protocol_settings})

@settings_bp.route("/api/settings/protocols", methods=["PUT", "POST"])
@login_required
def update_protocol_settings_api():
    """Update and validate user's secure protocol settings."""
    current_user = get_current_user()
    data = request.get_json() or {}

    mode = data.get("mode", "custom")
    if mode not in ["automatic", "custom"]:
        return jsonify({"success": False, "error": "Invalid mode. Must be 'automatic' or 'custom'."}), 400

    updated = {
        "mode": mode,
        "fragment_telemetry": bool(data.get("fragment_telemetry", True)),
        "fragment_reassembly_status": bool(data.get("fragment_reassembly_status", True)),
        "private_mode": bool(data.get("private_mode", False)),
    }

    if mode == "custom":
        frag_count = data.get("fragment_count", 3)
        is_valid_frag, parsed_frag, err = validate_fragment_count(frag_count)
        if not is_valid_frag:
            return jsonify({"success": False, "error": f"Invalid fragment count: {err}"}), 400
        updated["fragment_count"] = parsed_frag

        is_sss = bool(data.get("is_sss_enabled", False))
        updated["is_sss_enabled"] = is_sss
        if is_sss:
            k = data.get("sss_threshold_k")
            m = data.get("sss_total_shares_m")
            is_valid_sss, k_val, m_val, sss_err = validate_sss_parameters(k, m)
            if not is_valid_sss:
                return jsonify({"success": False, "error": f"Invalid SSS parameters: {sss_err}"}), 400
            updated["sss_threshold_k"] = k_val
            updated["sss_total_shares_m"] = m_val

    current_user.update_protocol_settings(updated)
    return jsonify({"success": True, "protocols": current_user.protocol_settings})

@settings_bp.route("/api/settings/password", methods=["POST"])
@login_required
def change_password_api():
    """Change account password after confirming current password."""
    current_user = get_current_user()
    data = request.get_json() or {}
    current_pwd = data.get("current_password", "")
    new_pwd = data.get("new_password", "")

    success, err = AccountService.change_password(current_user, current_pwd, new_pwd)
    if not success:
        return jsonify({"success": False, "error": err}), 400

    return jsonify({"success": True, "message": "Password updated successfully."})

@settings_bp.route("/api/settings/account", methods=["DELETE", "POST"])
@login_required
def delete_account_api():
    """
    Permanently delete account with explicit password confirmation.
    Applies hard-deletion cascade policy.
    """
    current_user = get_current_user()
    data = request.get_json() or {}
    confirmation_password = data.get("confirmation_password", "")

    success, err = AccountService.delete_account_permanently(current_user, confirmation_password)
    if not success:
        return jsonify({"success": False, "error": err}), 400

    # Invalidate session
    logout_user()
    return jsonify({"success": True, "message": "Account permanently deleted."})
