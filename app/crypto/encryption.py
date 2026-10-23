"""
Authenticated Encryption Module (AES-256-GCM)
Provides authenticated symmetric encryption and decryption with GCM integrity tags.
Plaintext messages are never stored in the database or logged.
"""

import base64
import os
from typing import Dict, Any, Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
from app.crypto.hashing import sha256_bytes

def encrypt_message(plaintext: str, key: Optional[bytes] = None) -> Dict[str, Any]:
    """
    Encrypt plaintext UTF-8 string using AES-256-GCM.
    Generates a cryptographically secure 12-byte nonce and 32-byte key (if not provided).
    Returns envelope containing ciphertext bytes, base64 strings, nonce, and SHA-256 hash.
    """
    if plaintext is None:
        raise ValueError("Plaintext cannot be None.")

    plaintext_bytes = plaintext.encode("utf-8")
    
    # 256-bit AES key (32 bytes)
    aes_key = key if key is not None else os.urandom(32)
    if len(aes_key) != 32:
        raise ValueError("AES-256 key must be exactly 32 bytes.")

    # 12-byte standard GCM nonce
    nonce = os.urandom(12)
    aesgcm = AESGCM(aes_key)
    
    # Encrypt (includes 16-byte GCM authentication tag)
    ciphertext_bytes = aesgcm.encrypt(nonce, plaintext_bytes, None)
    ciphertext_hash = sha256_bytes(ciphertext_bytes)

    return {
        "key_bytes": aes_key,
        "key_b64": base64.b64encode(aes_key).decode("ascii"),
        "nonce_bytes": nonce,
        "nonce_b64": base64.b64encode(nonce).decode("ascii"),
        "ciphertext_bytes": ciphertext_bytes,
        "ciphertext_b64": base64.b64encode(ciphertext_bytes).decode("ascii"),
        "ciphertext_hash": ciphertext_hash,
    }

def decrypt_message(ciphertext_bytes: bytes, nonce_bytes: bytes, key_bytes: bytes) -> str:
    """
    Authenticate and decrypt AES-256-GCM ciphertext.
    Raises ValueError if authentication tag fails (tampered payload or incorrect key).
    Returns decoded original UTF-8 string.
    """
    if not ciphertext_bytes or not nonce_bytes or not key_bytes:
        raise ValueError("Ciphertext, nonce, and key are all required for decryption.")

    if len(key_bytes) != 32:
        raise ValueError("AES-256 key must be exactly 32 bytes.")

    aesgcm = AESGCM(key_bytes)
    try:
        decrypted_bytes = aesgcm.decrypt(nonce_bytes, ciphertext_bytes, None)
        return decrypted_bytes.decode("utf-8")
    except InvalidTag as e:
        raise ValueError("Decryption failed: Message tampering detected or authentication tag mismatch.") from e
    except UnicodeDecodeError as e:
        raise ValueError("Decryption failed: Reconstructed bytes are not valid UTF-8.") from e
