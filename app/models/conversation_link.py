"""
ConversationLink Model Definition for MongoDB Atlas
Stores shareable navigation links for conversations.
"""

from datetime import datetime, timezone
import secrets
from app.database.db import mongo

class ConversationLink:
    """Shareable conversation link token for direct chat navigation."""

    def __init__(self, data):
        self._data = data or {}

    @property
    def id(self):
        return str(self._data.get("_id", ""))

    @property
    def token(self):
        return self._data.get("token")

    @property
    def conversation_id(self):
        return self._data.get("conversation_id")

    @property
    def created_by_id(self):
        return self._data.get("created_by_id")

    @property
    def is_active(self):
        return bool(self._data.get("is_active", True))

    @property
    def created_at(self):
        return self._data.get("created_at")

    def to_dict(self):
        created_at_val = self.created_at
        return {
            "token": self.token,
            "conversation_id": self.conversation_id,
            "created_by_id": self.created_by_id,
            "is_active": self.is_active,
            "created_at": created_at_val.isoformat() if isinstance(created_at_val, datetime) else created_at_val,
        }

    @classmethod
    def create(cls, conversation_id, created_by_id):
        """Create and store a shareable conversation token."""
        token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        doc = {
            "token": token,
            "conversation_id": conversation_id,
            "created_by_id": created_by_id,
            "is_active": True,
            "created_at": now,
        }
        mongo.conversation_links.insert_one(doc)
        return cls(doc)

    @classmethod
    def find_by_token(cls, token):
        """Find active conversation link by token."""
        if not token:
            return None
        doc = mongo.conversation_links.find_one({"token": token, "is_active": True})
        return cls(doc) if doc else None

    @classmethod
    def find_for_conversation(cls, conversation_id):
        """Find existing active link for a conversation."""
        doc = mongo.conversation_links.find_one({"conversation_id": conversation_id, "is_active": True})
        return cls(doc) if doc else None

    def __repr__(self):
        return f"<ConversationLink token='{self.token}' conv_id='{self.conversation_id}'>"
