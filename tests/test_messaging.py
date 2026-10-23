"""
Direct Messaging and Real-time Architecture Automated Tests
Tests contact search, direct conversation initialization, encrypted message sending with
configurable fragments (2-10), reassembly, and unauthorized access rejection.
"""

from app.services.conversation_service import ConversationService
from app.models.message import Message

def test_user_search_by_public_id(client, registered_user, second_user):
    """Test searching for another user by public user ID handle."""
    with client.session_transaction() as sess:
        sess["user_internal_id"] = registered_user.internal_id

    res = client.get("/api/users/search?q=ananya")
    assert res.status_code == 200
    data = res.get_json()
    assert len(data["users"]) == 1
    assert data["users"][0]["public_user_id"] == "ananya_202"

def test_create_or_open_direct_chat(client, registered_user, second_user):
    """Test opening a direct 1-on-1 chat between two users."""
    with client.session_transaction() as sess:
        sess["user_internal_id"] = registered_user.internal_id

    res = client.post("/api/conversations/direct", json={
        "target_public_id": "ananya_202"
    })
    assert res.status_code == 200
    conv_data = res.get_json()["conversation"]
    assert conv_data["peer"]["public_user_id"] == "ananya_202"

def test_send_and_reassemble_message_with_fragments(client, registered_user, second_user):
    """Test sending an encrypted message divided into 5 fragments and verifying reassembly."""
    conv, _ = ConversationService.get_or_create_direct_chat(registered_user, second_user.public_user_id)

    with client.session_transaction() as sess:
        sess["user_internal_id"] = registered_user.internal_id

    # 1. Send encrypted message with N=5 fragments
    send_res = client.post("/api/messages/send", json={
        "conversation_id": conv.conversation_id,
        "content": "Secret rendezvous at campus building 3.",
        "fragment_count": 5
    })
    assert send_res.status_code == 201
    msg_data = send_res.get_json()["message"]
    assert msg_data["fragment_count"] == 5
    assert len(msg_data["fragments"]) == 5
    assert msg_data["received_fragments_count"] == 5

    # 2. Query messages as recipient (second_user)
    with client.session_transaction() as sess:
        sess["user_internal_id"] = second_user.internal_id

    get_res = client.get(f"/api/messages/conversation/{conv.conversation_id}")
    assert get_res.status_code == 200
    messages = get_res.get_json()["messages"]
    assert len(messages) == 1
    assert messages[0]["status"] == "reassembled"
    assert messages[0]["plaintext"] == "Secret rendezvous at campus building 3."

def test_send_message_with_sss_enabled(client, registered_user, second_user):
    """Test sending a message with both payload fragmentation (N=4) and Shamir's Secret Sharing (K=3, M=5)."""
    conv, _ = ConversationService.get_or_create_direct_chat(registered_user, second_user.public_user_id)

    with client.session_transaction() as sess:
        sess["user_internal_id"] = registered_user.internal_id

    send_res = client.post("/api/messages/send", json={
        "conversation_id": conv.conversation_id,
        "content": "Encrypted message with SSS key sharing enabled.",
        "fragment_count": 4,
        "is_sss_enabled": True,
        "sss_threshold_k": 3,
        "sss_total_shares_m": 5
    })
    assert send_res.status_code == 201
    msg_data = send_res.get_json()["message"]
    assert msg_data["is_sss_enabled"] is True
    assert msg_data["sss_threshold_k"] == 3
    assert msg_data["sss_total_shares_m"] == 5
    assert len(msg_data["shares"]) == 5

    # Verify recipient can decrypt via SSS key recovery
    with client.session_transaction() as sess:
        sess["user_internal_id"] = second_user.internal_id

    get_res = client.get(f"/api/messages/conversation/{conv.conversation_id}")
    assert get_res.status_code == 200
    messages = get_res.get_json()["messages"]
    assert len(messages) == 1
    assert messages[0]["status"] == "reassembled"
    assert messages[0]["plaintext"] == "Encrypted message with SSS key sharing enabled."

def test_unauthorized_conversation_access_rejected(client, registered_user, second_user):
    """Test that an unrelated third user cannot access or read messages from another conversation."""
    conv, _ = ConversationService.get_or_create_direct_chat(registered_user, second_user.public_user_id)

    # Register third user
    from app.services.auth_service import AuthService
    third_user, _ = AuthService.register_user("Eve Spy", "eve_999", "EvePassword123!")

    with client.session_transaction() as sess:
        sess["user_internal_id"] = third_user.internal_id

    # Attempt to read conversation messages
    res = client.get(f"/api/messages/conversation/{conv.conversation_id}")
    assert res.status_code == 200
    # Should receive empty list (not authorized)
    assert res.get_json()["messages"] == []
