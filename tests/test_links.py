"""
Shareable Links Automated Tests
Tests public profile links (/u/<public_id>) and conversation navigation tokens.
"""

from app.services.conversation_service import ConversationService
from app.services.link_service import LinkService

def test_unauthenticated_profile_link_shows_public_badge(client, registered_user):
    """Test that visiting a profile link while unauthenticated displays the public profile view."""
    res = client.get(f"/u/{registered_user.public_user_id}")
    assert res.status_code == 200
    assert registered_user.display_name.encode("utf-8") in res.data
    assert b"Log In or Register to Chat" in res.data

def test_authenticated_profile_link_initiates_direct_chat(client, registered_user, second_user):
    """Test that an authenticated user navigating to /u/<peer_id> is redirected directly to a chat session."""
    with client.session_transaction() as sess:
        sess["user_internal_id"] = registered_user.internal_id

    res = client.get(f"/u/{second_user.public_user_id}")
    assert res.status_code == 302
    assert "/chat" in res.headers["Location"]

def test_conversation_link_generation_and_navigation(client, registered_user, second_user):
    """Test creating and resolving an authorized conversation navigation token."""
    conv, _ = ConversationService.get_or_create_direct_chat(registered_user, second_user.public_user_id)

    # 1. Generate link token
    with client.session_transaction() as sess:
        sess["user_internal_id"] = registered_user.internal_id

    res = client.post(f"/api/links/conversation/{conv.conversation_id}")
    assert res.status_code == 200
    token = res.get_json()["token"]
    assert token is not None

    # 2. Access link as second_user
    with client.session_transaction() as sess:
        sess["user_internal_id"] = second_user.internal_id

    link_res = client.get(f"/chat/link/{token}")
    assert link_res.status_code == 302
    assert f"conv={conv.conversation_id}" in link_res.headers["Location"]
