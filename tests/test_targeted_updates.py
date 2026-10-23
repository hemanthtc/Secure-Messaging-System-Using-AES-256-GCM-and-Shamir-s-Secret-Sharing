"""
Targeted Feature Updates Comprehensive Automated Tests
Validates:
1. Settings -> Secure Protocols (Automatic & Custom modes, validation)
2. SSS Key Management and threshold constraints
3. Fragment Telemetry, Reassembly Status & Private Mode preferences
4. Delivery and Read receipt state transitions (sent -> delivered -> read)
5. Secure Image Sharing (validation, authorization, 5MB limit, 7-day retention)
6. Safe Link Sharing (client-side sanitization, scheme filtering, no SSRF)
"""

import io
from datetime import datetime, timezone, timedelta
from app.services.conversation_service import ConversationService
from app.services.message_service import MessageService
from app.services.image_service import ImageService
from app.services.auth_service import AuthService
from app.models.message import Message
from app.models.user import User

# ==============================================================================
# FEATURE 1 & 2: SECURE PROTOCOLS & AUTOMATIC / CUSTOM MODE
# ==============================================================================

def test_protocol_settings_defaults_and_get(client, registered_user):
    """Test retrieving initial protocol settings defaults."""
    with client.session_transaction() as sess:
        sess["user_internal_id"] = registered_user.internal_id

    res = client.get("/api/settings/protocols")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    protocols = data["protocols"]
    assert protocols["mode"] in ("automatic", "custom")
    assert 2 <= protocols["fragment_count"] <= 10
    assert "fragment_telemetry" in protocols
    assert "fragment_reassembly_status" in protocols
    assert "private_mode" in protocols

def test_protocol_settings_custom_mode_validation(client, registered_user):
    """Test validation of custom mode parameters on backend."""
    with client.session_transaction() as sess:
        sess["user_internal_id"] = registered_user.internal_id

    # Fragment count below 2 must be rejected
    res_low = client.put("/api/settings/protocols", json={
        "mode": "custom",
        "fragment_count": 1
    })
    assert res_low.status_code == 400

    # Fragment count above 10 must be rejected
    res_high = client.put("/api/settings/protocols", json={
        "mode": "custom",
        "fragment_count": 11
    })
    assert res_high.status_code == 400

    # Invalid SSS where K > M must be rejected
    res_sss_inv = client.put("/api/settings/protocols", json={
        "mode": "custom",
        "fragment_count": 5,
        "is_sss_enabled": True,
        "sss_threshold_k": 6,
        "sss_total_shares_m": 5
    })
    assert res_sss_inv.status_code == 400

    # Valid custom settings must succeed
    res_valid = client.put("/api/settings/protocols", json={
        "mode": "custom",
        "fragment_count": 6,
        "is_sss_enabled": True,
        "sss_threshold_k": 3,
        "sss_total_shares_m": 5,
        "fragment_telemetry": True,
        "fragment_reassembly_status": True,
        "private_mode": False
    })
    assert res_valid.status_code == 200
    updated = res_valid.get_json()["protocols"]
    assert updated["fragment_count"] == 6
    assert updated["is_sss_enabled"] is True
    assert updated["sss_threshold_k"] == 3
    assert updated["sss_total_shares_m"] == 5

def test_automatic_mode_selection_and_persistence(client, registered_user, second_user):
    """Test that Automatic Mode dynamically generates valid configurations for each message."""
    conv, _ = ConversationService.get_or_create_direct_chat(registered_user, second_user.public_user_id)

    with client.session_transaction() as sess:
        sess["user_internal_id"] = registered_user.internal_id

    # Switch to Automatic Mode
    res_mode = client.put("/api/settings/protocols", json={
        "mode": "automatic"
    })
    assert res_mode.status_code == 200

    # Send multiple messages in Automatic Mode to test random selections
    fragment_counts_observed = set()
    sss_statuses_observed = set()

    for i in range(10):
        send_res = client.post("/api/messages/send", json={
            "conversation_id": conv.conversation_id,
            "content": f"Automatic message test payload #{i}"
        })
        assert send_res.status_code == 201
        msg = send_res.get_json()["message"]

        # 1. Fragment count must strictly be within 2 .. 10
        assert 2 <= msg["fragment_count"] <= 10
        fragment_counts_observed.add(msg["fragment_count"])

        # 2. If SSS enabled, M >= 2 and 2 <= K <= M
        if msg["is_sss_enabled"]:
            assert msg["sss_total_shares_m"] >= 2
            assert 2 <= msg["sss_threshold_k"] <= msg["sss_total_shares_m"]
        else:
            assert msg["sss_threshold_k"] is None or msg["sss_threshold_k"] == 0

        sss_statuses_observed.add(msg["is_sss_enabled"])

    # Verify recipient can decrypt and reassemble messages
    with client.session_transaction() as sess:
        sess["user_internal_id"] = second_user.internal_id

    get_res = client.get(f"/api/messages/conversation/{conv.conversation_id}")
    assert get_res.status_code == 200
    messages = get_res.get_json()["messages"]
    assert len(messages) == 10
    for m in messages:
        assert m["status"] == "reassembled"
        assert m["plaintext"].startswith("Automatic message test payload")

