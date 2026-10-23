"""
Authorization Security Module
Verifies user authorization for conversation access, message queries, and profile modifications.
Never trusts sender or user IDs supplied only in frontend request payloads.
"""

from app.models.conversation import Conversation
from app.models.user import User

def authorize_conversation_access(user: User, conversation_id: str) -> bool:
    """Ensure user is an active participant in the requested conversation."""
    if not user or not conversation_id:
        return False
    conversation = Conversation.find_by_id(conversation_id)
    if not conversation:
        return False
    return user.internal_id in conversation.participants

def get_authorized_conversation(user: User, conversation_id: str):
    """Retrieve conversation object if and only if the user is an authorized participant."""
    if not authorize_conversation_access(user, conversation_id):
        return None
    return Conversation.find_by_id(conversation_id)
