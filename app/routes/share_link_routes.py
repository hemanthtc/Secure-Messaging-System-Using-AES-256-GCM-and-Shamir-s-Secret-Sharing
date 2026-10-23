"""
Shareable Links Routes Module
Handles public profile links (/u/<public_user_id>) and conversation navigation links.
Ensures private messages and cryptographic keys are never leaked in URLs.
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from app.models.user import User
from app.security.session_security import get_current_user, login_required
from app.services.conversation_service import ConversationService
from app.services.link_service import LinkService

share_link_bp = Blueprint("share_link", __name__)

@share_link_bp.route("/u/<public_user_id>", methods=["GET"])
def public_profile_link(public_user_id):
    """
    Shareable profile link.
    If authenticated, initiates/opens direct chat with the target user.
    If unauthenticated, renders public profile badge with login/signup actions.
    """
    target_user = User.find_by_public_id(public_user_id)
    if not target_user or not target_user.is_active:
        return render_template("error.html", error_message=f"User '{public_user_id}' not found."), 404

    current_user = get_current_user()
    if current_user:
        if current_user.internal_id == target_user.internal_id:
            return redirect(url_for("profile.profile_view"))
        # Open direct conversation
        conv, _ = ConversationService.get_or_create_direct_chat(current_user, target_user.public_user_id)
        return redirect(url_for("chat.chat_view", conv=conv.conversation_id))

    return render_template("profile.html", user=target_user, is_public_view=True)

@share_link_bp.route("/chat/link/<token>", methods=["GET"])
@login_required
def join_via_conversation_link(token):
    """Resolve an authorized conversation navigation token."""
    current_user = get_current_user()
    conv, err = LinkService.resolve_conversation_link(token, current_user)
    if err:
        return render_template("error.html", error_message=err), 403

    return redirect(url_for("chat.chat_view", conv=conv.conversation_id))

@share_link_bp.route("/api/links/conversation/<conversation_id>", methods=["POST", "GET"])
@login_required
def create_conversation_link_api(conversation_id):
    """Generate or retrieve a shareable link token for a conversation."""
    current_user = get_current_user()
    link_obj, err = LinkService.get_or_create_conversation_link(conversation_id, current_user)
    if err:
        return jsonify({"success": False, "error": err}), 400

    link_url = url_for("share_link.join_via_conversation_link", token=link_obj.token, _external=True)
    return jsonify({
        "success": True,
        "token": link_obj.token,
        "share_url": link_url
    })
