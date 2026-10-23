"""
Chat and Conversation Routes Module
Provides WhatsApp-style chat view and conversation retrieval endpoints.
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from app.security.session_security import login_required, get_current_user
from app.services.conversation_service import ConversationService

chat_bp = Blueprint("chat", __name__)

@chat_bp.route("/")
def index():
    """Root route redirecting authenticated users to chat or visitors to login."""
    current_user = get_current_user()
    if current_user:
        return redirect(url_for("chat.chat_view"))
    return redirect(url_for("auth.login_view"))

@chat_bp.route("/chat", methods=["GET"])
@login_required
def chat_view():
    """Main WhatsApp-style chat application interface."""
    current_user = get_current_user()
    return render_template("chat.html", user=current_user)

@chat_bp.route("/api/conversations", methods=["GET"])
@login_required
def list_conversations_api():
    """List all active conversations for the current user."""
    current_user = get_current_user()
    conversations = ConversationService.list_conversations(current_user)
    return jsonify({"success": True, "conversations": conversations})

@chat_bp.route("/api/conversations/direct", methods=["POST"])
@login_required
def create_or_open_direct_chat_api():
    """Start or open a direct 1-on-1 chat with target user by public ID."""
    current_user = get_current_user()
    data = request.get_json() or {}
    target_public_id = data.get("target_public_id", "")

    conv, err = ConversationService.get_or_create_direct_chat(current_user, target_public_id)
    if err:
        return jsonify({"success": False, "error": err}), 400

    return jsonify({"success": True, "conversation": conv.to_dict(current_user_id=current_user.internal_id)})
