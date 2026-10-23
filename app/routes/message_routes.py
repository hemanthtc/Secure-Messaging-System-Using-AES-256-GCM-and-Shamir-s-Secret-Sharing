"""
Message Routes Module
Handles sending encrypted messages with configurable fragmentation (2-10 parts),
optional Shamir's Secret Sharing, and payload reassembly upon arrival.
"""

from flask import Blueprint, request, jsonify, send_file
from app.security.session_security import login_required, get_current_user
from app.services.message_service import MessageService
from app.services.delivery_service import DeliveryService
from app.services.image_service import ImageService
from app.models.conversation import Conversation
from app import socketio

message_bp = Blueprint("messages", __name__)

@message_bp.route("/api/messages/send", methods=["POST"])
@login_required
def send_message_api():
    """
    Send an encrypted message.
    Payload is divided into N fragments according to user's protocol settings (Automatic or Custom).
    Sender identity derived strictly from session.
    """
    current_user = get_current_user()
    data = request.get_json() or {}

    conversation_id = data.get("conversation_id")
    content = data.get("content", "")
    fragment_count = data.get("fragment_count")
    is_sss_enabled = data.get("is_sss_enabled")
    sss_threshold_k = data.get("sss_threshold_k")
    sss_total_shares_m = data.get("sss_total_shares_m")
    message_type = data.get("message_type", "text")
    image_id = data.get("image_id")
    image_filename = data.get("image_filename")

    msg_data, err = MessageService.send_message(
        conversation_id=conversation_id,
        sender=current_user,
        content=content,
        fragment_count=fragment_count,
        is_sss_enabled=is_sss_enabled,
        sss_threshold_k=sss_threshold_k,
        sss_total_shares_m=sss_total_shares_m,
        message_type=message_type,
        image_id=image_id,
        image_filename=image_filename
    )

    if err:
        return jsonify({"success": False, "error": err}), 400

    # Real-time broadcast
    if socketio:
        socketio.emit("new_message", msg_data, room=f"conv_{conversation_id}")
        conv = Conversation.find_by_id(conversation_id)
        if conv:
            for pid in conv.participants:
                socketio.emit("conversation_updated", {
                    "conversation_id": conversation_id,
                    "last_message": {
                        "message_uuid": msg_data["message_uuid"],
                        "created_at": msg_data["created_at"],
                        "message_type": msg_data.get("message_type", "text"),
                        "status": msg_data.get("status", "reassembled")
                    }
                }, room=f"user_{pid}")

    return jsonify({"success": True, "message": msg_data}), 201

@message_bp.route("/api/messages/conversation/<conversation_id>", methods=["GET"])
@login_required
def get_conversation_messages_api(conversation_id):
    """Retrieve messages for a conversation, performing reassembly and decryption where all fragments are present."""
    current_user = get_current_user()
    messages = MessageService.get_conversation_messages(conversation_id, current_user)
    return jsonify({"success": True, "messages": messages})

@message_bp.route("/api/messages/conversation/<conversation_id>/read", methods=["POST"])
@login_required
def mark_messages_read_api(conversation_id):
    """Mark incoming messages in conversation as read and notify sender in real-time."""
    current_user = get_current_user()
    read_uuids = MessageService.mark_conversation_as_read(conversation_id, current_user)
    
    if read_uuids and socketio:
        socketio.emit("messages_read", {
            "conversation_id": conversation_id,
            "read_uuids": read_uuids,
            "read_by_id": current_user.internal_id
        }, room=f"conv_{conversation_id}")

    return jsonify({"success": True, "read_uuids": read_uuids})

@message_bp.route("/api/messages/image/upload", methods=["POST"])
@login_required
def upload_image_api():
    """
    Upload an image for a conversation.
    Validates file type, size (up to 5MB), persists safely, and dispatches message.
    """
    current_user = get_current_user()
    conversation_id = request.form.get("conversation_id")
    if not conversation_id:
        return jsonify({"success": False, "error": "Missing conversation_id."}), 400

    if "image" not in request.files:
        return jsonify({"success": False, "error": "No image file provided."}), 400

    file_obj = request.files["image"]
    if not file_obj or file_obj.filename == "":
        return jsonify({"success": False, "error": "Empty or missing file."}), 400

    raw_bytes = file_obj.read()
    saved_meta, err = ImageService.save_image(
        raw_bytes=raw_bytes,
        original_filename=file_obj.filename,
        conversation_id=conversation_id,
        uploader=current_user
    )

    if err:
        return jsonify({"success": False, "error": err}), 400

    # Create message referencing image
    msg_data, msg_err = MessageService.send_message(
        conversation_id=conversation_id,
        sender=current_user,
        content=f"[Image: {saved_meta['original_filename']}]",
        message_type="image",
        image_id=saved_meta["image_id"],
        image_filename=saved_meta["original_filename"]
    )

    if msg_err:
        return jsonify({"success": False, "error": msg_err}), 400

    if socketio:
        socketio.emit("new_message", msg_data, room=f"conv_{conversation_id}")
        conv = Conversation.find_by_id(conversation_id)
        if conv:
            for pid in conv.participants:
                socketio.emit("conversation_updated", {
                    "conversation_id": conversation_id,
                    "last_message": {
                        "message_uuid": msg_data["message_uuid"],
                        "created_at": msg_data["created_at"],
                        "message_type": "image",
                        "status": msg_data.get("status", "reassembled")
                    }
                }, room=f"user_{pid}")

    return jsonify({"success": True, "message": msg_data, "image": saved_meta}), 201

