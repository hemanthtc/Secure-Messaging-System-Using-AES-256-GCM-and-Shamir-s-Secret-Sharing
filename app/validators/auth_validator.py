"""
Authentication Validator Module
Validates registration and login inputs according to strict requirements.
Requires only: Name, Public User ID, Password (no email, no phone).
"""

import re
from typing import Tuple, Optional

PUBLIC_ID_REGEX = re.compile(r"^[a-zA-Z0-9_]{3,30}$")

def validate_registration_input(display_name: str, public_user_id: str, password: str) -> Tuple[bool, Optional[str]]:
    """Validate user registration payload."""
    if not display_name or not isinstance(display_name, str) or not display_name.strip():
        return False, "Display name is required and cannot be empty."

    cleaned_name = display_name.strip()
    if len(cleaned_name) < 2 or len(cleaned_name) > 50:
        return False, "Display name must be between 2 and 50 characters."

    if not public_user_id or not isinstance(public_user_id, str) or not public_user_id.strip():
        return False, "Public user ID is required."

    cleaned_id = public_user_id.strip()
    if not PUBLIC_ID_REGEX.match(cleaned_id):
        return False, "Public user ID must be 3-30 characters long and contain only letters, numbers, and underscores."

    if not password or not isinstance(password, str):
        return False, "Password is required."

    if len(password) < 8:
        return False, "Password must be at least 8 characters long."

    if len(password) > 128:
        return False, "Password must not exceed 128 characters."

    return True, None

def validate_login_input(display_name: str, public_user_id: str, password: str) -> Tuple[bool, Optional[str]]:
    """Validate user login payload requiring Name, User ID, and Password."""
    if not display_name or not isinstance(display_name, str) or not display_name.strip():
        return False, "Name is required for login."

    if not public_user_id or not isinstance(public_user_id, str) or not public_user_id.strip():
        return False, "User ID is required for login."

    if not password or not isinstance(password, str) or not password:
        return False, "Password is required for login."

    return True, None
