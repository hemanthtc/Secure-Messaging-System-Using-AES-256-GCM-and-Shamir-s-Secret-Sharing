"""
Delivery Service Module
Handles incremental and out-of-order fragment delivery, duplicate event tracking,
and offline message queuing.
"""

from typing import Dict, Any, Tuple, Optional
from app.models.message import Message
from app.models.message_fragment import MessageFragment
from app.validators.fragment_validator import validate_fragment_packet
from app.services.reassembly_service import ReassemblyService

class DeliveryService:
    """Service for incremental fragment packet delivery."""

    @staticmethod
    def receive_fragment_packet(
        message_uuid: str,
        fragment_index: int,
        total_fragments: int,
        payload_b64: str,
        payload_hash: str
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Process an incoming individual fragment packet.
        Supports out-of-order arrivals, detects duplicates, and updates delivery tracking.
        """
        # Validate fragment packet format, index bounds, and SHA-256 hash
        is_valid, err = validate_fragment_packet(
            message_uuid=message_uuid,
            fragment_index=fragment_index,
            total_fragments=total_fragments,
            payload_b64=payload_b64,
            payload_hash=payload_hash
        )
        if not is_valid:
            return None, err

        msg = Message.find_by_uuid(message_uuid)
        if not msg:
            return None, f"Message '{message_uuid}' not found."

        if msg.fragment_count != int(total_fragments):
            return None, f"Packet fragment total {total_fragments} conflicts with registered count {msg.fragment_count}."

        # Insert or identify duplicate
        frag_obj, is_duplicate = MessageFragment.create(
            message_uuid=message_uuid,
            fragment_index=fragment_index,
            total_fragments=total_fragments,
            payload=payload_b64,
            payload_hash=payload_hash
        )

        all_fragments = msg.get_fragments()
        received_count = len(all_fragments)

        status_info = {
            "message_uuid": message_uuid,
            "fragment_index": fragment_index,
            "is_duplicate": is_duplicate,
            "received_count": received_count,
            "total_fragments": msg.fragment_count,
            "is_complete": received_count >= msg.fragment_count,
        }

        return status_info, None
