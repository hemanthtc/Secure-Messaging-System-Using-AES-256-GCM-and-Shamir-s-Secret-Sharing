"""
MongoDB Atlas Database Connection and Management Module
Supports MongoDB Atlas (mongodb+srv://), local MongoDB, and mongomock for testing.
"""

import os
from pymongo import MongoClient, ASCENDING
import mongomock

class MongoDB:
    """Singleton MongoDB wrapper providing collection access and index management."""
    def __init__(self):
        self.client = None
        self.db = None
        self._is_mock = False

    def init_app(self, app):
        """Initialize MongoDB client using Flask application configuration."""
        use_mock = app.config.get("USE_MONGOMOCK", False)
        mongo_uri = app.config.get("MONGO_URI", "mongodb://localhost:27017/secureshare")
        db_name = app.config.get("MONGO_DB_NAME", "secureshare")

        if use_mock:
            self.client = mongomock.MongoClient()
            self.db = self.client[db_name]
            self._is_mock = True
        else:
            try:
                # Attempt connection to MongoDB Atlas / Local MongoDB
                self.client = MongoClient(mongo_uri, serverSelectionTimeoutMS=6000)
                # Verify connection with ping
                self.client.admin.command('ping')
                self.db = self.client[db_name]
                self._is_mock = False
                print(f"[*] Connected to MongoDB Atlas cluster successfully (database: '{db_name}')")
                app.logger.info(f"Connected to MongoDB Atlas cluster successfully (database: '{db_name}')")
            except Exception as e:
                # If remote Atlas or local daemon is not reachable during local dev, fallback to mongomock
                # with clear documentation so the app stays functional.
                print(f"[!] MongoDB Atlas connection notice ({e}); falling back to mock store.")
                app.logger.warning(f"MongoDB Atlas/Local daemon not reachable ({e}); falling back to in-memory mock store for development.")
                self.client = mongomock.MongoClient()
                self.db = self.client[db_name]
                self._is_mock = True

        self._ensure_indexes()

    def _ensure_indexes(self):
        """Create required unique constraints and search indexes across MongoDB collections."""
        if self.db is None:
            return

        # Users collection
        self.db.users.create_index([("public_user_id", ASCENDING)], unique=True)
        self.db.users.create_index([("internal_id", ASCENDING)], unique=True)

        # Conversations collection
        self.db.conversations.create_index([("participants", ASCENDING)])

        # Messages collection
        self.db.messages.create_index([("message_uuid", ASCENDING)], unique=True)
        self.db.messages.create_index([("conversation_id", ASCENDING)])
        self.db.messages.create_index([("sender_id", ASCENDING)])
        self.db.messages.create_index([("recipient_id", ASCENDING)])

        # Message fragments collection: unique compound index on message_uuid + fragment_index
        self.db.message_fragments.create_index(
            [("message_uuid", ASCENDING), ("fragment_index", ASCENDING)],
            unique=True
        )

        # Message shares collection: unique compound index on message_uuid + share_index
        self.db.message_shares.create_index(
            [("message_uuid", ASCENDING), ("share_index", ASCENDING)],
            unique=True
        )

        # Conversation links collection
        self.db.conversation_links.create_index([("token", ASCENDING)], unique=True)

        # Images collection
        self.db.images.create_index([("image_id", ASCENDING)], unique=True)
        self.db.images.create_index([("conversation_id", ASCENDING)])
        self.db.images.create_index([("expires_at", ASCENDING)])

    @property
    def users(self):
        return self.db.users

    @property
    def conversations(self):
        return self.db.conversations

    @property
    def images(self):
        return self.db.images

    @property
    def messages(self):
        return self.db.messages

    @property
    def message_fragments(self):
        return self.db.message_fragments

    @property
    def message_shares(self):
        return self.db.message_shares

    @property
    def conversation_links(self):
        return self.db.conversation_links


# Singleton instance
mongo = MongoDB()
db = mongo  # Alias for compatibility
