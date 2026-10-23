"""
Fragmentation Algorithm Automated Tests
Tests fragmentation counts (2, 3, 5, 10), rejections (<2, >10, negative, decimal, non-integer),
and payload handling (empty, short, unicode, newlines).
"""

import pytest
from app.services.fragmentation_service import FragmentationService
from app.validators.fragment_validator import validate_fragment_count

@pytest.mark.parametrize("n", [2, 3, 5, 10])
def test_valid_fragment_counts(n):
    """Test valid fragment counts 2, 3, 5, 10."""
    is_valid, parsed_n, err = validate_fragment_count(n)
    assert is_valid is True
    assert parsed_n == n
    assert err is None

    # Test actual payload division
    payload = b"Hello, SecureShare Messenger Fragmentation Test!"
    fragments = FragmentationService.fragment_payload(payload, n, "msg-test-uuid")
    assert len(fragments) == n

    # Verify exact fragment count and sequential indexes 1 .. n
    for i, frag in enumerate(fragments, start=1):
        assert frag["fragment_index"] == i
        assert frag["total_fragments"] == n
        assert frag["message_uuid"] == "msg-test-uuid"

    # Verify exact byte preservation upon concatenation
    reassembled_bytes = b"".join(f["payload_bytes"] for f in fragments)
    assert reassembled_bytes == payload

def test_fragment_count_1_rejected():
    """Test that fragment count 1 is strictly rejected (minimum is 2)."""
    is_valid, parsed_n, err = validate_fragment_count(1)
    assert is_valid is False
    assert "too low" in err or "Minimum permitted is 2" in err

def test_fragment_count_11_rejected():
    """Test that fragment count 11 is strictly rejected (maximum is 10)."""
    is_valid, parsed_n, err = validate_fragment_count(11)
    assert is_valid is False
    assert "too high" in err or "Maximum permitted is 10" in err

def test_negative_fragment_counts_rejected():
    """Test that negative fragment counts are rejected."""
    is_valid, _, err = validate_fragment_count(-1)
    assert is_valid is False
    is_valid, _, err = validate_fragment_count("-5")
    assert is_valid is False

def test_decimal_fragment_counts_rejected():
    """Test that decimal and floating point fragment counts are strictly rejected."""
    is_valid, _, err = validate_fragment_count(3.5)
    assert is_valid is False
    assert "Decimal" in err

    is_valid, _, err = validate_fragment_count(3.0)
    assert is_valid is False

    is_valid, _, err = validate_fragment_count("3.5")
    assert is_valid is False

def test_empty_message_fragmentation():
    """Test fragmentation of empty payload."""
    payload = b""
    fragments = FragmentationService.fragment_payload(payload, 4, "msg-empty-uuid")
    assert len(fragments) == 4
    for frag in fragments:
        assert frag["payload_bytes"] == b""
    reassembled = b"".join(f["payload_bytes"] for f in fragments)
    assert reassembled == b""

def test_short_message_fragmentation():
    """Test fragmentation when payload length is smaller than fragment count N."""
    payload = b"AB"  # 2 bytes into 5 fragments
    fragments = FragmentationService.fragment_payload(payload, 5, "msg-short-uuid")
    assert len(fragments) == 5
    # First 2 fragments get 1 byte each, remaining 3 get 0 bytes
    assert fragments[0]["payload_bytes"] == b"A"
    assert fragments[1]["payload_bytes"] == b"B"
    assert fragments[2]["payload_bytes"] == b""
    assert fragments[3]["payload_bytes"] == b""
    assert fragments[4]["payload_bytes"] == b""
    reassembled = b"".join(f["payload_bytes"] for f in fragments)
    assert reassembled == payload

def test_unicode_message_fragmentation():
    """Test that complex Unicode strings (emojis, multilingual) are byte-preserved without corruption."""
    unicode_text = "SecureShare 🔐 🚀 नमस्ते दुनिया 你好世界 Привет мир"
    payload = unicode_text.encode("utf-8")
    fragments = FragmentationService.fragment_payload(payload, 7, "msg-unicode-uuid")
    assert len(fragments) == 7

    reassembled_bytes = b"".join(f["payload_bytes"] for f in fragments)
    decoded_text = reassembled_bytes.decode("utf-8")
    assert decoded_text == unicode_text

def test_messages_containing_newlines():
    """Test payload containing multiline newlines and escape sequences."""
    text_with_newlines = "Line 1: Header\nLine 2: Data\r\nLine 3: Final line\n\n\tTabbed"
    payload = text_with_newlines.encode("utf-8")
    fragments = FragmentationService.fragment_payload(payload, 5, "msg-newline-uuid")
    assert len(fragments) == 5

    reassembled_bytes = b"".join(f["payload_bytes"] for f in fragments)
    assert reassembled_bytes.decode("utf-8") == text_with_newlines
