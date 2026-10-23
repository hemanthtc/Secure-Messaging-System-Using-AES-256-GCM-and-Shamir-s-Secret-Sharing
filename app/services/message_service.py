"""
Message Service Module
Orchestrates authenticated message encryption, fragmentation into N parts (2-10),
optional Shamir's Secret Sharing, and deterministic reconstruction upon arrival.
"""

import base64
import secrets
from typing import Tuple, Optional, Dict, Any, List
from app.models.message import Message
from app.models.message_fragment import MessageFragment
from app.models.message_share import MessageShare
from app.models.conversation import Conversation
from app.models.user import User
from app.validators.message_validator import validate_message_input
from app.validators.fragment_validator import validate_fragment_count
from app.validators.share_validator import validate_sss_parameters
from app.crypto.encryption import encrypt_message, decrypt_message
from app.crypto.key_management import create_message_key_shares, reconstruct_aes_key_from_shares
from app.services.fragmentation_service import FragmentationService
from app.services.reassembly_service import ReassemblyService

class MessageService:
    """Service handling message creation, fragmentation, reassembly, and decryption."""

    @staticmethod
    def send_message(
        conversation_id: str,
        sender: User,
        content: str,
        fragment_count: Optional[Any] = None,
        is_sss_enabled: Optional[bool] = None,
        sss_threshold_k: Optional[int] = None,
        sss_total_shares_m: Optional[int] = None,
        message_type: str = "text",
        image_id: Optional[str] = None,
        image_filename: Optional[str] = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Validate, encrypt, fragment, and persist a secure message.
        Supports Automatic mode (CSPRNG configuration selection) and Custom mode.
        """
        conv = Conversation.find_by_id(conversation_id)
        if not conv or sender.internal_id not in conv.participants:
            return None, "Conversation not found or unauthorized."

        # 1. Validate plaintext content
        is_valid_msg, err = validate_message_input(content)
        if not is_valid_msg:
            return None, err

        user_settings = sender.protocol_settings
        mode = user_settings.get("mode", "custom")

        # Resolve configuration: Automatic vs. Custom mode
        if mode == "automatic" and (fragment_count is None or str(fragment_count).lower() == "auto"):
            # Automatic Mode:
            # - Random fragment count in [2, 10] using CSPRNG
            n_parts = secrets.randbelow(9) + 2  # Generates 2 .. 10
            # - Decide whether SSS is enabled via CSPRNG
            is_sss = secrets.choice([True, False])
            if is_sss:
                # - Valid M in [2, 10], valid K in [2, M]
                m_val = secrets.randbelow(9) + 2  # 2 .. 10
                k_val = secrets.randbelow(m_val - 1) + 2  # 2 .. m_val
            else:
                k_val, m_val = None, None
        else:
            # Custom Mode: Use provided overrides or sender's configured settings
            if fragment_count is None:
                frag_to_use = user_settings.get("fragment_count", 3)
            else:
                frag_to_use = fragment_count

            is_valid_frag, n_parts, err = validate_fragment_count(frag_to_use)
            if not is_valid_frag:
                return None, err

            if is_sss_enabled is None:
                is_sss = bool(user_settings.get("is_sss_enabled", False))
                k_candidate = user_settings.get("sss_threshold_k", 3)
                m_candidate = user_settings.get("sss_total_shares_m", 5)
            else:
                is_sss = bool(is_sss_enabled)
                k_candidate = sss_threshold_k
                m_candidate = sss_total_shares_m

            if is_sss:
                is_valid_sss, k_val, m_val, err = validate_sss_parameters(k_candidate, m_candidate)
                if not is_valid_sss:
                    return None, err
            else:
                k_val, m_val = None, None

        # Determine recipient user in 1-on-1 direct conversation
        recipient_id = None
        for pid in conv.participants:
            if pid != sender.internal_id:
                recipient_id = pid
                break

        # 4. Perform authenticated AES-256-GCM encryption
        enc_res = encrypt_message(content)
        aes_key_bytes = enc_res["key_bytes"]
        nonce_b64 = enc_res["nonce_b64"]
        ciphertext_bytes = enc_res["ciphertext_bytes"]
        ciphertext_hash = enc_res["ciphertext_hash"]

        key_bundle = None
        shares_data = []
        if is_sss:
            # Split key using Shamir's Secret Sharing into M shares
            shares_data = create_message_key_shares(aes_key_bytes, k_val, m_val)
        else:
            # Store key in base64 bundle for standard transmission
            key_bundle = enc_res["key_b64"]

        # 5. Persist message record
        msg = Message.create(
            conversation_id=conversation_id,
            sender_id=sender.internal_id,
            recipient_id=recipient_id,
            fragment_count=n_parts,
            nonce=nonce_b64,
            ciphertext_hash=ciphertext_hash,
            is_sss_enabled=is_sss,
            sss_threshold_k=k_val,
            sss_total_shares_m=m_val,
            encryption_key_bundle=key_bundle,
            message_type=message_type,
            image_id=image_id,
            image_filename=image_filename
        )

        # 6. Fragment ciphertext payload into exactly N parts
        fragments_info = FragmentationService.fragment_payload(
            payload=ciphertext_bytes,
            fragment_count=n_parts,
            message_uuid=msg.message_uuid
        )

        # Persist fragments in database
        saved_fragments = []
        for frag in fragments_info:
            frag_obj, _ = MessageFragment.create(
                message_uuid=msg.message_uuid,
                fragment_index=frag["fragment_index"],
                total_fragments=frag["total_fragments"],
                payload=frag["payload_b64"],
                payload_hash=frag["payload_hash"]
            )
            saved_fragments.append(frag_obj.to_dict())

        # Persist Shamir shares if enabled
        saved_shares = []
        if is_sss:
            for s in shares_data:
                share_obj, _ = MessageShare.create(
                    message_uuid=msg.message_uuid,
                    share_index=s["share_index"],
                    share_x=s["share_x"],
                    share_y=s["share_y"]
                )
                saved_shares.append(share_obj.to_dict())

        conv.update_timestamp()

        result = msg.to_dict(include_fragments=True)
        result["plaintext"] = content
        result["display_text"] = content
        return result, None

    @staticmethod
    def get_and_reassemble_message(
        message_uuid: str,
        requesting_user: User,
        provided_shares: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Retrieve fragments for a message, perform reassembly, and decrypt if all parts are available.
        Strict rule: message is only displayed when 100% of fragments are received and verified.
        """
        msg = Message.find_by_uuid(message_uuid)
        if not msg:
            return None, "Message not found."

        conv = Conversation.find_by_id(msg.conversation_id)
        if not conv or requesting_user.internal_id not in conv.participants:
            return None, "Unauthorized access to message."

        # If message was deleted by this specific user, do not display
        if requesting_user.internal_id in msg.deleted_for:
            return None, "Message was deleted."

        # Update delivery state to delivered if recipient is fetching
        if requesting_user.internal_id == msg.recipient_id and msg.delivery_state == "sent":
            msg.update_delivery_state("delivered")

        # Fast-path: If message was already verified, reassembled, and fragments purged, return directly
        if msg.fragments_purged and msg.plaintext is not None:
            response_data = msg.to_dict(include_fragments=True)
            response_data["reassembly_status"] = "complete"
            response_data["received_count"] = msg.fragment_count
            response_data["missing_indexes"] = []
            response_data["plaintext"] = msg.plaintext
            response_data["display_text"] = msg.plaintext
            return response_data, None

        # Fetch fragments currently received in database
        db_fragments = msg.get_fragments()
        frag_dicts = [f.to_dict() for f in db_fragments]

        reassembly_res = ReassemblyService.reassemble_fragments(
            fragments=frag_dicts,
            expected_total=msg.fragment_count,
            expected_hash=msg.ciphertext_hash
        )

        response_data = msg.to_dict(include_fragments=True)
        response_data["reassembly_status"] = reassembly_res["status"]
        response_data["received_count"] = reassembly_res["received_count"]
        response_data["missing_indexes"] = reassembly_res["missing_indexes"]

        if not reassembly_res["is_complete"]:
            response_data["plaintext"] = None
            response_data["display_text"] = f"Waiting for missing fragments: received {reassembly_res['received_count']}/{msg.fragment_count}."
            return response_data, None

        # All fragments arrived and verified! Now obtain AES key for decryption.
        ciphertext_bytes = reassembly_res["reassembled_bytes"]
        nonce_bytes = base64.b64decode(msg.nonce)

        aes_key_bytes = None
        if msg.is_sss_enabled:
            # Key shares recovery
            shares_to_use = provided_shares or [s.to_dict() for s in msg.get_shares()]
            if len(shares_to_use) < msg.sss_threshold_k:
                response_data["plaintext"] = None
                response_data["display_text"] = f"Waiting for Shamir key shares ({len(shares_to_use)}/{msg.sss_threshold_k} required)."
                return response_data, None

            try:
                aes_key_bytes = reconstruct_aes_key_from_shares(shares_to_use, msg.sss_threshold_k)
            except Exception as e:
                response_data["plaintext"] = None
                response_data["display_text"] = f"Key reconstruction error: {str(e)}"
                return response_data, None
        else:
            if msg.encryption_key_bundle:
                aes_key_bytes = base64.b64decode(msg.encryption_key_bundle)

        if not aes_key_bytes:
            return None, "Encryption key unavailable."

        # Decrypt payload
        try:
            plaintext = decrypt_message(ciphertext_bytes, nonce_bytes, aes_key_bytes)
            # Reassembly and integrity verified 100%!
            # Record reassembled plaintext and permanently purge bulky intermediate transmission fragments & shares
            msg.mark_reassembled_and_purge_fragments(plaintext)

            response_data["plaintext"] = plaintext
            response_data["display_text"] = plaintext
            response_data["status"] = "reassembled"
            response_data["fragments_purged"] = True
            return response_data, None
        except Exception as e:
            msg.update_status("tampered")
            response_data["status"] = "tampered"
            response_data["plaintext"] = None
            response_data["display_text"] = f"Decryption failed: integrity verification error ({str(e)})."
            return response_data, None

    @staticmethod
    def get_conversation_messages(conversation_id: str, current_user: User) -> List[Dict[str, Any]]:
        """Retrieve and attempt reassembly for all messages in a conversation."""
        conv = Conversation.find_by_id(conversation_id)
        if not conv or current_user.internal_id not in conv.participants:
            return []

        messages = Message.find_by_conversation(conversation_id, for_user_id=current_user.internal_id)
        results = []
        for m in messages:
            data, _ = MessageService.get_and_reassemble_message(m.message_uuid, current_user)
            if data:
                results.append(data)
        return results

    @staticmethod
    def mark_conversation_as_read(conversation_id: str, current_user: User) -> List[str]:
        """Mark all unread incoming messages in the conversation as read by the recipient."""
        from datetime import datetime, timezone
        from app.database.db import mongo

        conv = Conversation.find_by_id(conversation_id)
        if not conv or current_user.internal_id not in conv.participants:
            return []

        now = datetime.now(timezone.utc)
        query = {
            "conversation_id": conversation_id,
            "recipient_id": current_user.internal_id,
            "delivery_state": {"$ne": "read"}
        }
        msgs = list(mongo.messages.find(query, {"message_uuid": 1}))
        uuids = [m["message_uuid"] for m in msgs]
        if uuids:
            mongo.messages.update_many(
                {"message_uuid": {"$in": uuids}},
                {"$set": {"delivery_state": "read", "read_at": now}}
            )
        return uuids
