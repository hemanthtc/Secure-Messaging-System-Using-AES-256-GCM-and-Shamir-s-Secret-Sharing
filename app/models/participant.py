"""
Participant Model Definition
Associates users with conversations using unique constraints on (conversation_id, user_id).
"""

from datetime import datetime, timezone
from app.database.db import db

class Participant(db.Model):
    """Participant mapping table between User and Conversation."""
    __tablename__ = "participants"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    conversation_id = db.Column(
        db.Integer,
        db.ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    joined_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("conversation_id", "user_id", name="uq_conversation_participant"),
    )

    def __repr__(self):
        return f"<Participant conv_id={self.conversation_id} user_id={self.user_id}>"