@message_bp.route("/api/messages/images/<image_id>", methods=["GET"])
@login_required
def get_image_api(image_id):
    """
    Retrieve and stream image file.
    Enforces participant authorization and 7-day retention expiry.
    """
    current_user = get_current_user()
    file_path, mime_type, err = ImageService.get_authorized_image(image_id, current_user)
    if err:
        return jsonify({"success": False, "error": err}), 403

    as_download = request.args.get("download", "false").lower() in ("true", "1")
    return send_file(
        str(file_path),
        mimetype=mime_type,
        as_attachment=as_download,
        download_name=file_path.name if as_download else None
    )

@message_bp.route("/api/messages/<message_uuid>/reassemble", methods=["POST", "GET"])
@login_required
def reassemble_message_api(message_uuid):
    """Retrieve and reassemble a specific message, decrypting only if 100% fragments are verified."""
    current_user = get_current_user()
    data = request.get_json() if request.is_json else {}
    provided_shares = data.get("shares") if data else None

    result, err = MessageService.get_and_reassemble_message(
        message_uuid=message_uuid,
        requesting_user=current_user,
        provided_shares=provided_shares
    )

    if err:
        return jsonify({"success": False, "error": err}), 400

    return jsonify({"success": True, "message": result})

@message_bp.route("/api/messages/fragment", methods=["POST"])
@login_required
def receive_fragment_api():
    """
    Deliver an individual fragment packet incrementally.
    Supports out-of-order delivery testing and duplicate verification.
    """
    data = request.get_json() or {}
    message_uuid = data.get("message_uuid")
    fragment_index = data.get("fragment_index")
    total_fragments = data.get("total_fragments")
    payload_b64 = data.get("payload") or data.get("payload_b64")
    payload_hash = data.get("payload_hash")

    result, err = DeliveryService.receive_fragment_packet(
        message_uuid=message_uuid,
        fragment_index=fragment_index,
        total_fragments=total_fragments,
        payload_b64=payload_b64,
        payload_hash=payload_hash
    )

    if err:
        return jsonify({"success": False, "error": err}), 400

    return jsonify({"success": True, "status": result})

@message_bp.route("/api/messages/<message_uuid>", methods=["DELETE"])
@login_required
def delete_message_api(message_uuid):
    """
    Delete a specific message.
    - If mode is 'for_me' (or if a recipient is deleting):
      Deletes ONLY from the requesting user's view and account data.
      The message remains visible, downloadable, and intact for the other participant.
      When all conversation participants delete it for themselves, it cascades to hard deletion.
    - If mode is 'for_everyone' (or sender default without mode):
      Allowed only for sender. Hard-deletes message, files, and broadcasts removal to both participants.
    """
    from app.models.message import Message
    current_user = get_current_user()
    msg = Message.find_by_uuid(message_uuid)
    if not msg:
        return jsonify({"success": False, "error": "Message not found."}), 404

    conv = Conversation.find_by_id(msg.conversation_id)
    if not conv or current_user.internal_id not in conv.participants:
        return jsonify({"success": False, "error": "Unauthorized to delete this message."}), 403

    conversation_id = msg.conversation_id
    is_sender = (msg.sender_id == current_user.internal_id)

    # Determine requested deletion scope:
    mode = request.args.get("mode")
    if not mode and request.is_json:
        mode = (request.get_json(silent=True) or {}).get("mode")

    if not is_sender:
        # A recipient can ONLY delete for themselves (Delete for Me)
        delete_scope = "for_me"
    else:
        # Sender can choose: default to for_everyone unless for_me is specified
        if mode == "for_me":
            delete_scope = "for_me"
        else:
            delete_scope = "for_everyone"

    if delete_scope == "for_me":
        # Record deletion for current user only
        msg.mark_deleted_for_user(current_user.internal_id)

        # If all participants have now deleted this message, cascade to permanent deletion
        if msg.is_deleted_for_all(conv.participants):
            msg.delete()

        # Real-time event: notify ONLY the deleting user's client room
        if socketio:
            socketio.emit("message_deleted", {
                "conversation_id": conversation_id,
                "message_uuid": message_uuid,
                "mode": "for_me",
                "deleted_by": current_user.internal_id
            }, room=f"user_{current_user.internal_id}")
            socketio.emit("conversation_updated", {
                "conversation_id": conversation_id
            }, room=f"user_{current_user.internal_id}")

        return jsonify({
            "success": True,
            "message_uuid": message_uuid,
            "mode": "for_me"
        })
    else:
        # Hard delete for everyone across all participants (sender only)
        msg.delete()
        if socketio:
            socketio.emit("message_deleted", {
                "conversation_id": conversation_id,
                "message_uuid": message_uuid,
                "mode": "for_everyone",
                "deleted_by": current_user.internal_id
            }, room=f"conv_{conversation_id}")
            for pid in conv.participants:
                socketio.emit("conversation_updated", {
                    "conversation_id": conversation_id
                }, room=f"user_{pid}")

        return jsonify({
            "success": True,
            "message_uuid": message_uuid,
            "mode": "for_everyone"
        })
