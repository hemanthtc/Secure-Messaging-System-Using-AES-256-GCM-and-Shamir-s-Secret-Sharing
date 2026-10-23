"""
Routes package initialization.
"""

from app.routes.auth_routes import auth_bp
from app.routes.profile_routes import profile_bp
from app.routes.user_routes import user_bp
from app.routes.chat_routes import chat_bp
from app.routes.message_routes import message_bp
from app.routes.settings_routes import settings_bp
from app.routes.share_link_routes import share_link_bp

__all__ = [
    "auth_bp",
    "profile_bp",
    "user_bp",
    "chat_bp",
    "message_bp",
    "settings_bp",
    "share_link_bp",
]
