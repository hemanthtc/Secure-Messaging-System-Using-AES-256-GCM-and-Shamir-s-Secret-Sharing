"""
Account Service Module
Manages account lifecycle operations, password changes, and hard account deletion.
Enforces explicit confirmation before permanent deletion.
"""

from typing import Tuple, Optional
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.database.db import mongo
from app.security.password_security import verify_password, hash_password

class AccountService:
    """Service managing account operations and destructive deletions."""

    @staticmethod
    def change_password(user: User, current_password: str, new_password: str) -> Tuple[bool, Optional[str]]:
        """Change user password after verifying current credentials."""
        if not verify_password(current_password, user.password_hash):
            return False, "Current password is incorrect."

        if len(new_password) < 8:
            return False, "New password must be at least 8 characters long."

        new_hash = hash_password(new_password)
        mongo.users.update_one(
            {"internal_id": user.internal_id},
            {"$set": {"password_hash": new_hash}}
        )
        return True, None

    @staticmethod
    def delete_account_permanently(user: User, confirmation_password: str) -> Tuple[bool, Optional[str]]:
        """
        Permanently delete the user account and associated records per hard-deletion policy.
        Requires explicit confirmation of current password.
        """
        if not user:
            return False, "User not found."

        if not verify_password(confirmation_password, user.password_hash):
            return False, "Account deletion confirmation failed: incorrect password."

        # 1. Find all messages sent by this user
        sent_msgs = mongo.messages.find({"sender_id": user.internal_id}, {"message_uuid": 1})
        sent_uuids = [m["message_uuid"] for m in sent_msgs]
        if sent_uuids:
            # Delete fragments and shares of sent messages
            mongo.message_fragments.delete_many({"message_uuid": {"$in": sent_uuids}})
            mongo.message_shares.delete_many({"message_uuid": {"$in": sent_uuids}})
            mongo.messages.delete_many({"message_uuid": {"$in": sent_uuids}})

        # 2. Find conversations user participated in
        conv_cursor = mongo.conversations.find({"participants": user.internal_id})
        for c in conv_cursor:
            conv_id = c["conversation_id"]
            remaining_participants = [p for p in c.get("participants", []) if p != user.internal_id]
            if not remaining_participants:
                # If no participants left, delete entire conversation
                Conversation.find_by_id(conv_id).delete()
            else:
                # Update conversation participants
                mongo.conversations.update_one(
                    {"conversation_id": conv_id},
                    {"$set": {"participants": remaining_participants}}
                )

        # 3. Delete user document
        user.delete()
        return True, None
