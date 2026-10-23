"""
Conversation Model Definition for MongoDB Atlas
Manages direct chat threads between participants.
"""

from datetime import datetime, timezone
import uuid
from app.database.db import mongo
from app.models.user import User

class Conversation:
    """Conversation entity linking participants and messages in MongoDB."""

    def __init__(self, data):
        self._data = data or {}

    @property
    def id(self):
        return self._data.get("conversation_id")

    @property
    def conversation_id(self):
        return self._data.get("conversation_id")

    @property
    def participants(self):
        return self._data.get("participants", [])

    @property
    def created_at(self):
        return self._data.get("created_at")

    @property
    def updated_at(self):
        return self._data.get("updated_at")

    def get_other_participant(self, current_user_id):
        """Retrieve peer user in a direct 1-on-1 conversation."""
        for uid in self.participants:
            if uid != current_user_id:
                return User.find_by_internal_id(uid)
        return None

    def to_dict(self, current_user_id=None):
        """Serialize conversation details including peer contact information and last message snippet."""
        peer = self.get_other_participant(current_user_id) if current_user_id else None
        
        # Retrieve latest message for this conversation (excluding messages deleted for current_user_id)
        msg_query = {"conversation_id": self.conversation_id}
        if current_user_id:
            msg_query["deleted_for"] = {"$ne": current_user_id}
        last_msg_doc = mongo.messages.find_one(
            msg_query,
            sort=[("created_at", -1)]
        )

        last_message = None
        if last_msg_doc:
            created_at_val = last_msg_doc.get("created_at")
            last_message = {
                "message_uuid": last_msg_doc.get("message_uuid"),
                "status": last_msg_doc.get("status"),
                "fragment_count": last_msg_doc.get("fragment_count"),
                "created_at": created_at_val.isoformat() if isinstance(created_at_val, datetime) else created_at_val,
            }

        created_at_val = self.created_at
        updated_at_val = self.updated_at
        return {
            "id": self.conversation_id,
            "conversation_id": self.conversation_id,
            "participants": self.participants,
            "created_at": created_at_val.isoformat() if isinstance(created_at_val, datetime) else created_at_val,
            "updated_at": updated_at_val.isoformat() if isinstance(updated_at_val, datetime) else updated_at_val,
            "peer": peer.to_dict() if peer else None,
            "last_message": last_message,
        }

    @classmethod
    def get_or_create(cls, user1_id, user2_id):
        """Find existing conversation between two participants or create a new one."""
        # Find conversation containing both participants
        doc = mongo.conversations.find_one({
            "participants": {"$all": [user1_id, user2_id], "$size": 2}
        })
        if doc:
            return cls(doc)

        now = datetime.now(timezone.utc)
        conv_id = str(uuid.uuid4())
        new_doc = {
            "conversation_id": conv_id,
            "participants": [user1_id, user2_id],
            "created_at": now,
            "updated_at": now,
        }
        mongo.conversations.insert_one(new_doc)
        return cls(new_doc)

    @classmethod
    def find_by_id(cls, conversation_id):
        """Find conversation by unique string ID."""
        if not conversation_id:
            return None
        doc = mongo.conversations.find_one({"conversation_id": conversation_id})
        return cls(doc) if doc else None

    @classmethod
    def find_for_user(cls, user_id):
        """Retrieve all conversations in which the user participates, sorted by recent activity."""
        cursor = mongo.conversations.find({"participants": user_id}).sort("updated_at", -1)
        return [cls(doc) for doc in cursor]

    def update_timestamp(self):
        """Touch the updated_at timestamp when new messages arrive."""
        now = datetime.now(timezone.utc)
        self._data["updated_at"] = now
        mongo.conversations.update_one(
            {"conversation_id": self.conversation_id},
            {"$set": {"updated_at": now}}
        )

    def delete(self):
        """Delete conversation and all its messages, fragments, and shares."""
        # Find all message uuids
        msg_cursor = mongo.messages.find({"conversation_id": self.conversation_id}, {"message_uuid": 1})
        uuids = [m["message_uuid"] for m in msg_cursor]
        if uuids:
            mongo.message_fragments.delete_many({"message_uuid": {"$in": uuids}})
            mongo.message_shares.delete_many({"message_uuid": {"$in": uuids}})
            mongo.messages.delete_many({"message_uuid": {"$in": uuids}})

        mongo.conversation_links.delete_many({"conversation_id": self.conversation_id})
        mongo.conversations.delete_one({"conversation_id": self.conversation_id})

    def __repr__(self):
        return f"<Conversation id='{self.conversation_id}' participants={self.participants}>"
