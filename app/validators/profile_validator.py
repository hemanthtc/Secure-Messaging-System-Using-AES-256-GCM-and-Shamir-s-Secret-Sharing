"""
Profile Validator Module
Validates profile edits (display name and public user ID).
"""

from typing import Tuple, Optional
from app.validators.auth_validator import PUBLIC_ID_REGEX

def validate_profile_update(display_name: Optional[str], public_user_id: Optional[str]) -> Tuple[bool, Optional[str]]:
    """Validate user profile update data."""
    if display_name is not None:
        if not isinstance(display_name, str) or not display_name.strip():
            return False, "Display name cannot be empty."
        cleaned_name = display_name.strip()
        if len(cleaned_name) < 2 or len(cleaned_name) > 50:
            return False, "Display name must be between 2 and 50 characters."

    if public_user_id is not None:
        if not isinstance(public_user_id, str) or not public_user_id.strip():
            return False, "Public user ID cannot be empty."
        cleaned_id = public_user_id.strip()
        if not PUBLIC_ID_REGEX.match(cleaned_id):
            return False, "Public user ID must be 3-30 characters long and contain only letters, numbers, and underscores."

    return True, None
