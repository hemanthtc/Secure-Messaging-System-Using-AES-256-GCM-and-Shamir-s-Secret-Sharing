"""
Encryption and Cryptographic Verification Automated Tests
Tests AES-256-GCM encryption, decryption, authentication tag validation, and tampering rejection.
"""

import pytest
from app.crypto.encryption import encrypt_message, decrypt_message

def test_aes_256_gcm_encrypt_decrypt():
    """Test standard AES-256-GCM encryption and decryption cycle."""
    plaintext = "Secure academic direct message payload 🔒"
    enc = encrypt_message(plaintext)

    assert len(enc["key_bytes"]) == 32
    assert len(enc["nonce_bytes"]) == 12
    assert enc["ciphertext_bytes"] is not None

    decrypted = decrypt_message(
        enc["ciphertext_bytes"],
        enc["nonce_bytes"],
        enc["key_bytes"]
    )
    assert decrypted == plaintext

def test_encrypted_payload_tampering_rejected():
    """Test that modifying even a single byte of ciphertext causes AES-GCM tag verification to fail."""
    plaintext = "Top secret message content"
    enc = encrypt_message(plaintext)

    # Flip bits in ciphertext
    ciphertext_tampered = bytearray(enc["ciphertext_bytes"])
    ciphertext_tampered[0] ^= 0xFF

    with pytest.raises(ValueError, match="tampering detected|authentication tag mismatch"):
        decrypt_message(
            bytes(ciphertext_tampered),
            enc["nonce_bytes"],
            enc["key_bytes"]
        )

def test_modified_nonce_rejected():
    """Test that modifying the GCM nonce fails decryption."""
    plaintext = "Authentication nonce test"
    enc = encrypt_message(plaintext)

    nonce_tampered = bytearray(enc["nonce_bytes"])
    nonce_tampered[0] ^= 0x01

    with pytest.raises(ValueError, match="tampering detected|authentication tag mismatch"):
        decrypt_message(
            enc["ciphertext_bytes"],
            bytes(nonce_tampered),
            enc["key_bytes"]
        )

def test_wrong_key_rejected():
    """Test that supplying an incorrect 32-byte key fails authentication."""
    plaintext = "Wrong key test"
    enc = encrypt_message(plaintext)

    wrong_key = b"\x00" * 32
    with pytest.raises(ValueError, match="tampering detected|authentication tag mismatch"):
        decrypt_message(
            enc["ciphertext_bytes"],
            enc["nonce_bytes"],
            wrong_key
        )