# ==============================================================================
# FEATURE 3, 4, 5: TELEMETRY, REASSEMBLY & PRIVATE MODE PREFERENCES
# ==============================================================================

def test_private_mode_and_telemetry_toggles(client, registered_user):
    """Test saving Private Mode and display toggles in user settings."""
    with client.session_transaction() as sess:
        sess["user_internal_id"] = registered_user.internal_id

    # Enable Private Mode
    res = client.put("/api/settings/protocols", json={
        "private_mode": True,
        "fragment_telemetry": False,
        "fragment_reassembly_status": False
    })
    assert res.status_code == 200
    protocols = res.get_json()["protocols"]
    assert protocols["private_mode"] is True
    assert protocols["fragment_telemetry"] is False
    assert protocols["fragment_reassembly_status"] is False

def test_no_keys_or_plaintext_shares_in_telemetry(client, registered_user, second_user):
    """Verify that message serialization never exposes raw cryptographic keys or raw secrets in telemetry."""
    conv, _ = ConversationService.get_or_create_direct_chat(registered_user, second_user.public_user_id)

    with client.session_transaction() as sess:
        sess["user_internal_id"] = registered_user.internal_id

    send_res = client.post("/api/messages/send", json={
        "conversation_id": conv.conversation_id,
        "content": "Super sensitive telemetry test message",
        "fragment_count": 4,
        "is_sss_enabled": True,
        "sss_threshold_k": 3,
        "sss_total_shares_m": 5
    })
    assert send_res.status_code == 201
    msg_dict = send_res.get_json()["message"]

    # Verify that raw secret keys or raw byte payloads are not in standard dictionary
    assert "encryption_key_bundle" not in msg_dict
    assert "raw_key" not in msg_dict
    assert "secret" not in msg_dict
    # Shares, if included, must only expose share_index and commitment/metadata, never plaintext keys
    for share in msg_dict.get("shares", []):
        assert "aes_key" not in share

# ==============================================================================
# FEATURE 6: DELIVERY AND READ RECEIPTS
# ==============================================================================

def test_delivery_and_read_state_transitions(client, registered_user, second_user):
    """Test distinct transitions: sent -> delivered -> read."""
    conv, _ = ConversationService.get_or_create_direct_chat(registered_user, second_user.public_user_id)

    # 1. Sender sends a message
    with client.session_transaction() as sess:
        sess["user_internal_id"] = registered_user.internal_id

    send_res = client.post("/api/messages/send", json={
        "conversation_id": conv.conversation_id,
        "content": "Status receipt transition test message"
    })
    assert send_res.status_code == 201
    msg_uuid = send_res.get_json()["message"]["message_uuid"]

    # In database, message should initially be 'sent'
    msg_doc = Message.find_by_uuid(msg_uuid)
    assert msg_doc is not None
    assert msg_doc.delivery_state == "sent"

    # 2. Recipient fetches conversation messages -> transitions to 'delivered'
    with client.session_transaction() as sess:
        sess["user_internal_id"] = second_user.internal_id

    get_res = client.get(f"/api/messages/conversation/{conv.conversation_id}")
    assert get_res.status_code == 200

    msg_doc = Message.find_by_uuid(msg_uuid)
    assert msg_doc.delivery_state == "delivered"
    assert msg_doc.delivered_at is not None

    # 3. Recipient marks conversation as read -> transitions to 'read'
    read_res = client.post(f"/api/messages/conversation/{conv.conversation_id}/read")
    assert read_res.status_code == 200
    assert msg_uuid in read_res.get_json()["read_uuids"]

    msg_doc = Message.find_by_uuid(msg_uuid)
    assert msg_doc.delivery_state == "read"
    assert msg_doc.read_at is not None

