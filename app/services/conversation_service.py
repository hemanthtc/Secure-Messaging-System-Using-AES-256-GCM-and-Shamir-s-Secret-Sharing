"""
Conversation Service Module
Manages direct chat conversations between users.
"""

from typing import Tuple, Optional, List
from app.models.conversation import Conversation
from app.models.user import User

class ConversationService:
    """Service for conversation lifecycle and retrieval."""

    @staticmethod
    def get_or_create_direct_chat(current_user: User, target_public_id: str) -> Tuple[Optional[Conversation], Optional[str]]:
        """Start or retrieve an active 1-on-1 direct conversation with target user."""
        target_user = User.find_by_public_id(target_public_id)
        if not target_user:
            return None, f"User '{target_public_id}' not found."

        if target_user.internal_id == current_user.internal_id:
            return None, "You cannot initiate a direct conversation with yourself."

        conv = Conversation.get_or_create(current_user.internal_id, target_user.internal_id)
        return conv, None

    @staticmethod
    def list_conversations(current_user: User) -> List[dict]:
        """List all active conversations for the user with peer details and latest message."""
        convs = Conversation.find_for_user(current_user.internal_id)
        return [c.to_dict(current_user_id=current_user.internal_id) for c in convs]

    @staticmethod
    def get_conversation_for_user(conversation_id: str, current_user: User) -> Optional[Conversation]:
        """Retrieve conversation ensuring current user is an authorized participant."""
        conv = Conversation.find_by_id(conversation_id)
        if not conv or current_user.internal_id not in conv.participants:
            return None
        return conv
