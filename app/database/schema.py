"""
MongoDB Schema and Collection Management Utilities
Provides index initialization and collection reset functions.
"""

from app.database.db import mongo

def init_db(app=None):
    """Ensure all required collections and unique indexes exist in MongoDB."""
    mongo._ensure_indexes()

def reset_db(app=None):
    """Clear all collections (used in automated test setup/teardown)."""
    if mongo.db is not None:
        mongo.users.delete_many({})
        mongo.conversations.delete_many({})
        mongo.messages.delete_many({})
        mongo.message_fragments.delete_many({})
        mongo.message_shares.delete_many({})
        mongo.conversation_links.delete_many({})
        mongo.images.delete_many({})
        mongo._ensure_indexes()