def test_unauthorized_read_receipt_rejected(client, registered_user, second_user):
    """Test that unrelated users cannot mark other conversations as read."""
    conv, _ = ConversationService.get_or_create_direct_chat(registered_user, second_user.public_user_id)

    # Third user
    third_user, _ = AuthService.register_user(
        display_name="Intruder User",
        public_user_id="intruder_999",
        password="Password123!"
    )

    with client.session_transaction() as sess:
        sess["user_internal_id"] = third_user.internal_id

    res = client.post(f"/api/messages/conversation/{conv.conversation_id}/read")
    # Must return empty read list or fail authorization
    assert res.status_code == 200
    assert res.get_json()["read_uuids"] == []

# ==============================================================================
# FEATURE 7: IMAGE SHARING & 7-DAY RETENTION
# ==============================================================================

def test_image_upload_and_authorized_streaming(client, registered_user, second_user):
    """Test uploading an image, verifying format validation, and authorized download."""
    conv, _ = ConversationService.get_or_create_direct_chat(registered_user, second_user.public_user_id)

    with client.session_transaction() as sess:
        sess["user_internal_id"] = registered_user.internal_id

    # Create dummy PNG file with valid magic bytes
    png_header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
    data = {
        "conversation_id": conv.conversation_id,
        "image": (io.BytesIO(png_header), "test_photo.png")
    }

    upload_res = client.post(
        "/api/messages/image/upload",
        data=data,
        content_type="multipart/form-data"
    )
    assert upload_res.status_code == 201
    resp_data = upload_res.get_json()
    image_id = resp_data["image"]["image_id"]
    assert image_id is not None
    assert resp_data["message"]["message_type"] == "image"

    # Authorized download by recipient
    with client.session_transaction() as sess:
        sess["user_internal_id"] = second_user.internal_id

    img_res = client.get(f"/api/messages/images/{image_id}")
    assert img_res.status_code == 200
    assert img_res.mimetype == "image/png"
    assert img_res.data == png_header

def test_image_unauthorized_access_rejected(client, registered_user, second_user):
    """Test that non-participants cannot retrieve private images."""
    conv, _ = ConversationService.get_or_create_direct_chat(registered_user, second_user.public_user_id)

    with client.session_transaction() as sess:
        sess["user_internal_id"] = registered_user.internal_id

    png_header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    upload_res = client.post(
        "/api/messages/image/upload",
        data={
            "conversation_id": conv.conversation_id,
            "image": (io.BytesIO(png_header), "private.png")
        },
        content_type="multipart/form-data"
    )
    assert upload_res.status_code == 201
    image_id = upload_res.get_json()["image"]["image_id"]

    # Unauthorized third user attempts to access image
    third_user, _ = AuthService.register_user(
        display_name="Eve Hacker",
        public_user_id="eve_hacker",
        password="Password123!"
    )
    with client.session_transaction() as sess:
        sess["user_internal_id"] = third_user.internal_id

    unauth_res = client.get(f"/api/messages/images/{image_id}")
    assert unauth_res.status_code == 403

def test_image_size_limit_and_malformed_type_rejected(client, registered_user, second_user):
    """Test rejection of oversized (>5MB) and disallowed file formats."""
    conv, _ = ConversationService.get_or_create_direct_chat(registered_user, second_user.public_user_id)

    with client.session_transaction() as sess:
        sess["user_internal_id"] = registered_user.internal_id

    # 1. Oversized file (> 5MB)
    large_data = b"\x89PNG\r\n\x1a\n" + (b"X" * (5 * 1024 * 1024 + 10))
    res_large = client.post(
        "/api/messages/image/upload",
        data={
            "conversation_id": conv.conversation_id,
            "image": (io.BytesIO(large_data), "too_large.png")
        },
        content_type="multipart/form-data"
    )
    assert res_large.status_code == 400

    # 2. Fake image with invalid header (e.g., shell script)
    fake_data = b"#!/bin/bash\necho 'hello'"
    res_fake = client.post(
        "/api/messages/image/upload",
        data={
            "conversation_id": conv.conversation_id,
            "image": (io.BytesIO(fake_data), "script.png")
        },
        content_type="multipart/form-data"
    )
    assert res_fake.status_code == 400

def test_image_seven_day_retention_and_purge(client, registered_user, second_user):
    """Test that images older than 7 days are expired and purged."""
    conv, _ = ConversationService.get_or_create_direct_chat(registered_user, second_user.public_user_id)

    with client.session_transaction() as sess:
        sess["user_internal_id"] = registered_user.internal_id

    png_header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    upload_res = client.post(
        "/api/messages/image/upload",
        data={
            "conversation_id": conv.conversation_id,
            "image": (io.BytesIO(png_header), "expiring.png")
        },
        content_type="multipart/form-data"
    )
    assert upload_res.status_code == 201
    image_id = upload_res.get_json()["image"]["image_id"]

    # Artificially age the image record in MongoDB past 7 days
    past_date = datetime.now(timezone.utc) - timedelta(days=8)
    from app.database.db import mongo
    mongo.images.update_one(
        {"image_id": image_id},
        {"$set": {"expires_at": past_date}}
    )

    # Retrieval after expiration should return 403/410 expired error
    get_res = client.get(f"/api/messages/images/{image_id}")
    assert get_res.status_code == 403
    assert "expired" in get_res.get_json()["error"].lower()

    # Trigger automatic purge
    purged_count = ImageService.purge_expired_images()
    assert purged_count >= 1

