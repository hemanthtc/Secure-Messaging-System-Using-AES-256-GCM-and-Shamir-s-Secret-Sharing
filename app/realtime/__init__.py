"""
Realtime package initialization.
"""

from app.realtime.connection_manager import connection_manager
from app.realtime.socket_events import register_socket_events

__all__ = ["connection_manager", "register_socket_events"]
