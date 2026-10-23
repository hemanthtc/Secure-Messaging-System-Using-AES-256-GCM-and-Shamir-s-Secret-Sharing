"""
MessageShare Model Definition for MongoDB Atlas
Stores Shamir's Secret Sharing key shares associated with a message.
"""

from datetime import datetime, timezone
from pymongo.errors import DuplicateKeyError
from app.database.db import mongo

class MessageShare:
    """Represents a discrete cryptographic share of an encryption key generated via Shamir's scheme."""

    def __init__(self, data):
        self._data = data or {}

    @property
    def id(self):
        return str(self._data.get("_id", ""))

    @property
    def message_uuid(self):
        return self._data.get("message_uuid")

    @property
    def share_index(self):
        return int(self._data.get("share_index", 1))

    @property
    def share_x(self):
        return int(self._data.get("share_x", 1))

    @property
    def share_y(self):
        return str(self._data.get("share_y", ""))

    @property
    def created_at(self):
        return self._data.get("created_at")

    def to_dict(self):
        """Serialize share data."""
        created_at_val = self.created_at
        return {
            "message_uuid": self.message_uuid,
            "share_index": self.share_index,
            "share_x": self.share_x,
            "share_y": self.share_y,
            "created_at": created_at_val.isoformat() if isinstance(created_at_val, datetime) else created_at_val,
        }

    @classmethod
    def create(cls, message_uuid, share_index, share_x, share_y):
        """Insert a key share into MongoDB. Returns (instance, is_duplicate)."""
        now = datetime.now(timezone.utc)
        doc = {
            "message_uuid": message_uuid,
            "share_index": int(share_index),
            "share_x": int(share_x),
            "share_y": str(share_y),
            "created_at": now,
        }
        try:
            mongo.message_shares.insert_one(doc)
            return cls(doc), False
        except DuplicateKeyError:
            existing = mongo.message_shares.find_one({
                "message_uuid": message_uuid,
                "share_index": int(share_index)
            })
            return cls(existing), True

    @classmethod
    def find_all_for_message(cls, message_uuid):
        """Retrieve all shares for a message, sorted by share_index ascending."""
        cursor = mongo.message_shares.find({"message_uuid": message_uuid}).sort("share_index", 1)
        return [cls(doc) for doc in cursor]

    def __repr__(self):
        return f"<MessageShare msg='{self.message_uuid}' index={self.share_index} x={self.share_x}>"
