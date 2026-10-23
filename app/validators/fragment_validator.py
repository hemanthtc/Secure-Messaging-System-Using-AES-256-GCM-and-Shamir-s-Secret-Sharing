"""
Fragment Validator Module
Enforces strict rules on configurable fragment counts (2 to 10 parts) and individual fragment packets.
Both frontend and backend validate fragment values independently.
"""

from typing import Tuple, Optional, Any
import hashlib
import base64

def validate_fragment_count(val: Any) -> Tuple[bool, Optional[int], Optional[str]]:
    """
    Validate that the requested fragment count N is strictly an integer between 2 and 10.
    Rejects:
      - None / missing values
      - Values below 2
      - Values above 10
      - Negative values
      - Decimal values (float or decimal string like 3.5 or 3.0)
      - Non-integer types (bool, float, invalid strings, lists, etc.)
    Returns (is_valid, integer_value, error_message).
    """
    if val is None:
        return False, None, "Fragment count is missing."

    # Booleans are subclasses of int in Python, explicitly reject them
    if isinstance(val, bool):
        return False, None, "Fragment count must be an integer, not a boolean."

    # Floats must be rejected (decimal values)
    if isinstance(val, float):
        return False, None, "Decimal fragment counts are not allowed. Must be an integer between 2 and 10."

    # String parsing
    if isinstance(val, str):
        cleaned = val.strip()
        if not cleaned:
            return False, None, "Fragment count cannot be empty."
        # If string contains decimal point, minus sign, or non-digits, reject
        if "." in cleaned or "," in cleaned:
            return False, None, "Decimal fragment counts are not allowed. Must be an integer between 2 and 10."
        if cleaned.startswith("-"):
            return False, None, "Negative fragment counts are not allowed. Must be between 2 and 10."
        if not cleaned.isdigit():
            return False, None, "Fragment count must be a positive integer between 2 and 10."
        int_val = int(cleaned)
    elif isinstance(val, int):
        int_val = val
    else:
        return False, None, "Fragment count must be an integer between 2 and 10."

    if int_val < 0:
        return False, None, "Negative fragment counts are not allowed."

    if int_val < 2:
        return False, None, f"Fragment count {int_val} is too low. Minimum permitted is 2."

    if int_val > 10:
        return False, None, f"Fragment count {int_val} is too high. Maximum permitted is 10."

    return True, int_val, None


def validate_fragment_packet(
    message_uuid: str,
    fragment_index: Any,
    total_fragments: Any,
    payload_b64: str,
    payload_hash: str
) -> Tuple[bool, Optional[str]]:
    """Validate integrity, indices, and checksum of an individual fragment packet."""
    if not message_uuid or not isinstance(message_uuid, str):
        return False, "Invalid or missing message UUID."

    is_valid_total, total_int, err = validate_fragment_count(total_fragments)
    if not is_valid_total:
        return False, f"Invalid total_fragments in fragment packet: {err}"

    if isinstance(fragment_index, bool) or isinstance(fragment_index, float):
        return False, "Fragment index must be an integer."

    try:
        idx = int(fragment_index)
    except (ValueError, TypeError):
        return False, "Fragment index must be an integer."

    if idx < 1:
        return False, f"Fragment index {idx} is invalid. Indexes are 1-based (must be >= 1)."

    if idx > total_int:
        return False, f"Fragment index {idx} exceeds total fragments {total_int}."

    if payload_b64 is None or not isinstance(payload_b64, str):
        return False, "Fragment payload must be a base64 encoded string."

    try:
        payload_bytes = base64.b64decode(payload_b64)
    except Exception:
        return False, "Fragment payload is not valid base64."

    if not payload_hash or not isinstance(payload_hash, str):
        return False, "Fragment payload hash is missing."

    computed_hash = hashlib.sha256(payload_bytes).hexdigest()
    if computed_hash.lower() != payload_hash.lower():
        return False, f"Fragment payload hash mismatch: integrity verification failed."

    return True, None
