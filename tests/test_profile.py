"""
Profile Management Automated Tests
Verifies profile editing, public user ID updates, permanent internal ID immutability,
and preservation of existing conversations.
"""

from app.models.user import User
from app.services.conversation_service import ConversationService

def test_profile_editing_display_name(client, registered_user):
    """Test updating display name."""
    with client.session_transaction() as sess:
        sess["user_internal_id"] = registered_user.internal_id

    res = client.put("/api/profile", json={
        "display_name": "Hemanth K. Updated",
        "public_user_id": "hemanth_101"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["user"]["display_name"] == "Hemanth K. Updated"

    updated = User.find_by_internal_id(registered_user.internal_id)
    assert updated.display_name == "Hemanth K. Updated"
    assert updated.internal_id == registered_user.internal_id

def test_public_id_change_preserves_internal_id(client, registered_user):
    """Test updating public user ID while ensuring permanent internal ID remains unchanged."""
    old_internal_id = registered_user.internal_id

    with client.session_transaction() as sess:
        sess["user_internal_id"] = old_internal_id

    res = client.put("/api/profile", json={
        "display_name": registered_user.display_name,
        "public_user_id": "hemanth_new_handle"
    })
    assert res.status_code == 200

    updated = User.find_by_internal_id(old_internal_id)
    assert updated.public_user_id == "hemanth_new_handle"
    assert updated.internal_id == old_internal_id  # Immutable permanent ID preserved!

def test_public_id_duplicate_change_rejected(client, registered_user, second_user):
    """Test that changing public ID to an already existing user's public ID is rejected."""
    with client.session_transaction() as sess:
        sess["user_internal_id"] = registered_user.internal_id

    res = client.put("/api/profile", json={
        "display_name": registered_user.display_name,
        "public_user_id": second_user.public_user_id  # Already belongs to second_user!
    })
    assert res.status_code == 400
    assert "already taken" in res.get_json()["error"]

def test_conversation_preservation_after_public_id_change(client, registered_user, second_user):
    """Test that existing conversations continue to function seamlessly after a public ID change."""
    # Establish direct conversation
    conv, _ = ConversationService.get_or_create_direct_chat(registered_user, second_user.public_user_id)
    conv_id = conv.conversation_id

    # Change registered_user's public ID
    with client.session_transaction() as sess:
        sess["user_internal_id"] = registered_user.internal_id

    client.put("/api/profile", json={
        "display_name": registered_user.display_name,
        "public_user_id": "hemanth_brand_new_id"
    })

    # Verify conversation still exists and links both users
    retrieved_conv = ConversationService.get_conversation_for_user(conv_id, second_user)
    assert retrieved_conv is not None
    assert registered_user.internal_id in retrieved_conv.participants
    peer = retrieved_conv.get_other_participant(second_user.internal_id)
    assert peer.public_user_id == "hemanth_brand_new_id"
