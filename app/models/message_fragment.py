"""
MessageFragment Model Definition for MongoDB Atlas
Stores individual message fragments with index, total count, payload, and SHA-256 hash.
Unique compound index on (message_uuid, fragment_index) enforces uniqueness at the database level.
"""

from datetime import datetime, timezone
from pymongo.errors import DuplicateKeyError
from app.database.db import mongo

class MessageFragment:
    """Represents a discrete indexed fragment of an encrypted message payload."""

    def __init__(self, data):
        self._data = data or {}

    @property
    def id(self):
        return str(self._data.get("_id", ""))

    @property
    def message_uuid(self):
        return self._data.get("message_uuid")

    @property
    def fragment_index(self):
        return int(self._data.get("fragment_index", 1))

    @property
    def total_fragments(self):
        return int(self._data.get("total_fragments", 1))

    @property
    def payload(self):
        return self._data.get("payload", "")

    @property
    def payload_hash(self):
        return self._data.get("payload_hash", "")

    @property
    def received_at(self):
        return self._data.get("received_at")

    def to_dict(self):
        """Serialize fragment metadata."""
        received_at_val = self.received_at
        return {
            "message_uuid": self.message_uuid,
            "fragment_index": self.fragment_index,
            "total_fragments": self.total_fragments,
            "payload": self.payload,
            "payload_hash": self.payload_hash,
            "received_at": received_at_val.isoformat() if isinstance(received_at_val, datetime) else received_at_val,
        }

    @classmethod
    def create(cls, message_uuid, fragment_index, total_fragments, payload, payload_hash):
        """Insert a fragment into MongoDB. Returns (instance, is_duplicate)."""
        now = datetime.now(timezone.utc)
        doc = {
            "message_uuid": message_uuid,
            "fragment_index": int(fragment_index),
            "total_fragments": int(total_fragments),
            "payload": payload,
            "payload_hash": payload_hash,
            "received_at": now,
        }
        try:
            mongo.message_fragments.insert_one(doc)
            return cls(doc), False
        except DuplicateKeyError:
            # Duplicate fragment index rejected by database constraint
            existing = mongo.message_fragments.find_one({
                "message_uuid": message_uuid,
                "fragment_index": int(fragment_index)
            })
            return cls(existing), True

    @classmethod
    def find_by_message_and_index(cls, message_uuid, fragment_index):
        """Retrieve a specific fragment by message UUID and index."""
        doc = mongo.message_fragments.find_one({
            "message_uuid": message_uuid,
            "fragment_index": int(fragment_index)
        })
        return cls(doc) if doc else None

    @classmethod
    def find_all_for_message(cls, message_uuid):
        """Retrieve all fragments for a message, sorted by fragment_index ascending."""
        cursor = mongo.message_fragments.find({"message_uuid": message_uuid}).sort("fragment_index", 1)
        return [cls(doc) for doc in cursor]

    @classmethod
    def count_for_message(cls, message_uuid):
        """Count unique received fragments for a message."""
        return mongo.message_fragments.count_documents({"message_uuid": message_uuid})

    def __repr__(self):
        return f"<MessageFragment msg='{self.message_uuid}' index={self.fragment_index}/{self.total_fragments}>"
