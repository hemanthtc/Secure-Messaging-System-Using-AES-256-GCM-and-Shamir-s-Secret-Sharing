"""
Account Management and Deletion Automated Tests
Tests password changes, confirmation requirements, and hard deletion cascade.
"""

from app.models.user import User
from app.models.message import Message
from app.models.message_fragment import MessageFragment
from app.services.conversation_service import ConversationService
from app.services.message_service import MessageService

def test_password_change_success(client, registered_user):
    """Test updating user password with valid current credentials."""
    with client.session_transaction() as sess:
        sess["user_internal_id"] = registered_user.internal_id

    res = client.post("/api/settings/password", json={
        "current_password": "SecurePassword123!",
        "new_password": "BrandNewPassword456!"
    })
    assert res.status_code == 200

    # Verify new password authenticates
    from app.services.auth_service import AuthService
    authed_user, err = AuthService.authenticate_user(
        "Hemanth Kumar",
        "hemanth_101",
        "BrandNewPassword456!"
    )
    assert authed_user is not None
    assert err is None

def test_account_deletion_with_wrong_password_rejected(client, registered_user):
    """Test that account deletion with invalid password confirmation is rejected."""
    with client.session_transaction() as sess:
        sess["user_internal_id"] = registered_user.internal_id

    res = client.delete("/api/settings/account", json={
        "confirmation_password": "WrongPassword!"
    })
    assert res.status_code == 400
    assert "incorrect password" in res.get_json()["error"]
    assert User.find_by_internal_id(registered_user.internal_id) is not None

def test_account_hard_deletion_cascade(client, registered_user, second_user):
    """Test permanent account deletion cascades and deletes all sent messages and fragments."""
    # 1. Establish chat and send a message with 3 fragments
    conv, _ = ConversationService.get_or_create_direct_chat(registered_user, second_user.public_user_id)
    msg_dict, _ = MessageService.send_message(
        conversation_id=conv.conversation_id,
        sender=registered_user,
        content="Sensitive message that must be permanently wiped upon account deletion.",
        fragment_count=3
    )
    msg_uuid = msg_dict["message_uuid"]

    # Verify message and fragments exist in database
    assert Message.find_by_uuid(msg_uuid) is not None
    assert MessageFragment.count_for_message(msg_uuid) == 3

    # 2. Execute hard account deletion
    with client.session_transaction() as sess:
        sess["user_internal_id"] = registered_user.internal_id

    del_res = client.delete("/api/settings/account", json={
        "confirmation_password": "SecurePassword123!"
    })
    assert del_res.status_code == 200

    # 3. Verify user is erased
    assert User.find_by_internal_id(registered_user.internal_id) is None

    # 4. Verify message and fragments are completely erased
    assert Message.find_by_uuid(msg_uuid) is None
    assert MessageFragment.count_for_message(msg_uuid) == 0
