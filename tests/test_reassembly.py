"""
Reassembly Algorithm Automated Tests
Tests exact reconstruction, out-of-order arrival, duplicate deduplication,
missing fragment detection, conflicting metadata rejection, and cross-message isolation.
"""

import random
from app.services.fragmentation_service import FragmentationService
from app.services.reassembly_service import ReassemblyService
from app.crypto.hashing import sha256_bytes

def test_exact_reconstruction():
    """Test full sequential fragment reassembly matches original payload exactly."""
    payload = b"Exact byte-for-byte reconstruction verification."
    msg_id = "msg-exact-1"
    fragments = FragmentationService.fragment_payload(payload, 5, msg_id)
    expected_hash = sha256_bytes(payload)

    res = ReassemblyService.reassemble_fragments(fragments, expected_total=5, expected_hash=expected_hash)
    assert res["is_complete"] is True
    assert res["status"] == "COMPLETE"
    assert res["reassembled_bytes"] == payload
    assert res["received_count"] == 5

def test_out_of_order_delivery():
    """Test fragments arriving out of order (e.g. index 3, then 1, then 2)."""
    payload = b"Testing out-of-order packet arrival handling."
    msg_id = "msg-ooo-1"
    fragments = FragmentationService.fragment_payload(payload, 6, msg_id)

    # Shuffle fragments out of order
    shuffled = fragments.copy()
    random.seed(42)
    random.shuffle(shuffled)
    assert [f["fragment_index"] for f in shuffled] != [1, 2, 3, 4, 5, 6]

    res = ReassemblyService.reassemble_fragments(shuffled, expected_total=6)
    assert res["is_complete"] is True
    assert res["status"] == "COMPLETE"
    assert res["reassembled_bytes"] == payload

def test_duplicate_fragments_ignored():
    """Test that receiving duplicate fragments does not corrupt reassembly or inflate count."""
    payload = b"Deduplicating multiple arrivals."
    msg_id = "msg-dup-1"
    fragments = FragmentationService.fragment_payload(payload, 3, msg_id)

    # Duplicate fragment 2 three times
    with_duplicates = [fragments[0], fragments[1], fragments[1], fragments[1], fragments[2]]
    res = ReassemblyService.reassemble_fragments(with_duplicates, expected_total=3)
    assert res["is_complete"] is True
    assert res["received_count"] == 3
    assert res["reassembled_bytes"] == payload

def test_missing_fragments_detected():
    """Test that missing fragments prevent reassembly and report correct missing indices."""
    payload = b"Missing fragment detection test."
    msg_id = "msg-missing-1"
    fragments = FragmentationService.fragment_payload(payload, 5, msg_id)

    # Deliver only fragments 1, 2, 4 (missing 3 and 5)
    subset = [fragments[0], fragments[1], fragments[3]]
    res = ReassemblyService.reassemble_fragments(subset, expected_total=5)

    assert res["is_complete"] is False
    assert res["status"] == "WAITING_FOR_MISSING_FRAGMENTS"
    assert res["received_count"] == 3
    assert res["missing_indexes"] == [3, 5]
    assert res["reassembled_bytes"] is None

def test_conflicting_fragment_metadata_rejected():
    """Test that conflicting total_fragments metadata across fragments is rejected."""
    payload = b"Metadata conflict test."
    msg_id = "msg-conflict-1"
    fragments = FragmentationService.fragment_payload(payload, 4, msg_id)

    # Corrupt total_fragments metadata on fragment 2
    corrupted_fragments = [dict(f) for f in fragments]
    corrupted_fragments[1]["total_fragments"] = 6

    res = ReassemblyService.reassemble_fragments(corrupted_fragments, expected_total=4)
    assert res["is_complete"] is False
    assert res["status"] == "ERROR"
    assert "Conflicting total" in res["error_message"]

def test_cross_message_fragment_rejection():
    """Test that combining fragments from different messages is strictly rejected."""
    payload1 = b"Message 1 payload."
    payload2 = b"Message 2 payload."
    fragments1 = FragmentationService.fragment_payload(payload1, 3, "msg-111")
    fragments2 = FragmentationService.fragment_payload(payload2, 3, "msg-222")

    # Mix fragment from message 2 into message 1
    mixed = [fragments1[0], fragments2[1], fragments1[2]]
    res = ReassemblyService.reassemble_fragments(mixed, expected_total=3)

    assert res["is_complete"] is False
    assert res["status"] == "ERROR"
    assert "Cross-message fragment rejection" in res["error_message"]

def test_reassembled_hash_tampering_rejected():
    """Test that tampered fragment byte altering total hash is rejected."""
    payload = b"Tampering test."
    msg_id = "msg-tamper-1"
    fragments = FragmentationService.fragment_payload(payload, 3, msg_id)
    expected_hash = sha256_bytes(payload)

    # Tamper payload of fragment 1 (without updating hash)
    corrupted = [dict(f) for f in fragments]
    corrupted[0]["payload_bytes"] = b"X" * len(corrupted[0]["payload_bytes"])

    res = ReassemblyService.reassemble_fragments(corrupted, expected_total=3, expected_hash=expected_hash)
    assert res["is_complete"] is False
    assert res["status"] == "ERROR"
