"""
User Service Module
Provides search functionality and lookup by public user ID or internal ID.
"""

from typing import List, Optional
from app.models.user import User

class UserService:
    """Service for searching users and looking up profiles."""

    @staticmethod
    def search_users(query: str, current_user: User) -> List[dict]:
        """Search for other users by public ID or name, excluding current user."""
        if not query or not query.strip():
            return []
        users = User.search_by_query(query, exclude_internal_id=current_user.internal_id)
        return [u.to_dict() for u in users]

    @staticmethod
    def get_by_public_id(public_user_id: str) -> Optional[User]:
        """Retrieve user by public user ID."""
        return User.find_by_public_id(public_user_id)

    @staticmethod
    def get_by_internal_id(internal_id: str) -> Optional[User]:
        """Retrieve user by permanent internal ID."""
        return User.find_by_internal_id(internal_id)
