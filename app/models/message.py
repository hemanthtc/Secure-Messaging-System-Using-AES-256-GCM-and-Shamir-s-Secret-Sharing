"""
Message Model Definition for MongoDB Atlas
Tracks encrypted message metadata, fragmentation configuration (2-10 parts),
and optional Shamir's Secret Sharing configuration.
"""

from datetime import datetime, timezone
import uuid
from app.database.db import mongo
from app.models.user import User

class Message:
    """Encrypted Message entity wrapping MongoDB documents."""

    def __init__(self, data):
        self._data = data or {}

    @property
    def id(self):
        return self._data.get("message_uuid")

    @property
    def message_uuid(self):
        return self._data.get("message_uuid")

    @property
    def conversation_id(self):
        return self._data.get("conversation_id")

    @property
    def sender_id(self):
        return self._data.get("sender_id")

    @property
    def recipient_id(self):
        return self._data.get("recipient_id")

    @property
    def fragment_count(self):
        return int(self._data.get("fragment_count", 3))

    @property
    def is_sss_enabled(self):
        return bool(self._data.get("is_sss_enabled", False))

    @property
    def sss_threshold_k(self):
        return self._data.get("sss_threshold_k")

    @property
    def sss_total_shares_m(self):
        return self._data.get("sss_total_shares_m")

    @property
    def nonce(self):
        return self._data.get("nonce")

    @property
    def ciphertext_hash(self):
        return self._data.get("ciphertext_hash")

    @property
    def encryption_key_bundle(self):
        return self._data.get("encryption_key_bundle")

    @property
    def status(self):
        return self._data.get("status", "pending")

    @property
    def delivery_state(self):
        return self._data.get("delivery_state", "sent")

    @property
    def message_type(self):
        return self._data.get("message_type", "text")

    @property
    def image_id(self):
        return self._data.get("image_id")

    @property
    def image_filename(self):
        return self._data.get("image_filename")

    @property
    def plaintext(self):
        return self._data.get("plaintext")

    @property
    def fragments_purged(self):
        return bool(self._data.get("fragments_purged", False))

    @property
    def deleted_for(self):
        return list(self._data.get("deleted_for", []))

    @property
    def created_at(self):
        return self._data.get("created_at")

    @property
    def delivered_at(self):
        return self._data.get("delivered_at")

    @property
    def read_at(self):
        return self._data.get("read_at")

    def get_sender(self):
        """Retrieve sender user profile."""
        return User.find_by_internal_id(self.sender_id)

    def get_recipient(self):
        """Retrieve recipient user profile."""
        return User.find_by_internal_id(self.recipient_id)

    def get_fragments(self):
        """Retrieve all currently saved fragments for this message, ordered by fragment_index."""
        from app.models.message_fragment import MessageFragment
        cursor = mongo.message_fragments.find({"message_uuid": self.message_uuid}).sort("fragment_index", 1)
        return [MessageFragment(doc) for doc in cursor]

    def get_shares(self):
        """Retrieve all currently saved key shares for this message, ordered by share_index."""
        from app.models.message_share import MessageShare
        cursor = mongo.message_shares.find({"message_uuid": self.message_uuid}).sort("share_index", 1)
        return [MessageShare(doc) for doc in cursor]

    def to_dict(self, include_fragments=False):
        """Serialize message metadata for API responses."""
        sender = self.get_sender()
        fragments = self.get_fragments()
        received_count = self.fragment_count if self.fragments_purged else len(fragments)
        created_at_val = self.created_at
        delivered_at_val = self.delivered_at
        read_at_val = self.read_at

        data = {
            "id": self.message_uuid,
            "message_uuid": self.message_uuid,
            "conversation_id": self.conversation_id,
            "sender_id": self.sender_id,
            "sender_public_id": sender.public_user_id if sender else "Deleted User",
            "sender_display_name": sender.display_name if sender else "Deleted User",
            "recipient_id": self.recipient_id,
            "message_type": self.message_type,
            "image_id": self.image_id,
            "image_filename": self.image_filename,
            "delivery_state": self.delivery_state,
            "fragment_count": self.fragment_count,
            "received_fragments_count": received_count,
            "is_sss_enabled": self.is_sss_enabled,
            "sss_threshold_k": self.sss_threshold_k,
            "sss_total_shares_m": self.sss_total_shares_m,
            "status": self.status,
            "plaintext": self.plaintext,
            "display_text": self.plaintext,
            "fragments_purged": self.fragments_purged,
            "deleted_for": self.deleted_for,
            "created_at": created_at_val.isoformat() if isinstance(created_at_val, datetime) else created_at_val,
            "delivered_at": delivered_at_val.isoformat() if isinstance(delivered_at_val, datetime) else delivered_at_val,
            "read_at": read_at_val.isoformat() if isinstance(read_at_val, datetime) else read_at_val,
        }

        if include_fragments and not self.fragments_purged:
            data["fragments"] = [f.to_dict() for f in fragments]
            if self.is_sss_enabled:
                data["shares"] = [s.to_dict() for s in self.get_shares()]
        elif include_fragments:
            data["fragments"] = []
        return data

    @classmethod
    def create(cls, conversation_id, sender_id, recipient_id, fragment_count,
               nonce, ciphertext_hash, is_sss_enabled=False, sss_threshold_k=None,
               sss_total_shares_m=None, encryption_key_bundle=None, message_uuid=None,
               message_type="text", image_id=None, image_filename=None):
        """Create and store a new message document in MongoDB."""
        now = datetime.now(timezone.utc)
        msg_uuid = message_uuid or str(uuid.uuid4())
        doc = {
            "message_uuid": msg_uuid,
            "conversation_id": conversation_id,
            "sender_id": sender_id,
            "recipient_id": recipient_id,
            "message_type": message_type,
            "image_id": image_id,
            "image_filename": image_filename,
            "delivery_state": "sent",
            "fragment_count": int(fragment_count),
            "is_sss_enabled": bool(is_sss_enabled),
            "sss_threshold_k": int(sss_threshold_k) if sss_threshold_k else None,
            "sss_total_shares_m": int(sss_total_shares_m) if sss_total_shares_m else None,
            "nonce": nonce,
            "ciphertext_hash": ciphertext_hash,
            "encryption_key_bundle": encryption_key_bundle,
            "status": "pending",
            "deleted_for": [],
            "created_at": now,
            "delivered_at": None,
            "read_at": None,
        }
        mongo.messages.insert_one(doc)
        return cls(doc)

    @classmethod
    def find_by_uuid(cls, message_uuid):
        """Find message by UUID."""
        if not message_uuid:
            return None
        doc = mongo.messages.find_one({"message_uuid": message_uuid})
        return cls(doc) if doc else None

    @classmethod
    def find_by_conversation(cls, conversation_id, for_user_id=None):
        """Retrieve all messages belonging to a conversation, excluding messages deleted for for_user_id."""
        query = {"conversation_id": conversation_id}
        if for_user_id:
            query["deleted_for"] = {"$ne": for_user_id}
        cursor = mongo.messages.find(query).sort("created_at", 1)
        return [cls(doc) for doc in cursor]

    def mark_deleted_for_user(self, user_internal_id: str):
        """Record that this message has been deleted by a specific user (Delete for Me)."""
        if not user_internal_id:
            return
        mongo.messages.update_one(
            {"message_uuid": self.message_uuid},
            {"$addToSet": {"deleted_for": user_internal_id}}
        )
        if "deleted_for" not in self._data:
            self._data["deleted_for"] = []
        if user_internal_id not in self._data["deleted_for"]:
            self._data["deleted_for"].append(user_internal_id)

    def is_deleted_for_all(self, conversation_participants: list) -> bool:
        """Check if all participants of the conversation have deleted this message."""
        if not conversation_participants:
            return False
        del_set = set(self.deleted_for)
        return all(p in del_set for p in conversation_participants)

    def update_status(self, new_status):
        """Update message lifecycle status (e.g., 'reassembled', 'failed')."""
        self._data["status"] = new_status
        mongo.messages.update_one(
            {"message_uuid": self.message_uuid},
            {"$set": {"status": new_status}}
        )

    def update_delivery_state(self, new_state):
        """Update delivery receipt state ('sent' -> 'delivered' -> 'read')."""
        valid_states = ["sent", "delivered", "read"]
        if new_state not in valid_states:
            return
        
        now = datetime.now(timezone.utc)
        self._data["delivery_state"] = new_state
        update_fields = {"delivery_state": new_state}
        if new_state == "delivered" and not self._data.get("delivered_at"):
            self._data["delivered_at"] = now
            update_fields["delivered_at"] = now
        elif new_state == "read":
            if not self._data.get("delivered_at"):
                self._data["delivered_at"] = now
                update_fields["delivered_at"] = now
            self._data["read_at"] = now
            update_fields["read_at"] = now

        mongo.messages.update_one(
            {"message_uuid": self.message_uuid},
            {"$set": update_fields}
        )

    def mark_reassembled_and_purge_fragments(self, plaintext: str):
        """
        Record verified reassembled plaintext on message and purge
        bulky intermediate transmission fragments and shares from MongoDB Atlas.
        """
        self._data["status"] = "reassembled"
        self._data["plaintext"] = plaintext
        self._data["fragments_purged"] = True
        mongo.messages.update_one(
            {"message_uuid": self.message_uuid},
            {"$set": {
                "status": "reassembled",
                "plaintext": plaintext,
                "fragments_purged": True
            }}
        )
        mongo.message_fragments.delete_many({"message_uuid": self.message_uuid})
        mongo.message_shares.delete_many({"message_uuid": self.message_uuid})

    def delete(self):
        """Delete message and its associated fragments, shares, and physical image files."""
        if self.image_id:
            try:
                from app.services.image_service import ImageService
                ImageService.delete_image_by_id(self.image_id)
            except Exception:
                pass
        mongo.message_fragments.delete_many({"message_uuid": self.message_uuid})
        mongo.message_shares.delete_many({"message_uuid": self.message_uuid})
        mongo.messages.delete_one({"message_uuid": self.message_uuid})

    def __repr__(self):
        return f"<Message uuid='{self.message_uuid}' fragments={self.fragment_count} status='{self.status}'>"
