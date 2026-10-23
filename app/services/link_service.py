"""
Link Service Module
Manages shareable profile links and authorized conversation navigation tokens.
Never exposes sensitive keys, passwords, or messages in URLs.
"""

from typing import Tuple, Optional, Dict, Any
from app.models.user import User
from app.models.conversation import Conversation
from app.models.conversation_link import ConversationLink

class LinkService:
    """Service handling profile URLs and conversation share links."""

    @staticmethod
    def get_or_create_conversation_link(conversation_id: str, creator: User) -> Tuple[Optional[ConversationLink], Optional[str]]:
        """Generate or retrieve a shareable navigation link for an authorized conversation."""
        conv = Conversation.find_by_id(conversation_id)
        if not conv or creator.internal_id not in conv.participants:
            return None, "Unauthorized conversation access."

        existing = ConversationLink.find_for_conversation(conversation_id)
        if existing:
            return existing, None

        new_link = ConversationLink.create(conversation_id=conversation_id, created_by_id=creator.internal_id)
        return new_link, None

    @staticmethod
    def resolve_conversation_link(token: str, user: User) -> Tuple[Optional[Conversation], Optional[str]]:
        """Resolve a conversation link token, ensuring user authorization."""
        link_record = ConversationLink.find_by_token(token)
        if not link_record or not link_record.is_active:
            return None, "Conversation link is invalid or expired."

        conv = Conversation.find_by_id(link_record.conversation_id)
        if not conv:
            return None, "Conversation no longer exists."

        # If user is not yet a participant, allow them to join or open the direct chat
        if user.internal_id not in conv.participants:
            # For 1-on-1 conversations, verify if slot is available
            if len(conv.participants) >= 2:
                return None, "This direct conversation already has two participants."
            conv.participants.append(user.internal_id)
            from app.database.db import mongo
            mongo.conversations.update_one(
                {"conversation_id": conv.conversation_id},
                {"$set": {"participants": conv.participants}}
            )

        return conv, None
