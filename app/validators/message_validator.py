"""
Message Validator Module
Validates message text payloads against resource limits and data integrity rules.
"""

from typing import Tuple, Optional
from config import Config

def validate_message_input(content: str, allow_empty: bool = False) -> Tuple[bool, Optional[str]]:
    """Validate plaintext message before encryption and fragmentation."""
    if content is None:
        return False, "Message content cannot be None."

    if not isinstance(content, str):
        return False, "Message content must be a string."

    if not allow_empty and len(content.strip()) == 0:
        return False, "Message cannot be empty."

    # Check UTF-8 byte length against maximum resource limit
    payload_bytes = content.encode("utf-8")
    if len(payload_bytes) > Config.MAX_MESSAGE_PAYLOAD_BYTES:
        return False, (
            f"Message payload exceeds maximum allowed limit of "
            f"{Config.MAX_MESSAGE_PAYLOAD_BYTES} bytes (received {len(payload_bytes)} bytes)."
        )

    return True, None
