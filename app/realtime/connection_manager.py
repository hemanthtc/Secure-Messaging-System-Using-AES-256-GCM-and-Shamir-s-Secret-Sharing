"""
Real-time Connection Manager Module
Tracks active WebSocket clients and maps user internal IDs to socket session IDs.
"""

from collections import defaultdict
from typing import Set, Dict, List

class ConnectionManager:
    """Manages active socket IDs per user internal ID for room and presence tracking."""

    def __init__(self):
        # Maps user_internal_id -> set of socket session IDs (sid)
        self._user_sids: Dict[str, Set[str]] = defaultdict(set)
        # Maps sid -> user_internal_id
        self._sid_to_user: Dict[str, str] = {}

    def register(self, sid: str, user_internal_id: str):
        """Register active socket connection for a user."""
        self._user_sids[user_internal_id].add(sid)
        self._sid_to_user[sid] = user_internal_id

    def unregister(self, sid: str) -> str:
        """Unregister socket connection on disconnect. Returns user_internal_id if found."""
        user_id = self._sid_to_user.pop(sid, None)
        if user_id and user_id in self._user_sids:
            self._user_sids[user_id].discard(sid)
            if not self._user_sids[user_id]:
                del self._user_sids[user_id]
        return user_id

    def is_user_online(self, user_internal_id: str) -> bool:
        """Check if user has at least one active socket connection."""
        return bool(self._user_sids.get(user_internal_id))

    def get_user_sids(self, user_internal_id: str) -> List[str]:
        """Get all active socket IDs for a user."""
        return list(self._user_sids.get(user_internal_id, []))

connection_manager = ConnectionManager()
