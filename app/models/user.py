"""
User Model Definition for MongoDB Atlas
Stores user credentials and profile information with separation between
permanent internal ID and editable public user ID.
"""

from datetime import datetime, timezone
import uuid
from app.database.db import mongo

class User:
    """User entity model wrapping MongoDB documents."""

    def __init__(self, data):
        self._data = data or {}

    @property
    def id(self):
        """Permanent internal ID."""
        return self._data.get("internal_id")

    @property
    def internal_id(self):
        return self._data.get("internal_id")

    @property
    def public_user_id(self):
        return self._data.get("public_user_id")

    @property
    def display_name(self):
        return self._data.get("display_name")

    @property
    def password_hash(self):
        return self._data.get("password_hash")

    @property
    def is_active(self):
        return self._data.get("is_active", True)

    @property
    def created_at(self):
        return self._data.get("created_at")

    @property
    def updated_at(self):
        return self._data.get("updated_at")

    DEFAULT_PROTOCOL_SETTINGS = {
        "mode": "custom",  # "automatic" or "custom"
        "fragment_count": 3,
        "is_sss_enabled": False,
        "sss_threshold_k": 3,
        "sss_total_shares_m": 5,
        "fragment_telemetry": True,
        "fragment_reassembly_status": True,
        "private_mode": False,
    }

    @property
    def protocol_settings(self):
        settings = dict(self.DEFAULT_PROTOCOL_SETTINGS)
        user_settings = self._data.get("protocol_settings")
        if isinstance(user_settings, dict):
            settings.update(user_settings)
        return settings

    def to_dict(self):
        """Serialize user information for safe frontend consumption."""
        created_at_val = self.created_at
        updated_at_val = self.updated_at
        return {
            "id": self.internal_id,
            "internal_id": self.internal_id,
            "public_user_id": self.public_user_id,
            "display_name": self.display_name,
            "is_active": self.is_active,
            "protocol_settings": self.protocol_settings,
            "created_at": created_at_val.isoformat() if isinstance(created_at_val, datetime) else created_at_val,
            "updated_at": updated_at_val.isoformat() if isinstance(updated_at_val, datetime) else updated_at_val,
        }

    @classmethod
    def create(cls, public_user_id, display_name, password_hash):
        """Create and persist a new user document in MongoDB."""
        now = datetime.now(timezone.utc)
        internal_id = str(uuid.uuid4())
        doc = {
            "internal_id": internal_id,
            "public_user_id": public_user_id.strip(),
            "display_name": display_name.strip(),
            "password_hash": password_hash,
            "protocol_settings": dict(cls.DEFAULT_PROTOCOL_SETTINGS),
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        mongo.users.insert_one(doc)
        return cls(doc)

    @classmethod
    def find_by_internal_id(cls, internal_id):
        """Find a user by permanent internal ID."""
        if not internal_id:
            return None
        doc = mongo.users.find_one({"internal_id": internal_id})
        return cls(doc) if doc else None

    @classmethod
    def find_by_public_id(cls, public_user_id):
        """Find a user by public unique user ID (case-insensitive search)."""
        if not public_user_id:
            return None
        doc = mongo.users.find_one({"public_user_id": {"$regex": f"^{public_user_id.strip()}$", "$options": "i"}})
        return cls(doc) if doc else None

    @classmethod
    def search_by_query(cls, query, exclude_internal_id=None):
        """Search active users matching public_user_id or display_name."""
        q = query.strip()
        filter_criteria = {
            "is_active": True,
            "$or": [
                {"public_user_id": {"$regex": q, "$options": "i"}},
                {"display_name": {"$regex": q, "$options": "i"}},
            ]
        }
        if exclude_internal_id:
            filter_criteria["internal_id"] = {"$ne": exclude_internal_id}
        cursor = mongo.users.find(filter_criteria).limit(20)
        return [cls(doc) for doc in cursor]

    def update_profile(self, display_name=None, public_user_id=None):
        """Update display name and/or public user ID while preserving internal_id."""
        updates = {"updated_at": datetime.now(timezone.utc)}
        if display_name is not None:
            updates["display_name"] = display_name.strip()
            self._data["display_name"] = display_name.strip()
        if public_user_id is not None:
            updates["public_user_id"] = public_user_id.strip()
            self._data["public_user_id"] = public_user_id.strip()

        mongo.users.update_one({"internal_id": self.internal_id}, {"$set": updates})

    def update_protocol_settings(self, new_settings: dict):
        """Update user's secure protocol settings."""
        current = self.protocol_settings
        current.update(new_settings)
        self._data["protocol_settings"] = current
        self._data["updated_at"] = datetime.now(timezone.utc)
        mongo.users.update_one(
            {"internal_id": self.internal_id},
            {"$set": {
                "protocol_settings": current,
                "updated_at": self._data["updated_at"]
            }}
        )

    def delete(self):
        """Hard delete user document from MongoDB."""
        mongo.users.delete_one({"internal_id": self.internal_id})

    def __repr__(self):
        return f"<User internal_id='{self.internal_id}' public_id='{self.public_user_id}'>"