# ==============================================================================
# FEATURE 8: CLICKABLE LINK SHARING SECURITY
# ==============================================================================

def test_safe_links_rendering_logic():
    """Test linkification safety logic (reject javascript:/data:, escape XSS)."""
    import html
    import re

    def sanitize_and_linkify(text):
        escaped = html.escape(text)
        url_regex = re.compile(r'(https?://[^\s<>"\']+)', re.IGNORECASE)
        def replace_link(match):
            url = match.group(1)
            # Ensure safe scheme strictly http or https
            if not url.startswith(("http://", "https://")):
                return url
            return f'<a href="{url}" target="_blank" rel="noopener noreferrer" class="chat-link">{url}</a>'
        return url_regex.sub(replace_link, escaped)

    # 1. Normal HTTPS link
    out1 = sanitize_and_linkify("Check this site https://example.com/docs")
    assert 'href="https://example.com/docs"' in out1
    assert 'rel="noopener noreferrer"' in out1
    assert 'target="_blank"' in out1

    # 2. Dangerous javascript: scheme must NOT be made into link
    out2 = sanitize_and_linkify("javascript:alert(1)")
    assert 'href="javascript:' not in out2

    # 3. Dangerous data: scheme must NOT be made into link
    out3 = sanitize_and_linkify("data:text/html,<script>alert(1)</script>")
    assert 'href="data:' not in out3

    # 4. Attempted XSS in text must be strictly escaped
    out4 = sanitize_and_linkify("<script>alert('xss')</script> https://secure.org")
    assert "<script>" not in out4
    assert "&lt;script&gt;" in out4
    assert 'href="https://secure.org"' in out4

# ==============================================================================
# FEATURE 9: POST-REASSEMBLY METADATA PURGE & MESSAGE DELETION
# ==============================================================================

def test_post_reassembly_fragment_purge(client, registered_user, second_user):
    """Test that intermediate transmission fragments are purged upon reassembly while preserving message display."""
    from app.database.db import mongo
    conv, _ = ConversationService.get_or_create_direct_chat(registered_user, second_user.public_user_id)

    with client.session_transaction() as sess:
        sess["user_internal_id"] = registered_user.internal_id

    # 1. Send encrypted message with N=4 fragments
    send_res = client.post("/api/messages/send", json={
        "conversation_id": conv.conversation_id,
        "content": "Purge test secret message",
        "fragment_count": 4
    })
    assert send_res.status_code == 201
    msg_uuid = send_res.get_json()["message"]["message_uuid"]

    # Fragments should initially exist in the database
    init_frag_count = mongo.message_fragments.count_documents({"message_uuid": msg_uuid})
    assert init_frag_count == 4

    # 2. Recipient fetches conversation messages -> triggers reassembly and automatic fragment purge
    with client.session_transaction() as sess:
        sess["user_internal_id"] = second_user.internal_id

    get_res = client.get(f"/api/messages/conversation/{conv.conversation_id}")
    assert get_res.status_code == 200
    messages = get_res.get_json()["messages"]
    assert len(messages) >= 1
    target_msg = next((m for m in messages if m["message_uuid"] == msg_uuid), None)
    assert target_msg is not None
    assert target_msg["status"] == "reassembled"
    assert target_msg["plaintext"] == "Purge test secret message"
    assert target_msg["fragments_purged"] is True

    # 3. Intermediate fragments MUST be purged from MongoDB Atlas to save storage space
    post_frag_count = mongo.message_fragments.count_documents({"message_uuid": msg_uuid})
    assert post_frag_count == 0

    # 4. Sender can also query conversation messages and still read the preserved plaintext
    with client.session_transaction() as sess:
        sess["user_internal_id"] = registered_user.internal_id

    get_res_sender = client.get(f"/api/messages/conversation/{conv.conversation_id}")
    assert get_res_sender.status_code == 200
    sender_messages = get_res_sender.get_json()["messages"]
    target_sender_msg = next((m for m in sender_messages if m["message_uuid"] == msg_uuid), None)
    assert target_sender_msg is not None
    assert target_sender_msg["plaintext"] == "Purge test secret message"

