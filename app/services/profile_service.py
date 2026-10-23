"""
Profile Service Module
Handles updating display names and unique public user IDs.
Preserves the permanent internal ID so conversations and messages remain intact.
"""

from typing import Tuple, Optional
from app.models.user import User
from app.validators.profile_validator import validate_profile_update

class ProfileService:
    """Service managing user profile modifications."""

    @staticmethod
    def update_profile(
        user: User,
        display_name: Optional[str] = None,
        public_user_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Update user profile.
        Changing public_user_id preserves internal_id and all conversation relationships.
        """
        if not user:
            return False, "User not found."

        is_valid, err = validate_profile_update(display_name, public_user_id)
        if not is_valid:
            return False, err

        if public_user_id is not None:
            cleaned_new_id = public_user_id.strip()
            # If changing to a different ID, ensure uniqueness
            if cleaned_new_id.lower() != user.public_user_id.lower():
                existing = User.find_by_public_id(cleaned_new_id)
                if existing and existing.internal_id != user.internal_id:
                    return False, f"Public user ID '{cleaned_new_id}' is already taken."

        user.update_profile(display_name=display_name, public_user_id=public_user_id)
        return True, None
