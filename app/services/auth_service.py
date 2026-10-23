"""
Authentication Service Module
Handles user registration and authentication logic.
Enforces unique public user IDs, Argon2id password hashing, and login credential checks.
"""

from typing import Tuple, Optional
from app.models.user import User
from app.validators.auth_validator import validate_registration_input, validate_login_input
from app.security.password_security import hash_password, verify_password

class AuthService:
    """Service encapsulating user registration and login workflows."""

    @staticmethod
    def register_user(display_name: str, public_user_id: str, password: str) -> Tuple[Optional[User], Optional[str]]:
        """Register a new user account with display name, unique public user ID, and password."""
        is_valid, err = validate_registration_input(display_name, public_user_id, password)
        if not is_valid:
            return None, err

        # Check uniqueness of public_user_id
        existing = User.find_by_public_id(public_user_id)
        if existing:
            return None, f"Public user ID '{public_user_id}' is already taken. Please choose another."

        pwd_hash = hash_password(password)
        user = User.create(
            public_user_id=public_user_id,
            display_name=display_name,
            password_hash=pwd_hash
        )
        return user, None

    @staticmethod
    def authenticate_user(display_name: str, public_user_id: str, password: str) -> Tuple[Optional[User], Optional[str]]:
        """Authenticate user requiring Name, User ID, and Password."""
        is_valid, err = validate_login_input(display_name, public_user_id, password)
        if not is_valid:
            return None, err

        user = User.find_by_public_id(public_user_id)
        if not user or not user.is_active:
            return None, "Invalid credentials: user ID not found or account inactive."

        # Verify display name matches (case-insensitive check)
        if user.display_name.strip().lower() != display_name.strip().lower():
            return None, "Invalid credentials: name does not match user account records."

        # Verify password hash
        if not verify_password(password, user.password_hash):
            return None, "Invalid credentials: password does not match."

        return user, None
