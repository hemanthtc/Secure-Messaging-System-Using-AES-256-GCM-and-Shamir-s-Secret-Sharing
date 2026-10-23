"""
WebSocket Event Handlers Module
Handles real-time communication events via Flask-SocketIO.
Implements room management, out-of-order fragment delivery, and live presence updates.
"""

from flask import request, session
from flask_socketio import emit, join_room, leave_room
from app.realtime.connection_manager import connection_manager
from app.models.user import User
from app.models.conversation import Conversation
from app.services.message_service import MessageService
from app.services.delivery_service import DeliveryService

def register_socket_events(socketio):
    """Register all Flask-SocketIO event handlers."""

    @socketio.on("connect")
    def handle_connect():
        user_id = session.get("user_internal_id")
        if not user_id:
            # Unauthenticated socket connections are rejected or kept in guest mode
            return False

        user = User.find_by_internal_id(user_id)
        if not user or not user.is_active:
            return False

        connection_manager.register(request.sid, user_id)
        # Join personal user notification room
        join_room(f"user_{user_id}")
        emit("status", {"message": "Connected to SecureShare Messenger real-time service."})

    @socketio.on("disconnect")
    def handle_disconnect():
        user_id = connection_manager.unregister(request.sid)
        if user_id:
            leave_room(f"user_{user_id}")

    @socketio.on("join_conversation")
    def handle_join_conversation(data):
        user_id = session.get("user_internal_id")
        if not user_id:
            emit("error", {"message": "Authentication required."})
            return

        conversation_id = data.get("conversation_id")
        conv = Conversation.find_by_id(conversation_id)
        if not conv or user_id not in conv.participants:
            emit("error", {"message": "Unauthorized conversation access."})
            return

        room_name = f"conv_{conversation_id}"
        join_room(room_name)
        emit("joined_conversation", {"conversation_id": conversation_id}, room=room_name)

    @socketio.on("leave_conversation")
    def handle_leave_conversation(data):
        conversation_id = data.get("conversation_id")
        if conversation_id:
            leave_room(f"conv_{conversation_id}")

    @socketio.on("send_message")
    def handle_send_message(data):
        """Process real-time message submission, fragment delivery, and broadcast."""
        user_id = session.get("user_internal_id")
        if not user_id:
            emit("error", {"message": "Authentication required."})
            return

        user = User.find_by_internal_id(user_id)
        if not user:
            emit("error", {"message": "User not found."})
            return

        conversation_id = data.get("conversation_id")
        content = data.get("content", "")
        fragment_count = data.get("fragment_count", 3)
        is_sss_enabled = data.get("is_sss_enabled", False)
        sss_threshold_k = data.get("sss_threshold_k")
        sss_total_shares_m = data.get("sss_total_shares_m")

        # Process message via message service
        msg_result, err = MessageService.send_message(
            conversation_id=conversation_id,
            sender=user,
            content=content,
            fragment_count=fragment_count,
            is_sss_enabled=is_sss_enabled,
            sss_threshold_k=sss_threshold_k,
            sss_total_shares_m=sss_total_shares_m
        )

        if err:
            emit("send_message_error", {"error": err})
            return

        room_name = f"conv_{conversation_id}"
        
        # Broadcast the new message event with its fragments to the room
        socketio.emit("new_message", msg_result, room=room_name)

        # Notify recipient's private room to update conversation list snippets
        conv = Conversation.find_by_id(conversation_id)
        if conv:
            for pid in conv.participants:
                socketio.emit("conversation_updated", {
                    "conversation_id": conversation_id,
                    "last_message": {
                        "message_uuid": msg_result["message_uuid"],
                        "status": msg_result["status"],
                        "fragment_count": msg_result["fragment_count"],
                        "created_at": msg_result["created_at"],
                    }
                }, room=f"user_{pid}")

    @socketio.on("mark_as_read")
    def handle_mark_as_read(data):
        user_id = session.get("user_internal_id")
        if not user_id:
            return
        user = User.find_by_internal_id(user_id)
        if not user:
            return
        conversation_id = data.get("conversation_id")
        if conversation_id:
            read_uuids = MessageService.mark_conversation_as_read(conversation_id, user)
            if read_uuids:
                socketio.emit("messages_read", {
                    "conversation_id": conversation_id,
                    "read_uuids": read_uuids,
                    "read_by_id": user.internal_id
                }, room=f"conv_{conversation_id}")