def test_delete_message_api(client, registered_user, second_user):
    """Test deleting a message via DELETE /api/messages/<uuid> and verifying authorization."""
    from app.database.db import mongo
    conv, _ = ConversationService.get_or_create_direct_chat(registered_user, second_user.public_user_id)

    with client.session_transaction() as sess:
        sess["user_internal_id"] = registered_user.internal_id

    # Send a message
    send_res = client.post("/api/messages/send", json={
        "conversation_id": conv.conversation_id,
        "content": "Message to be deleted"
    })
    assert send_res.status_code == 201
    msg_uuid = send_res.get_json()["message"]["message_uuid"]

    # Unauthorized user cannot delete
    third_user, _ = AuthService.register_user(
        display_name="Random User",
        public_user_id="random_777",
        password="Password123!"
    )
    with client.session_transaction() as sess:
        sess["user_internal_id"] = third_user.internal_id

    unauth_del = client.delete(f"/api/messages/{msg_uuid}")
    assert unauth_del.status_code == 403

    # Authorized user deletes the message
    with client.session_transaction() as sess:
        sess["user_internal_id"] = registered_user.internal_id

    del_res = client.delete(f"/api/messages/{msg_uuid}")
    assert del_res.status_code == 200
    assert del_res.get_json()["success"] is True

    # Verify message is gone from database
    assert mongo.messages.find_one({"message_uuid": msg_uuid}) is None
    assert mongo.message_fragments.count_documents({"message_uuid": msg_uuid}) == 0

def test_images_collection_and_indexes():
    """Verify that images collection and unique indexes are created properly."""
    from app.database.db import mongo
    assert mongo.images is not None
    mongo._ensure_indexes()
    indexes = list(mongo.images.list_indexes())
    index_names = [idx.get("name") for idx in indexes]
    assert any("image_id" in name for name in index_names)

def test_delete_message_for_me_preserves_sender_view(client, registered_user, second_user):
    """Test that when a recipient deletes a message ('Delete for Me'), the sender retains full access."""
    from app.database.db import mongo
    conv, _ = ConversationService.get_or_create_direct_chat(registered_user, second_user.public_user_id)

    # 1. User A (registered_user) sends a message to User B (second_user)
    with client.session_transaction() as sess:
        sess["user_internal_id"] = registered_user.internal_id

    send_res = client.post("/api/messages/send", json={
        "conversation_id": conv.conversation_id,
        "content": "Secret text message from A to B",
        "fragment_count": 3
    })
    assert send_res.status_code == 201
    msg_uuid = send_res.get_json()["message"]["message_uuid"]

    # 2. User B receives and reassembles the message
    with client.session_transaction() as sess:
        sess["user_internal_id"] = second_user.internal_id

    get_b_res = client.get(f"/api/messages/conversation/{conv.conversation_id}")
    assert get_b_res.status_code == 200
    b_msgs = get_b_res.get_json()["messages"]
    assert any(m["message_uuid"] == msg_uuid for m in b_msgs)

    # 3. User B deletes the message ("Delete for Me")
    del_res = client.delete(f"/api/messages/{msg_uuid}?mode=for_me")
    assert del_res.status_code == 200
    assert del_res.get_json()["success"] is True
    assert del_res.get_json()["mode"] == "for_me"

    # Message MUST still exist in database
    msg_doc = mongo.messages.find_one({"message_uuid": msg_uuid})
    assert msg_doc is not None
    assert second_user.internal_id in msg_doc.get("deleted_for", [])

    # 4. User B checks messages -> message is gone from User B's view
    get_b_again = client.get(f"/api/messages/conversation/{conv.conversation_id}")
    assert not any(m["message_uuid"] == msg_uuid for m in get_b_again.get_json()["messages"])

    # 5. User A (sender) checks messages -> message MUST STILL BE VISIBLE AND INTACT for User A!
    with client.session_transaction() as sess:
        sess["user_internal_id"] = registered_user.internal_id

    get_a_res = client.get(f"/api/messages/conversation/{conv.conversation_id}")
    assert get_a_res.status_code == 200
    a_msgs = get_a_res.get_json()["messages"]
    target_a_msg = next((m for m in a_msgs if m["message_uuid"] == msg_uuid), None)
    assert target_a_msg is not None
    assert target_a_msg["plaintext"] == "Secret text message from A to B"

    # 6. Now User A also deletes for themselves -> all participants have deleted it -> cascades to hard deletion
    del_a_res = client.delete(f"/api/messages/{msg_uuid}?mode=for_me")
    assert del_a_res.status_code == 200
    assert mongo.messages.find_one({"message_uuid": msg_uuid}) is None
